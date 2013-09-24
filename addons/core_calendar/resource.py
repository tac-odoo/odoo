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
from openerp.tools.translate import _


def float_to_hm(hours):
    """ convert a number of hours (float) into a tuple like (hour, minute) """
    #return (int(v // 1), int(round((v % 1) * 60, 1)))
    minutes = int(round(hours * 60))
    return divmod(minutes, 60)


class ResourceCalendar(osv.Model):
    _inherit = 'resource.calendar'
    _columns = {
        'slot_duration': fields.float('Slot Duration',
                                      help="Standard slot duration, used for planification purpuse"),
        'company_leave_ids': fields.one2many('resource.calendar.leaves', 'calendar_id', 'Company non-working days',
                                             domain=[('resource_id', '=', False)]),
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


class resource_calendar_leaves(osv.Model):
    _inherit = "resource.calendar.leaves"

    def _get_leave_company_id(self, cr, uid, ids, field_name, args, context=None):
        result = {}
        if not ids:
            return result
        calendar = self.pool.get('resource.calendar')
        calendar_all_ids = calendar.search(cr, uid, [])
        calendar_records = dict((x.id, x)
                                for x in calendar.browse(cr, uid, calendar_all_ids))
        cr.execute("SELECT id, calendar_id, company_id FROM "+self._table+" WHERE id IN %s", (tuple(ids),))
        for leave_id, calendar_id, company_id in cr.fetchall():
            if calendar_id:
                company_id = calendar_records[calendar_id].company_id.id
            result[leave_id] = company_id
        return result

    def _set_leave_company_id(self, cr, uid, id, field_name, field_value, args, context=None):
        leave = self.browse(cr, uid, id, context=context)
        if not leave.calendar_id:
            cr.execute("UPDATE "+self._table+" SET company_id = %s WHERE id = %s", (field_value, id,))
        return True

    def _get_applies_to_selection(self, cr, uid, context=None):
        return [
            ('company', _('Whole Company')),
            ('calendar', _('This calendar')),
            ('resource', _('This resource')),
            ('resource_all', _('All resources')),
        ]

    def _get_applies_to(self, cr, uid, ids, field_name, args, context=None):
        result = {}
        for leave in self.browse(cr, uid, ids, context=context):
            if leave.applies_to == 'resource_all':
                result[leave.id] = 'resource_all'
            elif leave.partner_id or leave.resource_id:
                result[leave.id] = 'resource'
            elif leave.calendar_id:
                result[leave.id] = 'calendar'
            else:
                result[leave.id] = 'company'
        return result

    def _set_applies_to(self, cr, uid, id, field_name, value, args, context=None):
        if value == 'resource_all':
            cr.execute("""UPDATE resource_calendar_leaves
                             SET applies_to = %s
                          WHERE id = %s""",
                       (value, id,))
        return True

    _columns = {
        # allow to store company id directly - this is required to have company global closing days
        'company_id': fields.function(_get_leave_company_id, type='many2one', relation='res.company',
                                      fnct_inv=_set_leave_company_id,
                                      string="Company", store=True, readonly=True),
        'applies_to': fields.function(lambda s, *a, **kw: s._get_applies_to(*a, **kw), type='selection', string='Applies to',
                                      selection=lambda s, *a, **kw: s._get_applies_to_selection(*a, **kw),
                                      store=True, fnct_inv=lambda s, *a, **kw: s._set_applies_to(*a, **kw)),
        'partner_id': fields.many2one('res.partner', 'Contact'),
    }

    def onchange_applies_to(self, cr, uid, ids, applies_to, context=None):
        values = {}
        if applies_to == 'company':
            values.update(calendar_id=False, resource_id=False, partner_id=False, event_id=False)
        elif applies_to == 'calendar':
            values.update(resource_id=False, partner_id=False, event_id=False)
        return {'value': values}
