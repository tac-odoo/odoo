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

    @api.one
    def _set_default_template(self):
        model, template_id = self.env['ir.model.data'].get_object_reference('hr_evaluation', 'email_template_appraisal')
        return template_id

    @api.one
    def _set_servey_link(self,):
        self.survey_link = ''
        self.email_list = ''

    interview_deadline = fields.Date("Final Interview", select=True)
    employee_id = fields.Many2one('hr.employee', required=True, string='Employee')
    department_id = fields.Many2one('hr.department', 'Department')
    note_summary = fields.Text('Appraisal Summary')
    evaluation = fields.Text('Evaluation Summary', help="If the evaluation does not meet the expectations, you can propose an action plan")
    state = fields.Selection([
            ('new', 'To Start'),
            ('pending', 'Appraisal Sent'),
            ('done', 'Done'),
    ], 'Status', required=True, readonly=True, copy=False, default='new')
    date_close = fields.Date('Appraisal Deadline', select=True)
    appraisal_manager = fields.Boolean('Manger',)
    apprasial_manager_ids = fields.Many2many('hr.employee', 'evaluation_apprasial_manager_rel', 'hr_evaluation_evaluation_id')
    apprasial_manager_survey_id = fields.Many2one('survey.survey', required=False)
    appraisal_colleagues = fields.Boolean('Colleagues')
    appraisal_colleagues_ids = fields.Many2many('hr.employee', 'evaluation_appraisal_colleagues_rel', 'hr_evaluation_evaluation_id')
    appraisal_colleagues_survey_id = fields.Many2one('survey.survey')
    appraisal_self = fields.Boolean('Employee')
    apprasial_employee_id = fields.Many2one('hr.employee')
    appraisal_self_survey_id = fields.Many2one('survey.survey',string='self Appraisal',)
    appraisal_subordinates = fields.Boolean('Collaborator')
    appraisal_subordinates_ids = fields.Many2many('hr.employee', 'evaluation_appraisal_subordinates_rel', 'hr_evaluation_evaluation_id')
    appraisal_subordinates_survey_id = fields.Many2one('survey.survey',)
    color = fields.Integer('Color Index')
    display_name = fields.Char(compute='_set_display_name')
    mail_template = fields.Many2one('email.template', string="Email Template For Appraisal", default=_set_default_template)
    email_list = fields.Char('Receiver', compute=_set_servey_link)
    survey_link = fields.Char('Link', compute=_set_servey_link)

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
        self.apprasial_employee_id = self.employee_id
        self.appraisal_self_survey_id = self.employee_id.appraisal_self_survey_id
        self.appraisal_subordinates = self.employee_id.appraisal_subordinates
        self.appraisal_subordinates_ids = self.employee_id.appraisal_subordinates_ids
        self.appraisal_subordinates_survey_id = self.employee_id.appraisal_subordinates_survey_id

    @api.cr_uid_ids_context
    def update_survey_link(self, cr, uid, ids, link, email_to, context=None):
        for rec in self.browse(cr, uid, ids, context):
            rec.survey_link = link
            rec.email_list = email_to
        return True

    @api.cr_uid_ids_context
    def button_sent_appraisal(self, cr, uid, ids, context=None):
        template_obj = self.pool.get('email.template')
        for evaluation in self.browse(cr, uid, ids, context=context):
            if evaluation.employee_id:
                if evaluation.appraisal_manager and evaluation.apprasial_manager_survey_id:
                    email_to = ''
                    for rec in evaluation.apprasial_manager_ids: email_to += rec.work_email + ','
                    self.update_survey_link(cr, uid, [evaluation.id], evaluation.apprasial_manager_survey_id.public_url, email_to, context)
                    template_obj.send_mail(cr, uid, evaluation.mail_template.id, evaluation.id, force_send=True, context=context)
                if evaluation.appraisal_colleagues and evaluation.appraisal_colleagues_ids:
                    email_to = ''
                    for rec in evaluation.appraisal_colleagues_ids: email_to += rec.work_email + ','
                    self.update_survey_link(cr, uid, [evaluation.id], evaluation.appraisal_colleagues_survey_id.public_url, email_to, context)
                    template_obj.send_mail(cr, uid, evaluation.mail_template.id, evaluation.id, force_send=True, context=context)
                if evaluation.appraisal_subordinates and evaluation.appraisal_subordinates_ids:
                    email_to = ''
                    for rec in evaluation.appraisal_subordinates_ids: email_to += rec.work_email + ','
                    self.update_survey_link(cr, uid, [evaluation.id], evaluation.appraisal_subordinates_survey_id.public_url, email_to, context)
                    template_obj.send_mail(cr, uid, evaluation.mail_template.id, evaluation.id, force_send=True, context=context)
                if evaluation.appraisal_self and evaluation.apprasial_employee_id:
                    email_to = ''
                    for rec in evaluation.apprasial_employee_id: email_to += rec.work_email + ','
                    self.update_survey_link(cr, uid, [evaluation.id], evaluation.appraisal_self_survey_id.public_url, email_to, context)
                    template_obj.send_mail(cr, uid, evaluation.mail_template.id, evaluation.id, force_send=True, context=context)
            self.write(cr, uid, [evaluation.id], {'state': 'pending'})
        return True

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
    apprasial_employee_id = fields.Many2one('hr.employee', 'Employee', readonly=True)
    appraisal_self_survey_id = fields.Many2one('survey.survey', 'self Appraisal',)
    appraisal_subordinates = fields.Boolean('Collaborator', help="")
    appraisal_subordinates_ids = fields.Many2many('hr.employee', 'appraisal_subordinates_rel', 'hr_evaluation_evaluation_id')
    appraisal_subordinates_survey_id = fields.Many2one('survey.survey', "Employee's Appraisal" )
    appraisal_repeat = fields.Boolean('Repeat', help="")
    appraisal_repeat_number = fields.Integer('Repeat')
    appraisal_repeat_delay = fields.Selection([('year','Year'),('month','Month')], 'Repeat Delay', copy=False)
    date_from = fields.Date('From', select=True)
    appraisal_count = fields.Integer(compute='_appraisal_count', string='Appraisal Interviews')
    #user_id = fields.Many2one('res.users','employee_ids',)
    @api.one
    def _appraisal_count(self):
        Evaluation = self.env['hr_evaluation.evaluation']
        for rec in self:
            self.appraisal_count = Evaluation.search_count([('employee_id', '=', rec.id)],)
