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

from openerp import tools
from openerp.osv import fields, osv


class hr_evaluation_report(osv.Model):
    _name = "hr.evaluation.report"
    _description = "Evaluations Statistics"
    _auto = False
    _columns = {
        'create_date': fields.date('Create Date', readonly=True),
        'department_id' : fields.many2one('hr.department', 'Department'),
        'delay_date': fields.float('Delay to Start', digits=(16, 2), readonly=True),
        'overpass_delay': fields.float('Overpassed Deadline', digits=(16, 2), readonly=True),
        'deadline': fields.date("Deadline", readonly=True),
        'final_interview': fields.date("Interview", readonly=True),
        'employee_id': fields.many2one('hr.employee', "Employee", readonly=True),
        'nbr': fields.integer('# of Requests', readonly=True),
        'state': fields.selection([
            ('new', 'To Start'),
            ('pending', 'Appraisal Sent'),
            ('done', 'Done')
        ], 'Status', readonly=True),
    }
    _order = 'create_date desc'

    _depends = {
        'hr_evaluation.evaluation': [
            'create_date', 'interview_deadline', 'date_close', 'employee_id','state',
        ],
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'hr_evaluation_report')
        cr.execute("""
            create or replace view hr_evaluation_report as (
                 select
                     min(s.id) as id,
                     date(s.create_date) as create_date,
                     s.employee_id,
                     s.department_id as department_id,
                     s.date_close as deadline,
                     s.interview_deadline as final_interview,
                     count(s.*) as nbr,
                     s.state,
                     avg(extract('epoch' from age(s.create_date,CURRENT_DATE)))/(3600*24) as  delay_date,
                     avg(extract('epoch' from age(s.date_close,CURRENT_DATE)))/(3600*24) as overpass_delay
                     from hr_evaluation_evaluation s
                 GROUP BY
                     s.id,
                     s.create_date,
                     s.state,
                     s.employee_id,
                     s.date_close,
                     s.interview_deadline,
                     s.department_id
                )
            """)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
