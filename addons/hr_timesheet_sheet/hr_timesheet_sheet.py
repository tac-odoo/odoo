# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from pytz import timezone
import pytz

from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _

class hr_timesheet_sheet(osv.osv):
    _inherit = "hr_timesheet_sheet.sheet"
    #_table = 'hr_timesheet_sheet_sheet'

    def _total(self, cr, uid, ids, name, args, context=None):
        """ Compute the attendances, analytic lines timesheets and differences between them
            for all the days of a timesheet and the current day
        """

        res = {}
        for sheet in self.browse(cr, uid, ids, context=context or {}):
            res.setdefault(sheet.id, {
                'total_attendance': 0.0,
                'total_timesheet': 0.0,
                'total_difference': 0.0,
            })
            for period in sheet.period_ids:
                res[sheet.id]['total_attendance'] += period.total_attendance
                res[sheet.id]['total_timesheet'] += period.total_timesheet
                res[sheet.id]['total_difference'] += period.total_attendance - period.total_timesheet
        return res

    def check_employee_attendance_state(self, cr, uid, sheet_id, context=None):
        ids_signin = self.pool.get('hr.attendance').search(cr,uid,[('sheet_id', '=', sheet_id),('action','=','sign_in')])
        ids_signout = self.pool.get('hr.attendance').search(cr,uid,[('sheet_id', '=', sheet_id),('action','=','sign_out')])

        if len(ids_signin) != len(ids_signout):
            raise osv.except_osv(('Warning!'),_('The timesheet cannot be validated as it does not contain an equal number of sign ins and sign outs.'))
        return True

    def create(self, cr, uid, vals, context=None):
        if vals.get('attendances_ids'):
            # If attendances, we sort them by date asc before writing them, to satisfy the alternance constraint
            vals['attendances_ids'] = self.sort_attendances(cr, uid, vals['attendances_ids'], context=context)
        return super(hr_timesheet_sheet, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('attendances_ids'):
            # If attendances, we sort them by date asc before writing them, to satisfy the alternance constraint
            # In addition to the date order, deleting attendances are done before inserting attendances
            vals['attendances_ids'] = self.sort_attendances(cr, uid, vals['attendances_ids'], context=context)
        res = super(hr_timesheet_sheet, self).write(cr, uid, ids, vals, context=context)
        if vals.get('attendances_ids'):
            for timesheet in self.browse(cr, uid, ids):
                if not self.pool['hr.attendance']._altern_si_so(cr, uid, [att.id for att in timesheet.attendances_ids]):
                    raise osv.except_osv(_('Warning !'), _('Error ! Sign in (resp. Sign out) must follow Sign out (resp. Sign in)'))
        return res

    def sort_attendances(self, cr, uid, attendance_tuples, context=None):
        date_attendances = []
        for att_tuple in attendance_tuples:
            if att_tuple[0] in [0,1,4]:
                if att_tuple[0] in [0,1]:
                    name = att_tuple[2]['name']
                else:
                    name = self.pool['hr.attendance'].browse(cr, uid, att_tuple[1]).name
                date_attendances.append((1, name, att_tuple))
            elif att_tuple[0] in [2,3]:
                date_attendances.append((0, self.pool['hr.attendance'].browse(cr, uid, att_tuple[1]).name, att_tuple))
            else: 
                date_attendances.append((0, False, att_tuple))
        date_attendances.sort()
        return [att[2] for att in date_attendances]

    def button_confirm(self, cr, uid, ids, context=None):
        for sheet in self.browse(cr, uid, ids, context=context):
            if sheet.employee_id and sheet.employee_id.parent_id and sheet.employee_id.parent_id.user_id:
                self.message_subscribe_users(cr, uid, [sheet.id], user_ids=[sheet.employee_id.parent_id.user_id.id], context=context)
            self.check_employee_attendance_state(cr, uid, sheet.id, context=context)
            di = sheet.user_id.company_id.timesheet_max_difference
            if (abs(sheet.total_difference) < di) or not di:
                self.signal_confirm(cr, uid, [sheet.id])
            else:
                raise osv.except_osv(_('Warning!'), _('Please verify that the total difference of the sheet is lower than %.2f.') %(di,))
        return True

    def attendance_action_change(self, cr, uid, ids, context=None):
        hr_employee = self.pool.get('hr.employee')
        employee_ids = []
        for sheet in self.browse(cr, uid, ids, context=context):
            if sheet.employee_id.id not in employee_ids: employee_ids.append(sheet.employee_id.id)
        return hr_employee.attendance_action_change(cr, uid, employee_ids, context=context)
    
    def _count_attendance(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        Attendance = self.pool['hr.attendance']
        for sheet_id in ids: 
            attendance_count = Attendance.search_count(cr,uid, [('sheet_id','=', sheet_id)], context=context)
            res[sheet_id] = attendance_count
        return res

    _columns = {
        'attendances_ids' : fields.one2many('hr.attendance', 'sheet_id', 'Attendances'),
        'total_attendance': fields.function(_total, method=True, string='Total Attendance', multi="_total"),
        'total_timesheet': fields.function(_total, method=True, string='Total Timesheet', multi="_total"),
        'total_difference': fields.function(_total, method=True, string='Difference', multi="_total"),
        'period_ids': fields.one2many('hr_timesheet_sheet.sheet.day', 'sheet_id', 'Period', readonly=True),
        'account_ids': fields.one2many('hr_timesheet_sheet.sheet.account', 'sheet_id', 'Analytic accounts', readonly=True),
        'attendance_count': fields.function(_count_attendance, type='integer', string="Attendances"),
    }

    _defaults = {}

    def unlink(self, cr, uid, ids, context=None):
        sheets = self.read(cr, uid, ids, ['state','total_attendance'], context=context)
        for sheet in sheets:
            if sheet['state'] in ('confirm', 'done'):
                raise osv.except_osv(_('Invalid Action!'), _('You cannot delete a timesheet which is already confirmed.'))
            elif sheet['total_attendance'] <> 0.00:
                raise osv.except_osv(_('Invalid Action!'), _('You cannot delete a timesheet which have attendance entries.'))
        return super(hr_timesheet_sheet, self).unlink(cr, uid, ids, context=context)

class hr_attendance(osv.osv):
    _inherit = "hr.attendance"

    def _get_default_date(self, cr, uid, context=None):
        if context is None:
            context = {}
        if 'name' in context:
            return context['name'] + time.strftime(' %H:%M:%S')
        return time.strftime('%Y-%m-%d %H:%M:%S')

    def _get_hr_timesheet_sheet(self, cr, uid, ids, context=None):
        attendance_ids = []
        for ts in self.browse(cr, uid, ids, context=context):
            cr.execute("""
                        SELECT a.id
                          FROM hr_attendance a
                         INNER JOIN hr_employee e
                               INNER JOIN resource_resource r
                                       ON (e.resource_id = r.id)
                            ON (a.employee_id = e.id)
                        WHERE %(date_to)s >= date_trunc('day', a.name)
                              AND %(date_from)s <= a.name
                              AND %(user_id)s = r.user_id
                         GROUP BY a.id""", {'date_from': ts.date_from,
                                            'date_to': ts.date_to,
                                            'user_id': ts.employee_id.user_id.id,})
            attendance_ids.extend([row[0] for row in cr.fetchall()])
        return attendance_ids

    def _get_attendance_employee_tz(self, cr, uid, employee_id, date, context=None):
        """ Simulate timesheet in employee timezone

        Return the attendance date in string format in the employee
        tz converted from utc timezone as we consider date of employee
        timesheet is in employee timezone
        """
        employee_obj = self.pool['hr.employee']

        tz = False
        if employee_id:
            employee = employee_obj.browse(cr, uid, employee_id, context=context)
            tz = employee.user_id.partner_id.tz

        if not date:
            date = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        att_tz = timezone(tz or 'utc')

        attendance_dt = datetime.strptime(date, DEFAULT_SERVER_DATETIME_FORMAT)
        att_tz_dt = pytz.utc.localize(attendance_dt)
        att_tz_dt = att_tz_dt.astimezone(att_tz)
        # We take only the date omiting the hours as we compare with timesheet
        # date_from which is a date format thus using hours would lead to
        # be out of scope of timesheet
        att_tz_date_str = datetime.strftime(att_tz_dt, DEFAULT_SERVER_DATE_FORMAT)
        return att_tz_date_str

    def _get_current_sheet(self, cr, uid, employee_id, date=False, context=None):

        sheet_obj = self.pool['hr_timesheet_sheet.sheet']
        if not date:
            date = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        att_tz_date_str = self._get_attendance_employee_tz(
                cr, uid, employee_id,
                date=date, context=context)
        sheet_ids = sheet_obj.search(cr, uid,
            [('date_from', '<=', att_tz_date_str),
             ('date_to', '>=', att_tz_date_str),
             ('employee_id', '=', employee_id)],
            limit=1, context=context)
        return sheet_ids and sheet_ids[0] or False

    def _sheet(self, cursor, user, ids, name, args, context=None):
        res = {}.fromkeys(ids, False)
        for attendance in self.browse(cursor, user, ids, context=context):
            res[attendance.id] = self._get_current_sheet(
                    cursor, user, attendance.employee_id.id, attendance.name,
                    context=context)
        return res

    _columns = {
        'sheet_id': fields.function(_sheet, string='Sheet',
            type='many2one', relation='hr_timesheet_sheet.sheet',
            store={
                      'hr_timesheet_sheet.sheet': (_get_hr_timesheet_sheet, ['employee_id', 'date_from', 'date_to'], 10),
                      'hr.attendance': (lambda self,cr,uid,ids,context=None: ids, ['employee_id', 'name', 'day'], 10),
                  },
            )
    }
    _defaults = {
        'name': _get_default_date,
    }

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}

        sheet_id = context.get('sheet_id') or self._get_current_sheet(cr, uid, vals.get('employee_id'), vals.get('name'), context=context)
        if sheet_id:
            att_tz_date_str = self._get_attendance_employee_tz(
                    cr, uid, vals.get('employee_id'),
                   date=vals.get('name'), context=context)
            ts = self.pool.get('hr_timesheet_sheet.sheet').browse(cr, uid, sheet_id, context=context)
            if ts.state not in ('draft', 'new'):
                raise osv.except_osv(_('Error!'), _('You can not enter an attendance in a submitted timesheet. Ask your manager to reset it before adding attendance.'))
            elif ts.date_from > att_tz_date_str or ts.date_to < att_tz_date_str:
                raise osv.except_osv(_('User Error!'), _('You can not enter an attendance date outside the current timesheet dates.'))
        return super(hr_attendance,self).create(cr, uid, vals, context=context)

    def unlink(self, cr, uid, ids, *args, **kwargs):
        if isinstance(ids, (int, long)):
            ids = [ids]
        self._check(cr, uid, ids)
        return super(hr_attendance,self).unlink(cr, uid, ids,*args, **kwargs)

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        self._check(cr, uid, ids)
        res = super(hr_attendance,self).write(cr, uid, ids, vals, context=context)
        if 'sheet_id' in context:
            for attendance in self.browse(cr, uid, ids, context=context):
                if context['sheet_id'] != attendance.sheet_id.id:
                    raise osv.except_osv(_('User Error!'), _('You cannot enter an attendance ' \
                            'date outside the current timesheet dates.'))
        return res

    def _check(self, cr, uid, ids):
        for att in self.browse(cr, uid, ids):
            if att.sheet_id and att.sheet_id.state not in ('draft', 'new'):
                raise osv.except_osv(_('Error!'), _('You cannot modify an entry in a confirmed timesheet'))
        return True


class hr_timesheet_sheet_sheet_day(osv.osv):
    _name = "hr_timesheet_sheet.sheet.day"
    _description = "Timesheets by Period"
    _auto = False
    _order='name'
    _columns = {
        'name': fields.date('Date', readonly=True),
        'sheet_id': fields.many2one('hr_timesheet_sheet.sheet', 'Sheet', readonly=True, select="1"),
        'total_timesheet': fields.float('Total Timesheet', readonly=True),
        'total_attendance': fields.float('Attendance', readonly=True),
        'total_difference': fields.float('Difference', readonly=True),
    }

    def init(self, cr):
        cr.execute("""create or replace view hr_timesheet_sheet_sheet_day as
            SELECT
                id,
                name,
                sheet_id,
                total_timesheet,
                total_attendance,
                cast(round(cast(total_attendance - total_timesheet as Numeric),2) as Double Precision) AS total_difference
            FROM
                ((
                    SELECT
                        MAX(id) as id,
                        name,
                        sheet_id,
                        SUM(total_timesheet) as total_timesheet,
                        CASE WHEN SUM(total_attendance) < 0
                            THEN (SUM(total_attendance) +
                                CASE WHEN current_date <> name
                                    THEN 1440
                                    ELSE (EXTRACT(hour FROM current_time AT TIME ZONE 'UTC') * 60) + EXTRACT(minute FROM current_time AT TIME ZONE 'UTC')
                                END
                                )
                            ELSE SUM(total_attendance)
                        END /60  as total_attendance
                    FROM
                        ((
                            select
                                min(hrt.id) as id,
                                l.date::date as name,
                                s.id as sheet_id,
                                sum(l.unit_amount) as total_timesheet,
                                0.0 as total_attendance
                            from
                                hr_analytic_timesheet hrt
                                JOIN account_analytic_line l ON l.id = hrt.line_id
                                LEFT JOIN hr_timesheet_sheet_sheet s ON s.id = hrt.sheet_id
                            group by l.date::date, s.id
                        ) union (
                            select
                                -min(a.id) as id,
                                a.name::date as name,
                                s.id as sheet_id,
                                0.0 as total_timesheet,
                                SUM(((EXTRACT(hour FROM a.name) * 60) + EXTRACT(minute FROM a.name)) * (CASE WHEN a.action = 'sign_in' THEN -1 ELSE 1 END)) as total_attendance
                            from
                                hr_attendance a
                                LEFT JOIN hr_timesheet_sheet_sheet s
                                ON s.id = a.sheet_id
                            WHERE action in ('sign_in', 'sign_out')
                            group by a.name::date, s.id
                        )) AS foo
                        GROUP BY name, sheet_id
                )) AS bar""")



class hr_timesheet_sheet_sheet_account(osv.osv):
    _name = "hr_timesheet_sheet.sheet.account"
    _description = "Timesheets by Period"
    _auto = False
    _order='name'
    _columns = {
        'name': fields.many2one('account.analytic.account', 'Project / Analytic Account', readonly=True),
        'sheet_id': fields.many2one('hr_timesheet_sheet.sheet', 'Sheet', readonly=True),
        'total': fields.float('Total Time', digits=(16,2), readonly=True),
        'invoice_rate': fields.many2one('hr_timesheet_invoice.factor', 'Invoice rate', readonly=True),
        }

    def init(self, cr):
        cr.execute("""create or replace view hr_timesheet_sheet_sheet_account as (
            select
                min(hrt.id) as id,
                l.account_id as name,
                s.id as sheet_id,
                sum(l.unit_amount) as total,
                l.to_invoice as invoice_rate
            from
                hr_analytic_timesheet hrt
                left join (account_analytic_line l
                    LEFT JOIN hr_timesheet_sheet_sheet s
                        ON (s.date_to >= l.date
                            AND s.date_from <= l.date
                            AND s.user_id = l.user_id))
                    on (l.id = hrt.line_id)
            group by l.account_id, s.id, l.to_invoice
        )""")


class res_company(osv.osv):
    _inherit = 'res.company'
    _columns = {
        'timesheet_max_difference': fields.float('Timesheet allowed difference(Hours)',
            help="Allowed difference in hours between the sign in/out and the timesheet " \
                 "computation for one sheet. Set this to 0 if you do not want any control."),
    }
    _defaults = {
        'timesheet_max_difference': lambda *args: 0.0
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
