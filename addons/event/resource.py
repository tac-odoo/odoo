# -*- coding: utf-8 ⁻*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2013-TODAY OpenERP S.A. (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import pytz
import logging
from datetime import datetime
from collections import defaultdict
from dateutil.relativedelta import relativedelta, MO, SU
from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DT_FMT
from timeline import Timeline, Availibility, WorkingHoursPeriodEmiter, GenericEventPeriodEmiter


def float_to_hm(hours):
    """ convert a number of hours (float) into a tuple like (hour, minute) """
    #return (int(v // 1), int(round((v % 1) * 60, 1)))
    minutes = int(round(hours * 60))
    return divmod(minutes, 60)


class ResourceTimeline(osv.TransientModel):
    _name = 'resource.timeline'

    LAYERS = set([
        'working_hours',
        'leaves',
        'event',  # calendar event (can be an event, a task, ...)
    ])

    def _get_resource_working_hours(self, cr, uid, ids, context=None):
        # weekday: 0: Monday, ..., 6: Saturday, 7: Sunday
        return [(wday, 0, 24) for wday in xrange(7)]

    def _get_resource_leaves(self, cr, uid, ids, date_from=None, date_to=None, context=None):
        return []

    def _get_resource_events(self, cr, uid, ids, date_from=None, date_to=None, context=None):
        return []

    def _get_resource_timezone(self, cr, uid, ids, context=None):
        if 'tz' in self._all_columns:
            result = {}
            for record in self.browse(cr, uid, ids, context=context):
                result[record.id] = record.tz or 'UTC'
        else:
            result = dict.fromkeys(ids, 'UTC')
        return result

    def _get_resource_timeline(self, cr, uid, ids, layers=None, date_from=None, date_to=None, context=None):
        if not ids:
            return False
        record_ids = ids
        if isinstance(ids, (int, long)):
            record_ids = [ids]
        if isinstance(date_from, basestring):
            date_from = datetime.strptime(date_from, DT_FMT)
        if isinstance(date_to, basestring):
            date_to = datetime.strptime(date_to, DT_FMT)

        if layers is None:
            timeline_layers = self.LAYERS
        else:
            timeline_layers = [l for l in self.LAYERS if l in layers]

        result = {}
        for record in self.browse(cr, uid, record_ids, context=context):

            tz = self._get_resource_timezone(cr, uid, [record.id], context=context)[record.id]
            # NOTE: All datetime passed to Timeline should be naive date in the resource "local timezone" !!!
            tz_resource = pytz.timezone(tz)
            tz_utc = pytz.timezone('UTC')
            date_from = Timeline.datetime_tz_convert(date_from, tz_utc, tz_resource)
            date_to = Timeline.datetime_tz_convert(date_to, tz_utc, tz_resource)
            timeline = Timeline(date_from, date_to, tz=tz, default=Availibility.AVAILABLE)

            for layer in timeline_layers:
                if layer == 'working_hours':

                    if record.calendar_id:
                        timeline.add_emiter(WorkingHoursPeriodEmiter([
                            (int(att.dayofweek)+1, att.hour_from, att.hour_to)
                            for att in record.calendar_id.attendance_ids
                        ]))

                elif layer == 'leaves':

                    # add all leaves for this event
                    leaves_emiter = GenericEventPeriodEmiter()
                    timeline.add_emiter(leaves_emiter)
                    Leave = self.pool.get('resource.calendar.leaves')
                    # leave_domain = [
                    #     '|',
                    #         '&', ('applies_to', '=', 'company'), ('company_id', '=', record.company_id.id),
                    #         '&', ('applies_to', '=', 'event'), ('event_id', '=', record.id),
                    # ]
                    # if record.calendar_id:
                    #     leave_domain[:0] = ['|', '&', ('applies_to', '=', 'calendar'),
                    #                                   ('calendar_id', '=', record.calendar_id.id)]
                    # leave_ids = leave_obj.search(cr, uid, leave_domain, context=context)
                    leave_ids = []  # FIXME: missing patches for general leaves stuff!
                    for leave in Leave.browse(cr, uid, leave_ids, context=context):
                        leave_from = timeline.datetime_from_str(leave.date_from, tz='UTC')
                        leave_to = timeline.datetime_from_str(leave.date_to, tz='UTC')
                        leaves_emiter.add_event(leave_from, leave_to, Availibility.UNAVAILABLE)

                elif layer == 'events':
                    # TODO: ...
                    pass

            result[record.id] = timeline

        if isinstance(ids, (int, long)):
            return result.values()[0]
        return result


class ResourceCalendar(osv.Model):
    _inherit = 'resource.calendar'
    _columns = {
        'slot_duration': fields.integer('Slot duration'),
    }
    _defaults = {
        'slot_duration': 4,
    }

    def name_get(self, cr, user, ids, context=None):
        if not ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        if context is None:
            context = {}
        result = super(ResourceCalendar, self).name_get(cr, user, ids, context=context)
        if context.get('show_week_hours'):
            Attendance = self.pool.get('resource.calendar.attendance')
            resdict = dict(result)
            weekdaynames = dict(Attendance.fields_get(cr, user, ['dayofweek'], context=context)['dayofweek']['selection'])
            for calendar in self.browse(cr, user, ids, context=context):
                hours_by_wday = defaultdict(list)
                # Group attendance per "week day"
                # then merge them together (1 weekday per line)
                for attendance in calendar.attendance_ids:
                    wday = attendance.dayofweek
                    hours = '%d:%02d - %d:%02d' % (
                        float_to_hm(attendance.hour_from)
                        + float_to_hm(attendance.hour_to)
                    )
                    hours_by_wday[wday].append(hours)
                hours_text = '\n'.join(('%s: %s' % (weekdaynames[wday],
                                                    ', '.join(hours_by_wday[wday]))
                                        for wday in sorted(hours_by_wday)))
                resdict[calendar.id] += u'\n' + hours_text
            result = [(_id, resdict[_id]) for _id in ids]
        return result
