# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-Today OpenERP S.A. (<http://www.openerp.com>).
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
from dateutil import parser
import time

from openerp import fields, api, tools, models
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DF


class hr_evaluation(models.Model):
    _name = "hr_evaluation.evaluation"
    _inherit = ['mail.thread']
    _description = "Employee Appraisal"

    _track = {
        'state': {
            'hr_evaluation.mt_apprasial_stage': lambda self, cr, uid, obj, ctx=None: True,
        },
    }

    @api.one
    def _set_default_template(self):
        model, template_id = self.env['ir.model.data'].get_object_reference('hr_evaluation', 'email_template_appraisal')
        return template_id

    @api.one
    def _set_appraisal_url(self,):
        self.appraisal_url = ''
        self.email_to = ''
        self.send_mail_status = False

    @api.cr_uid
    def _get_state_list(self, cr, uid, context=None):
        return [('new', 'To Start'),
                ('pending', 'Appraisal Sent'),
                ('done', 'Done'),]

    interview_deadline = fields.Date("Final Interview", select=True)
    employee_id = fields.Many2one('hr.employee', required=True, string='Employee')
    department_id = fields.Many2one('hr.department', 'Department')
    evaluation = fields.Text('Evaluation Summary', help="If the evaluation does not meet the expectations, you can propose an action plan")
    state = fields.Selection(_get_state_list, 'Status', track_visibility='onchange', required=True, readonly=True, copy=False, default='new', select=True)
    date_close = fields.Date('Appraisal Deadline', select=True, required=True)
    appraisal_manager = fields.Boolean('Manger',)
    apprasial_manager_ids = fields.Many2many('hr.employee', 'evaluation_apprasial_manager_rel', 'hr_evaluation_evaluation_id')
    apprasial_manager_survey_id = fields.Many2one('survey.survey', required=False)
    appraisal_colleagues = fields.Boolean('Colleagues')
    appraisal_colleagues_ids = fields.Many2many('hr.employee', 'evaluation_appraisal_colleagues_rel', 'hr_evaluation_evaluation_id')
    appraisal_colleagues_survey_id = fields.Many2one('survey.survey')
    appraisal_self = fields.Boolean('Employee',)
    apprasial_employee = fields.Char('Employee Name',)
    appraisal_self_survey_id = fields.Many2one('survey.survey',string='self Appraisal',)
    appraisal_subordinates = fields.Boolean('Collaborator')
    appraisal_subordinates_ids = fields.Many2many('hr.employee', 'evaluation_appraisal_subordinates_rel', 'hr_evaluation_evaluation_id')
    appraisal_subordinates_survey_id = fields.Many2one('survey.survey',)
    color = fields.Integer('Color Index')
    display_name = fields.Char(compute='_set_display_name')
    mail_template = fields.Many2one('email.template', string="Email Template For Appraisal", default=_set_default_template)
    email_to = fields.Char('Appraisal Receiver', compute=_set_appraisal_url)
    appraisal_url = fields.Char('Appraisal URL', compute=_set_appraisal_url)
    send_mail_status = fields.Boolean('Appraisal Send Mail Status', compute=_set_appraisal_url)

    @api.one
    @api.depends('employee_id')
    def _set_display_name(self):
        for record in self:
            self.display_name = record.employee_id.name_related

    @api.one
    @api.onchange('employee_id')
    def onchange_employee_id(self):
        self.department_id = self.employee_id.department_id
        self.appraisal_manager = self.employee_id.appraisal_manager
        self.apprasial_manager_ids = self.employee_id.apprasial_manager_ids
        self.apprasial_manager_survey_id = self.employee_id.apprasial_manager_survey_id
        self.appraisal_colleagues = self.employee_id.appraisal_colleagues
        self.appraisal_colleagues_ids = self.employee_id.appraisal_colleagues_ids
        self.appraisal_colleagues_survey_id = self.employee_id.appraisal_colleagues_survey_id
        self.appraisal_self = self.employee_id.appraisal_self
        self.apprasial_employee = self.employee_id.name
        self.appraisal_self_survey_id = self.employee_id.appraisal_self_survey_id
        self.appraisal_subordinates = self.employee_id.appraisal_subordinates
        self.appraisal_subordinates_ids = self.employee_id.appraisal_subordinates_ids
        self.appraisal_subordinates_survey_id = self.employee_id.appraisal_subordinates_survey_id

    @api.one
    def create_message_subscribe_users_list(self, val):
        user_ids = [emp.user_id.id for rec in val for emp in rec if emp.user_id]
        if self.employee_id.user_id:
            user_ids.append(self.employee_id.user_id.id)
        return self.message_subscribe_users(user_ids=user_ids)

    @api.model
    def create(self, vals):
        res = super(hr_evaluation, self).create(vals)
        val = [res.apprasial_manager_ids,res.appraisal_colleagues_ids,res.appraisal_subordinates_ids]
        res.create_message_subscribe_users_list(val)
        return res

    @api.one
    def update_appraisal_url(self, url, email_to):
        self.appraisal_url = url
        self.email_to = email_to
        return True

    @api.one
    def create_receiver_list(self, apprasial, url):
        email_to = ''
        for rec in apprasial: 
            if rec.work_email: email_to += rec.work_email + ','
        self.update_appraisal_url(url, email_to)
        self.mail_template.send_mail(self.id, force_send=True)
        return True

    @api.one
    def button_sent_appraisal(self):
        if self.employee_id:
            if self.appraisal_manager and self.apprasial_manager_ids:
                self.create_receiver_list(self.apprasial_manager_ids, self.apprasial_manager_survey_id.public_url)
            if self.appraisal_colleagues and self.appraisal_colleagues_ids:
                self.create_receiver_list(self.appraisal_colleagues_ids, self.appraisal_colleagues_survey_id.public_url)
            if self.appraisal_subordinates and self.appraisal_subordinates_ids:
                self.create_receiver_list(self.appraisal_subordinates_ids, self.appraisal_subordinates_survey_id.public_url)
            if self.appraisal_self and self.apprasial_employee:
                self.create_receiver_list(self.employee_id, self.appraisal_self_survey_id.public_url)
            if self.state == 'new':
                self.write({'state': 'pending', 'send_mail_status': True})
        return True

    @api.one
    def button_done_appraisal(self):
        return self.write({'state': 'done'})

    @api.multi
    def write(self, vals):
        if vals.get('state') == 'pending' and not vals.get('send_mail_status'):
            self.button_sent_appraisal()
        return super(hr_evaluation, self).write(vals)

    @api.cr_uid_ids_context
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        """ Override read_group to always display all states. """
        if groupby and groupby[0] == "state":
            states = self._get_state_list(cr, uid, context=context)
            read_group_all_states = [{
                        '__context': {'group_by': groupby[1:]},
                        '__domain': domain + [('state', '=', state_value)],
                        'state': state_value,
                    } for state_value, state_name in states]
            read_group_res = super(hr_evaluation, self).read_group(cr, uid, domain, fields, groupby, offset, limit, context, orderby, lazy)
            result = []
            for state_value, state_name in states:
                res = filter(lambda x: x['state'] == state_value, read_group_res)
                if not res:
                    res = filter(lambda x: x['state'] == state_value, read_group_all_states)
                result.append(res[0])
            return result
        else:
            return super(hr_evaluation, self).read_group(cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby, lazy=lazy)

class hr_employee(models.Model):
    _name = "hr.employee"
    _inherit="hr.employee"

    evaluation_date = fields.Date('Next Appraisal Date', help="The date of the next appraisal is computed by the appraisal plan's dates (first appraisal + periodicity).")
    appraisal_manager = fields.Boolean('Manager', help="",)
    apprasial_manager_ids = fields.Many2many('hr.employee', 'apprasial_manager_rel', 'hr_evaluation_evaluation_id',)
    apprasial_manager_survey_id = fields.Many2one('survey.survey', 'Manager Appraisal',)
    appraisal_colleagues = fields.Boolean('Colleagues', help="")
    appraisal_colleagues_ids = fields.Many2many('hr.employee', 'appraisal_colleagues_rel', 'hr_evaluation_evaluation_id',)
    appraisal_colleagues_survey_id = fields.Many2one('survey.survey', "Employee's Appraisal", )
    appraisal_self = fields.Boolean('Employee', help="")
    apprasial_employee = fields.Char('Employee Name',)
    appraisal_self_survey_id = fields.Many2one('survey.survey', 'self Appraisal',)
    appraisal_subordinates = fields.Boolean('Collaborator', help="")
    appraisal_subordinates_ids = fields.Many2many('hr.employee', 'appraisal_subordinates_rel', 'hr_evaluation_evaluation_id')
    appraisal_subordinates_survey_id = fields.Many2one('survey.survey', "Employee's Appraisal" )
    appraisal_repeat = fields.Boolean('Repeat', help="", default=False)
    appraisal_repeat_number = fields.Integer('Appraisal Cycle', default=1,)
    appraisal_repeat_delay = fields.Selection([('year','Year'),('month','Month')], 'Repeat Every', copy=False, default='year',)
    appraisal_count = fields.Integer(compute='_appraisal_count', string='Appraisal Interviews')

    @api.one
    def _appraisal_count(self):
        Evaluation = self.env['hr_evaluation.evaluation']
        for rec in self:
            self.appraisal_count = Evaluation.search_count([('employee_id', '=', rec.id)],)

    @api.one
    @api.onchange('appraisal_manager')
    def onchange_manager_appraisal(self):
        self.apprasial_manager_ids = [self.parent_id.id]

    @api.one
    @api.onchange('appraisal_self')
    def onchange_self_employee(self):
        self.apprasial_employee = self.name

    @api.cr_uid_ids_context
    def run_employee_evaluation(self, cr, uid, automatic=False, use_new_cursor=False, context=None):  # cronjob
        now = parser.parse(datetime.now().strftime('%Y-%m-%d'))
        obj_evaluation = self.pool.get('hr_evaluation.evaluation')
        next_date = datetime.now()
        emp_ids = self.search(cr, uid, [('evaluation_date', '<=', time.strftime("%Y-%m-%d"))], context=context)
        for emp in self.browse(cr, uid, emp_ids, context=context):
            if emp.appraisal_repeat_delay == 'month':
                next_date = (now + relativedelta(months=emp.appraisal_repeat_number)).strftime('%Y-%m-%d')
            else:
                next_date = (now + relativedelta(months=emp.appraisal_repeat_number * 12)).strftime('%Y-%m-%d')
            self.write(cr, uid, [emp.id], {'evaluation_date': next_date}, context=context)
            vals = {'employee_id': emp.id,
                    'appraisal_manager': emp.appraisal_manager,
                    'apprasial_manager_ids': [(4,manager.id) for manager in emp.apprasial_manager_ids],
                    'apprasial_manager_survey_id' : emp.apprasial_manager_survey_id.id,
                    'appraisal_colleagues': emp.appraisal_colleagues,
                    'appraisal_colleagues_ids': [(4,colleagues.id) for colleagues in emp.appraisal_colleagues_ids],
                    'appraisal_colleagues_survey_id': emp.appraisal_colleagues_survey_id.id,
                    'appraisal_self': emp.appraisal_self,
                    'apprasial_employee_id': emp.id,
                    'appraisal_self_survey_id': emp.appraisal_self_survey_id.id,
                    'appraisal_subordinates': emp.appraisal_subordinates,
                    'appraisal_subordinates_ids': [(4,subordinates.id) for subordinates in emp.appraisal_subordinates_ids],
                    'appraisal_subordinates_survey_id': emp.appraisal_subordinates_survey_id.id
            }
            obj_evaluation.create(cr, uid, vals, context=context)
        return True

