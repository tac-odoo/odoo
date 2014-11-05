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

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import openerp
from openerp.osv import fields, osv
from openerp.report import report_sxw

class report_custom(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(report_custom, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_start_date': lambda start_date: datetime.strptime(start_date, "%Y-%m-%d").strftime('%m/%d/%Y'),
            'get_end_date': lambda start_date: (datetime.strptime(start_date, "%Y-%m-%d").date() + relativedelta(days=59)).strftime('%m/%d/%Y'),
            'get_leave_type': lambda holiday_type: 'Confirmed and Approved' if holiday_type == 'both' else 'Approved' if holiday_type == 'Approved' else 'Confirmed',
            'get_day': self._get_day,
            'get_months': self._get_months,
            'get_data_from_report': self._get_data_from_report,
            'get_holidays_status': self._get_holidays_status,
        })

    def _get_day(self, start_date):
        res = []
        # find the date and which day.
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = start_date + relativedelta(days=59)
        total_days = (end_date - start_date).days + 1
        for x in range(0, total_days):
            color = ' '
            if start_date.strftime('%a') == 'Sat' or start_date.strftime('%a') == 'Sun':
                color = '#ababab'
            res.append({'day_str': start_date.strftime('%a'), 'day': start_date.day , 'color': color})
            start_date = start_date + relativedelta(days=1)
        return res

    def _get_months(self, start_date):
        res = []
        # it work for get month last date and different between two date.
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = start_date + relativedelta(days=59)
        ld = start_date
        while ld <= end_date:
            temp = ld + relativedelta(day=1, months=+1, days=-1)
            if temp > end_date:
                temp = end_date
            res.append({'month_name': ld.strftime('%B'), 'days': (temp - ld).days + 1})
            ld = ld + relativedelta(day=1, months=+1)
        return res

    def _get_leaves_summary(self, start_date, empid, holiday_type):
        display = []
        count = 0
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = start_date + relativedelta(days=59)
        total_days = (end_date - start_date).days + 1
        holidays_obj = self.pool['hr.holidays']
        if holiday_type != 'both':
            if holiday_type == 'Confirmed':
                holiday_type = ['confirm']
            else:
                holiday_type = ['validate']
        else:
            holiday_type = ['confirm','validate']

        holidays_ids = holidays_obj.search(self.cr, self.uid, ['&', ('employee_id', 'in', [empid,False]), ('state', 'in', holiday_type), ('type', '=', 'remove'), ('date_from', '<=', str(end_date)), ('date_to', '>=', str(start_date))])

        # count and get leave summary details.
        for index in range(0, total_days):
            current = start_date + timedelta(index)
            display.append({'day': current.day, 'color': ''})
            if current.strftime('%a') == 'Sat' or current.strftime('%a') == 'Sun':
                display[index].update({'color': '#ababab'})

        holidays_data = holidays_obj.browse(self.cr, self.uid, holidays_ids)
        for holiday in holidays_data:
            date_from = datetime.strptime(holiday.date_from, '%Y-%m-%d %H:%M:%S')
            date_to = datetime.strptime(holiday.date_to, '%Y-%m-%d %H:%M:%S')
            for index in range(0, ((date_to - date_from).days + 1)):
                tmp = date_from + timedelta(index)
                if tmp >= start_date and tmp <= end_date:
                    display[(tmp-start_date).days].update({'color': holiday.holiday_status_id.color_name})
                    count+=1
        self.sum = count
        return display

    def _get_data_from_report(self, data):
        res = []
        if 'depts' in data:
            departments = self.pool['hr.department'].browse(self.cr, self.uid, data['depts'])
            for department in departments:
                res.append({'dept' : department.name, 'data': [], 'color': self._get_day(data['date_from'])})
                employee_ids = self.pool['hr.employee'].search(self.cr, self.uid, [('department_id', '=', department.id)])
                employees = self.pool['hr.employee'].browse(self.cr, self.uid, employee_ids)
                for emp in employees:
                    res[len(res)-1]['data'].append({
                        'emp': emp.name,
                        'display': self._get_leaves_summary(data['date_from'], emp.id, data['holiday_type']),
                        'sum': self.sum
                    })
        elif 'emp' in data:
            employees = self.pool['hr.employee'].browse(self.cr, self.uid, data['emp'])
            res.append({'data':[]})
            for emp in employees:
                res[0]['data'].append({
                    'emp': emp.name,
                    'display': self._get_leaves_summary(data['date_from'], emp.id, data['holiday_type']),
                    'sum': self.sum
                })
        return res

    def _get_holidays_status(self):
        res = []
        holiday_obj = self.pool['hr.holidays.status']
        holiday_ids = self.pool['hr.holidays.status'].search(self.cr, self.uid, [])
        for holiday in self.pool['hr.holidays.status'].browse(self.cr, self.uid, holiday_ids):
            res.append({'color': holiday.color_name, 'name': holiday.name})
        return res


class wrapped_report_holidays_summary(osv.AbstractModel):
    _name = 'report.hr_holidays.report_holidayssummary'
    _inherit = 'report.abstract_report'
    _template = 'hr_holidays.report_holidayssummary'
    _wrapped_report_class = report_custom

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: