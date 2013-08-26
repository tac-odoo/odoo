#!/usr/bin/python
# -*- coding: utf-8 -*-

import pytz
import math
from functools import partial
from datetime import datetime, timedelta

D_FMT = '%Y-%m-%d'
T_FMT = '%H:%M:%S'
DT_FMT = '{0} {1}'.format(D_FMT, T_FMT)


class Availibility:
    UNKNOWN, UNAVAILABLE, FREE, BUSY_TENTATIVE, BUSY = range(5)
    values = [UNKNOWN, UNAVAILABLE, FREE, BUSY_TENTATIVE, BUSY]

    @staticmethod
    def get_availability_value(value):
        return {
            Availibility.UNKNOWN: 'UNKNOWN',
            Availibility.UNAVAILABLE: 'UNAVAILABLE',
            Availibility.FREE: 'FREE',
            Availibility.BUSY_TENTATIVE: 'BUSY_TENTATIVE',
            Availibility.BUSY: 'BUSY',
        }[value]


class AvailibilityPeriod(object):
    name = 'Availability'
    __slots__ = ('start', 'stop', 'status', 'splitable')

    def __init__(self, start, stop, status, splitable=True):
        assert status in Availibility.values
        self.start = start
        self.stop = stop
        self.status = status
        self.splitable = splitable

    def __str__(self):
        return "%s '[ %s -> %s [' :: %s" % (
            self.name, self.start, self.stop,
            Availibility.get_availability_value(self.status),
        )

    __repr__ = __str__

    def __nonzero__(self):
        return self.duration > 0

    def shift_hours(self, hours):
        new_start = self.start + timedelta(hours=hours)
        if new_start > self.stop:
            raise ValueError('Shift period exceed stop date')
        v = (self.start, new_start)
        self.start = new_start
        return v

    @property
    def duration(self):
        """return period duration in hours - float representation"""
        d = self.stop - self.start
        return d.days * 24. + d.seconds / 3600.

    @staticmethod
    def dump(periods):
        print("Periods dump:")
        for p in periods:
            print("--- %s" % (p,))


class PeriodEmiter(object):
    def __init__(self, name, default=Availibility.UNKNOWN):
        assert default in Availibility.values
        self.name = name
        self.default = default

    def get_iterator(self, start, end, tz=None):
        raise NotImplementedError()


class WorkingHoursPeriodEmiter(PeriodEmiter):
    """Emit availibility for each working hours"""
    def __init__(self, name, default=Availibility.FREE, working_hours=None):
        super(WorkingHoursPeriodEmiter, self).__init__(name, default)
        if not working_hours:  # None or empty list
            self.working_hours = [
                ((1, 0.0), (7, 24.0), default),
            ]
        else:
            H_WEEKDAY, H_START, H_END, H_STATUS = range(4)
            hours = []
            last = (1, 0.0)
            for i, workhour in enumerate(working_hours):
                workhour_start = (workhour[H_WEEKDAY], float(workhour[H_START]))
                workhour_end = (workhour[H_WEEKDAY], float(workhour[H_END]))

                last_consecutive = list(last)
                if last_consecutive[1] == 24.0:
                    last_consecutive[1] = 0.0
                    last_consecutive[0] += 1
                    if last_consecutive[0] > 7:
                        last_consecutive[0] -= 7
                last_consecutive = tuple(last_consecutive)

                if workhour_start > last_consecutive:
                    hours.append((last, workhour_start, Availibility.UNKNOWN))
                hours.append((workhour_start, workhour_end, default))
                last = hours[-1][1]

            if last < (7, 24.0):
                hours.append((last, (7, 24.0), Availibility.UNKNOWN))

            self.working_hours = hours

    def get_iterator(self, start, end, tz=None):
        P_START, P_END, P_STATUS = range(3)
        P_WEEKDAY, P_HOURMIN = range(2)

        def to_hourmin(x):
            m, h = math.modf(x)
            m = m * 60.
            return (int(h), int(m))

        def to_float(h, m):
            return h + (m / 60.)

        s = start.replace()

        hours = self.working_hours[:]
        p = (s.isoweekday(), to_float(s.hour, s.minute))
        period_idx = None
        for i, wh in enumerate(hours):
            if wh[P_START] <= p < wh[P_END]:
                period_idx = i
                break
        else:
            raise Exception('No matching working hours found for starting date: %s' % s.strftime(DT_FMT))
        period = hours[period_idx]

        while s < end:
            h, m = to_hourmin(period[P_END][P_HOURMIN])
            end_weekday = period[P_END][P_WEEKDAY]
            if (h, m) == (24, 0):
                end_weekday += 1
                if end_weekday > 7:
                    end_weekday -= 7
                h, m = (0, 0)
            e = s.replace()
            while e.isoweekday() != end_weekday:
                e += timedelta(days=1)
            e = min(e.replace(hour=h, minute=m, second=0, microsecond=0), end)
            yield AvailibilityPeriod(s, e, period[P_STATUS])

            s = e
            period_idx = (period_idx + 1) % len(hours)
            period = hours[period_idx]

            h, m = to_hourmin(period[P_START][P_HOURMIN])
            start_weekday = period[P_START][P_WEEKDAY]
            while s.isoweekday() != start_weekday:
                s += timedelta(days=1)
            s = s.replace(hour=h, minute=m, second=0, microsecond=0)
        return


class EventPeriod(AvailibilityPeriod):
    name = 'Event'
    pass


class GenericEventPeriodEmiter(PeriodEmiter):
    """Emit period from a list of events
    :return: the default availability status defined for the period
    """
    def __init__(self, name, default=Availibility.UNKNOWN):
        super(GenericEventPeriodEmiter, self).__init__(name, default)
        self.events = []  # list of event period

    def add_event(self, start, stop, status=None):
        if status is None:
            status = self.default
        self.events.append(EventPeriod(start, stop, status))

    def add_events(self, event_list):
        for (s, e, a) in event_list:
            self.events.append(EventPeriod(s, e, a))
        return True

    def get_iterator(self, start, end, tz=None):
        for e in self.events:
            yield AvailibilityPeriod(e.start, e.stop, e.status)
        return


class EmiterIteratorHelper(object):
    def __init__(self, it):
        self.it = it
        self.alive = True
        # get initial period
        self.next()

    def getnext(self, start_date):
        emiter_next = self.next
        while self.alive:
            c = self.current
            if c.start <= start_date < c.stop:
                # match date within current period
                return c
            elif start_date < c.start:
                # mathc date before current period (empty zone)
                return None

            # Get next iterator and retry
            emiter_next()
        return None

    def next(self):
        try:
            self.current = self.it.next()
        except StopIteration:
            self.alive = False
            self.current = None


class Timeline(object):
    TZ_UTC = pytz.timezone('UTC')

    def __init__(self, start, end=None, default=Availibility.UNKNOWN, tz=None):
        self.tz_local = tz or 'UTC'
        self.tz_local_info = pytz.timezone(self.tz_local)
        self.default = default
        self.start = start
        self.end = end or datetime.max
        # initialize emiters
        self.emiters = []

    def add_emiter(self, emiter):
        self.emiters.append(emiter)

    def tz_adaptor(self, availibility, tz_from=None, tz_to=None):
        assert tz_from is not None
        assert tz_to is not None
        availibility.start = self.datetime_tz_convert(availibility.start, tz_from, tz_to)
        availibility.stop = self.datetime_tz_convert(availibility.stop, tz_from, tz_to)
        return availibility

    @staticmethod
    def datetime_tz_convert(dt, tz_from, tz_to, naive=True):
        if isinstance(tz_from, basestring):
            tz_from = pytz.timezone(tz_from)
        if isinstance(tz_to, basestring):
            tz_to = pytz.timezone(tz_to)
        if isinstance(dt, basestring):
            try:
                dt = datetime.strptime(dt, DT_FMT)
            except ValueError:
                dt = datetime.strptime(dt, D_FMT)
        # print("DT: %s, TZ: %s -> %s" % (dt, tz_from, tz_to,))
        # if dt is None:
        #     import pdb; pdb.set_trace()
        if tz_from == tz_to:
            return dt
        d = tz_from.localize(dt).astimezone(tz_to)
        if naive:
            d = d.replace(tzinfo=None)
        return d

    def datetime_from_str(self, string, tz=None):
        """Convert a string into a datetime object

        :param tz: used to determine the source timezone of datetime string
                   if provided the date is converted from this timezone to  timeline internal "local timezone"
        :return: datetime instance represented by string (in naive timezone)
        """
        if tz is None:
            tz = self.tz_local_info
        elif isinstance(tz, basestring):
            tz = self.TZ_UTC if tz == 'UTC' else pytz.timezone(tz)
        dt = datetime.strptime(string, DT_FMT)
        return self.datetime_tz_convert(dt, tz, self.tz_local_info)

    def iterperiods(self, start=None, end=None, layers=None, as_tz=None, debug=False):
        # TODO: handle customer tz
        start = start or self.start
        end = end or self.end or (datetime.max - timedelta(hours=12))
        cdate = start.replace()

        tzhandler = lambda a: a
        if as_tz is not None:
            as_tz_info = pytz.timezone(as_tz)
            tzhandler = partial(self.tz_adaptor, tz_from=self.tz_local_info, tz_to=as_tz_info)

        # Conf local iters
        iters = [
            EmiterIteratorHelper(emiter.get_iterator(start, end, tz=self.tz_local))
            for emiter in self.emiters
            if layers is None or emiter.name in layers
        ]

        p = None
        while iters and cdate < end:
            pstart = cdate
            pend = datetime.max
            pstatus = self.default
            pinfo = []  # TODO: handle specific pinfo states

            # Get all matching periods from iterators
            periods = []
            for i in iters:
                c = i.getnext(pstart)
                if c:
                    periods.append(c)
                elif i.alive:
                    periods.append(AvailibilityPeriod(pstart, i.current.start, self.default))
                else:  # not i.alive:
                    iters.remove(i)

            if not periods and iters:
                # still some iters available but no matching
                # for current start date, returning default one
                pend = min(i.current.start for i in iters)
                cdate = pend
                yield tzhandler(AvailibilityPeriod(pstart, pend, self.default))
            elif periods:
                # find min end date
                pend = min(p.stop for p in periods)
                pstatus = max(p.status for p in periods)
                cdate = pend
                yield tzhandler(AvailibilityPeriod(pstart, pend, pstatus))
            # else (not period & not iters)
            # => we've finished - returning final date with default status
            pass
        if cdate < end:
            yield tzhandler(AvailibilityPeriod(cdate, end, self.default))


if __name__ == '__main__':

    UNKNOWN = Availibility.UNKNOWN
    BUSY = Availibility.BUSY
    BUSY_TENTATIVE = Availibility.BUSY_TENTATIVE
    FREE = Availibility.FREE

    def D(v):
        return datetime.strptime(v, '%Y-%m-%d %H:%M:%S')

    t = Timeline(
        D('2013-08-19 00:00:00'),
        D('2013-08-26 00:00:00'),
        tz='Europe/Paris')

    wkhours = WorkingHoursPeriodEmiter('working-hours', working_hours=[
        (1, 8, 12), (1, 13, 17),
        (2, 8, 12), (2, 13, 17),
        (3, 8, 12), (3, 13, 17),
        (4, 8, 12), (4, 13, 17),
        (5, 8, 12), (5, 13, 17),
    ])
    t.add_emiter(wkhours)

    rngdates = GenericEventPeriodEmiter('events')
    rngdates.add_event(D('2013-08-19 10:00:00'), D('2013-08-19 12:00:00'), BUSY)
    rngdates.add_event(D('2013-08-25 08:00:00'), D('2013-08-25 16:00:00'), BUSY_TENTATIVE)
    t.add_emiter(rngdates)

    # Iter with no layers
    print("Test #0:")
    for p in t.iterperiods(layers=[]):
        print("P: %s" % p)

    # Iter with only events (+ default)
    print("Test #1:")
    for p in t.iterperiods(layers=['events'], debug=False):
        print("P EVENT: %s" % p)

    # Iter with only working-hours (+ default)
    print("Test #2:")
    for p in t.iterperiods(layers=['working-hours'], debug=False):
        print("P WRK HOURS: %s" % p)

    # Iter with all layers (working-hours + events + default)
    print("Test #3:")
    for p in t.iterperiods(debug=False):
        print("P ALL: %s" % p)
