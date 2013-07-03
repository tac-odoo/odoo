#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# TimePeriodsQuery(start -> end, tz='UTC', default_avail='Unavail'):
#     GlobalRangeEmiter(start -> end, splittable=True, avail=default_avail)
#     WorkingHoursRangeEmiter(start -> end, splittable=True, avail='Available')
#     EventsEmiter(start -> end, splittable=False, )
#

import pytz
from functools import partial
from datetime import datetime, timedelta
from collections import deque, namedtuple, defaultdict

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

    @classmethod
    def merge(cls, avails, default=Availibility.UNKNOWN, aggregate=True):
        """Return list of merged availiblity periods"""
        Period = cls
        if not avails:
            return []
        avails.sort(key=lambda o: o.start)
        s = [avails.pop(0)]
        dm = lambda m: timedelta(minutes=m)
        ds = lambda m: timedelta(seconds=m)

        while avails:
            a = avails.pop(0)  # 1st availilbity from the list
            f, t = a.start, a.stop
            for i, b in enumerate(s):
                if (b.start <= f < b.stop) or (f <= b.start <= t):  # case 1, 2, 3, 4
                    if b.start <= f <= t <= b.stop:
                        # avail time contrains within block
                        if a.status == b.status:
                            break  # no change needed
                        l = [Period(f, t, max(a.status, b.status))]
                        if f > b.start:
                            l.insert(0, Period(b.start, f, b.status))
                            # l.insert(0, Period(b.start, f + ds(-1), b.status))  # ORIG
                        if t < b.stop:
                            l.append(Period(t, b.stop, b.status))
                            # l.append(Period(t + ds(1), b.stop, b.status))  # ORIG
                        s[i:i + 1] = l
                        break
                    if f >= b.start and t > b.stop:
                        # B:   [==========]
                        # A:        [==========]
                        # --- or ---
                        # B:   [=======]
                        # A:   [==========]
                        l = [Period(f, b.stop, max(a.status, b.status))]
                        if f > b.start:
                            l.insert(0, Period(b.start, f, b.status))
                            # l.insert(0, Period(b.start, f - ds(1), b.status))  # ORIG
                        s[i:i + 1] = l
                        # push extra back on stack
                        avails.insert(0, Period(b.stop, t, a.status))
                        break
            else:
                # availibility does not overlap with other parts
                # add it to the solution list
                s.append(a)

        # Aggregate consecutive time
        if aggregate:
            sr = []
            for a in s:
                if a.status == Availibility.UNKNOWN:
                    a.status = default  # unknown slots are consider unavailable
                if not sr or (sr and sr[-1].status != a.status):
                    sr.append(Period(a.start, a.stop, a.status))
                    continue
                sr[-1].stop = a.stop
                sr[-1].status = a.status
        else:
            sr = s[:]
        sr.sort(key=lambda o: o.start)
        return sr


def izip_notruncate(iterators, barrier_delta=None):
    """like izip but do not truncate to shortest length

        :return: list of iterators values (variable length)
    """

    iterators = dict((n, {
        'it': iterator,
        'alive': True,
        'values': deque()
    }) for n, iterator in enumerate(iterators))

    while sum(i['alive'] for i in iterators.itervalues()):
        v = []
        for n, iterator in iterators.items():
            if iterator['alive']:
                try:
                    v = iterator['it'].next()
                    iterator['values'].append(v)
                except StopIteration:
                    iterator['alive'] = False
        # collect values
        if not barrier_delta:
            v = []
            for i in iterators.itervalues():
                if i['values']:
                    v.append(i['values'].popleft())
            yield v
        else:
            min_date = min(v.start
                           for i in iterators.itervalues()
                           for v in i['values'] if i['values'])
            barrier_date = min_date + barrier_delta
            ok = all(not i['alive'] or (i['values'] and max(v.start for v in i['values']) > barrier_date)
                     for i in iterators.itervalues())
            # XXX: fix that following ugly! code
            if ok:
                v = []
                for i in iterators.itervalues():
                    if not i['alive']:
                        v.extend(i['values'])
                        i['values'].clear()
                    else:
                        while i['values']:
                            k = i['values'].popleft()
                            if k.start < barrier_date:
                                v.append(k)
                            else:
                                # push it back
                                i['values'].appendleft(k)
                                break
                yield v


class PeriodEmiter(object):
    def get_iterator(self, start, end, by='change', tz=None):
        raise NotImplementedError()

    def get_default_delta(self, mode):
        if mode == 'second':
            return timedelta(seconds=1)
        elif mode == 'minute':
            return timedelta(minutes=1)
        elif mode == 'hour':
            return timedelta(hours=1)
        elif mode == 'day':
            return timedelta(days=1)
        raise Exception("invalid mode '%s' for delta" % (mode,))


class GlobalPeriodEmiter(PeriodEmiter):
    """Simpliest event emiter

    :return: the default availability status defined for the period
    """
    def __init__(self, default):
        assert default in Availibility.values
        self.default = default

    def get_iterator(self, start, end, by='change', tz=None):
        s = start.replace()
        if by == 'change':
            # iter by end of a day
            delta = self.get_default_delta('day')
        else:
            delta = self.get_default_delta(by)
        first = True
        while s < end:
            if by == 'change' and first:
                e = min((s + delta).replace(hour=0, minute=0, second=0), end)
                first = False
            else:
                e = min(s + delta, end)
            yield AvailibilityPeriod(s, e, self.default)
            s = e


class WorkingHoursPeriodEmiter(PeriodEmiter):
    """Emit availibility for each working hours"""
    def __init__(self, working_hours, default=Availibility.UNAVAILABLE):
        self.default = default
        self.wrkhours_per_isoweekday = defaultdict(list)
        for (isoweekday, hour_from, hour_to) in working_hours:
            self.wrkhours_per_isoweekday[isoweekday].append((hour_from, hour_to))
        self.wrkhours_flatten = self.get_flatten_working_hours()

    def get_flatten_working_hours(self):
        wkhours_list = []
        for isoweekday in range(1, 7+1):
            hours = self.wrkhours_per_isoweekday.get(isoweekday, [])
            hours.sort(key=lambda o: o[0])
            if not hours:
                wkhours_list.append((isoweekday, 0., 24., self.default))
            else:
                xflat, prev = [], 0
                for (hfrom, hto) in hours:
                    if hfrom < prev:
                        raise Exception('overlapping working hours')
                    if abs(hfrom - prev) > 0.01:
                        xflat.append((isoweekday, prev, hfrom, self.default))
                    xflat.append((isoweekday, hfrom, hto, Availibility.FREE))
                    prev = hto
                if abs(24. - xflat[-1][2]) > 0.01:
                    xflat.append((isoweekday, prev, 24., self.default))
                wkhours_list.extend(xflat)
        return wkhours_list

    def find_workhours(self, date):
        date_wday = date.isoweekday()
        date_time = date.hour + (date.second / 60.)
        for i, (wday, hour_from, hour_to, _) in enumerate(self.wrkhours_flatten):
            if wday == date_wday and hour_from <= date_time < hour_to:
                return i
        raise IndexError()

    def find_workhours_in_range(self, date_from, date_to):
        s = date_from.replace()
        current_idx = self.find_workhours(s)
        wkhours = []
        while s < date_to:
            wkhours.append(self.wrkhours_flatten[current_idx])
            current = self.wrkhours_flatten[current_idx]
            next_idx = (current_idx + 1) % len(self.wrkhours_flatten)
            next = self.wrkhours_flatten[next_idx]
            if current[0] != next[0]:
                s = datetime(s.year, s.month, s.day) + timedelta(days=1, hours=next[1])
            else:
                s = datetime(s.year, s.month, s.day) + timedelta(hours=next[1])
            current_idx = next_idx
        return wkhours

    def get_iterator(self, start, end, by='change', tz=None):
        s = start.replace()
        if by == 'second':
            delta = timedelta(seconds=1)
        elif by == 'minute':
            delta = timedelta(minutes=1)
        elif by == 'hour':
            delta = timedelta(hours=1)
        elif by == 'day':
            delta = timedelta(days=1)
        while s < end:
            current_period_idx = self.find_workhours(s)
            current_period = self.wrkhours_flatten[current_period_idx]

            if by == 'change':
                e = min(datetime(s.year, s.month, s.day) + timedelta(hours=current_period[2]),
                        end)
                yield AvailibilityPeriod(s, e, current_period[3])

                next_period = self.wrkhours_flatten[(current_period_idx + 1) % len(self.wrkhours_flatten)]
                if current_period[0] != next_period[0]:
                    # shiffted days
                    s = datetime(s.year, s.month, s.day) + timedelta(days=1, hours=next_period[1])
                else:
                    s = datetime(s.year, s.month, s.day) + timedelta(hours=next_period[1])
            elif by in ('second', 'minute', 'hour', 'day'):
                e = min(s + delta, end)
                wkhours = self.find_workhours_in_range(s, e)
                availibility = max(x[3] for x in wkhours)
                yield AvailibilityPeriod(s, e, availibility)
                s = e


class EventPeriod(AvailibilityPeriod):
    name = 'Event'
    pass


class GenericEventPeriodEmiter(PeriodEmiter):
    """Emit period from a list of events
    :return: the default availability status defined for the period
    """
    def __init__(self, default=Availibility.UNKNOWN):
        assert default in Availibility.values
        self.default = default
        self.events = []  # list of event period

    def add_event(self, start, stop, status=Availibility.UNAVAILABLE):
        self.events.append(EventPeriod(start, stop, status))

    def add_events(self, event_list):
        for (s, e, a) in event_list:
            self.events.append(EventPeriod(s, e, a))
        return True

    def events_range(self, events, start, end):
        start_idx, stop_idx = None, None
        for i, event in enumerate(events):
            if start_idx is None:
                if event.start <= start <= event.stop:
                    start_idx = i
            if start_idx is not None:
                if event.start <= end <= event.stop:
                    stop_idx = i
                    break
        else:
            # either not start or not end date found
            return []
        return self.events[start_idx:stop_idx+1]

    def event_idx(self, events, date):
        for i, event in enumerate(events):
            if event.start <= date <= event.stop:
                return i
        return None

    def get_iterator(self, start, end, by='change', tz=None):
        global_event_period = EventPeriod(start, end, Availibility.UNKNOWN)
        events = EventPeriod.merge(self.events + [global_event_period])
        s = start.replace()
        if by == 'change':
            event_idx = self.event_idx(events, start)
            event_max = len(events)
        else:
            delta = self.get_default_delta(by)
        while s < end:
            if by == 'change':
                if event_idx is not None:
                    current_event = events[event_idx]
                    yield AvailibilityPeriod(current_event.start, current_event.stop,
                                             current_event.status)
                    event_idx += 1
                    if event_idx >= event_max:
                        break
                    s = events[event_idx].start
            else:
                e = min(s + delta, end)
                range_events = self.events_range(events, s, e)
                if not range_events:
                    range_avail = Availibility.UNKNOWN
                else:
                    range_avail = max(e.status for e in range_events)
                yield AvailibilityPeriod(s, e, range_avail)
                s = e


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
        self.setup_emiters()

    def setup_emiters(self):
        self.emiters.append(GlobalPeriodEmiter(self.default))

    def add_emiter(self, emiter):
        self.emiters.append(emiter)

    def emit_periods(self, by='change'):
        barrier_delta = None
        if by == 'change':
            barrier_delta = timedelta(days=1)
        return izip_notruncate([
            emiter.get_iterator(self.start, self.end, by=by, tz=self.tz_local)
            for emiter in self.emiters
        ], barrier_delta=barrier_delta)

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

    def iter(self, by='change', as_tz=None):
        """iterate over time period by specified cycle

        :param by: represent availiblity period range
                   can be any of: change, day, hour, minute
        :return: yield new AvailiblityPeriod instance
        """
        assert by in ('change', 'day', 'hour', 'minute', 'second')
        change_periods = []

        tzhandler = lambda a: a
        if as_tz is not None:
            as_tz_info = pytz.timezone(as_tz)
            tzhandler = partial(self.tz_adaptor, tz_from=self.tz_local_info, tz_to=as_tz_info)

        for periods in self.emit_periods(by=by):
            # fit period with Timeline start/end range
            periods = [p for p in periods
                       if p.stop > self.start and p.start <= self.end]
            for p in periods:
                if p.start < self.start:
                    p.start = self.start
                if p.stop > self.end:
                    p.stop = self.end

            # merge periods availability
            if by in ('day', 'hour', 'minute', 'second'):
                # period start/end should be in sync, we only
                # have to compute availibility status
                if periods:
                    availibility = max(p.status for p in periods)
                else:
                    availibility = self.default
                start, stop = periods[0].start, periods[0].stop
                yield tzhandler(AvailibilityPeriod(start, stop, availibility))
            elif by == 'change':
                change_periods.extend(periods)
                change_periods = AvailibilityPeriod.merge(change_periods, default=self.default)
                if change_periods:
                    # only yield 1st period so that we get the
                    # smalest change each time
                    yield tzhandler(change_periods.pop(0))
        if by == 'change':
            for p in change_periods:
                yield tzhandler(p)


if __name__ == '__main__':
    start, end = datetime(2013, 1, 1, 8, 0, 0), datetime(2013, 1, 8, 20, 0, 0)
    tp = Timeline(start, end, tz='Europe/Paris')
    tp.add_emiter(
        WorkingHoursPeriodEmiter([
            (1, 8., 12.), (1, 13., 17.),
            (2, 8., 12.), (2, 13., 17.),
            (3, 8., 12.), (3, 13., 17.),
            (4, 8., 12.), (4, 13., 17.),
            (5, 8., 12.), (5, 13., 17.),
        ])
    )
    # Add custom event to timeline, like leaves, task or training events
    leaves_emiter = GenericEventPeriodEmiter()
    leaves_emiter.add_events([
        # New year's day
        (datetime(2013, 1, 1, 0, 0, 0), datetime(2013, 1, 2, 0, 0), Availibility.UNAVAILABLE, 'Community Days Workshop'),
    ])
    tp.add_emiter(leaves_emiter)

    for p in tp.iter(by='change', as_tz='UTC'):
        print(p)
