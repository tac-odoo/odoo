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

from collections import defaultdict
from openerp.osv import osv, fields


def float_to_hm(hours):
    """ convert a number of hours (float) into a tuple like (hour, minute) """
    #return (int(v // 1), int(round((v % 1) * 60, 1)))
    minutes = int(round(hours * 60))
    return divmod(minutes, 60)


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
