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
#from openerp.osv import osv, orm
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DF


class hr_evaluation(models.Model):
    _name = "hr_evaluation.evaluation"
    _inherit = ['mail.thread']
    _description = "Employee Appraisal"


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
    appraisal_manager = fields.Boolean(string='Manger', store=True, related='employee_id.appraisal_manager', readonly=True)
    apprasial_manager_ids = fields.Many2many('hr.employee', related='employee_id.apprasial_manager_ids', readonly=True)
    apprasial_manager_survey_id = fields.Many2one('survey.survey', store=True, related='employee_id.apprasial_manager_survey_id', readonly=True)
    appraisal_colleagues = fields.Boolean( string='Colleagues', store=True, related='employee_id.appraisal_colleagues', readonly=True)
    appraisal_colleagues_ids = fields.Many2many('hr.employee', related='employee_id.appraisal_colleagues_ids', readonly=True)
    appraisal_colleagues_survey_id = fields.Many2one('survey.survey', store=True, related='employee_id.appraisal_colleagues_survey_id', readonly=True)
    appraisal_self = fields.Boolean(string='Employee', store=True, related='employee_id.appraisal_self', readonly=True)
    apprasial_employee_id = fields.Many2one('hr.employee', store=True, related='employee_id.apprasial_employee_id', readonly=True)
    appraisal_self_survey_id = fields.Many2one('survey.survey', store=True, related='employee_id.appraisal_self_survey_id', string='self Appraisal', readonly=True)
    appraisal_subordinates = fields.Boolean(string='Collaborator', store=True, related='employee_id.appraisal_subordinates', readonly=True)
    appraisal_subordinates_ids = fields.Many2many('hr.employee', related='employee_id.appraisal_subordinates_ids', readonly=True)
    appraisal_subordinates_survey_id = fields.Many2one('survey.survey', store=True, related='employee_id.appraisal_subordinates_survey_id', readonly=True)
    color = fields.Integer('Color Index')
    display_name = fields.Char(compute='_set_display_name')

    @api.one
    @api.depends('employee_id')
    def _set_display_name(self):
        for record in self:
            self.display_name = record.employee_id.name_related

    @api.one
    @api.onchange('employee_id')
    def onchange_employee_id(self):
        self.apprasial_employee_id = self.employee_id
        self.department_id = self.employee_id.department_id

    def _read_group_stage_ids(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context=None):
        stage_obj = self.pool.get('hr_evaluation.stage')
        stage_ids = stage_obj.search(cr, uid, [], context=context)
        result = stage_obj.name_get(cr, uid, stage_ids, context=context)
        return result, {}

    _group_by_full = {'stage_id': _read_group_stage_ids,}

class hr_employee(models.Model):
    _name = "hr.employee"
    _inherit="hr.employee"

    evaluation_date = fields.Date('Next Appraisal Date', help="The date of the next appraisal is computed by the appraisal plan's dates (first appraisal + periodicity).")
    appraisal_manager = fields.Boolean('Manager', help="",)
    apprasial_manager_ids = fields.Many2many('hr.employee', 'apprasial_manager_rel', 'hr_evaluation_evaluation_id', compute='_appraisal_manager')

    @api.one
    @api.depends('parent_id','coach_id')
    def _appraisal_manager(self):
        self.apprasial_manager_ids = [self.parent_id.id , self.coach_id.id]

    apprasial_manager_survey_id = fields.Many2one('survey.survey', 'Manager Appraisal',)
    appraisal_colleagues = fields.Boolean('Colleagues', help="")
    appraisal_colleagues_ids = fields.Many2many('hr.employee', 'appraisal_colleagues_rel', 'hr_evaluation_evaluation_id', compute='_appraisal_colleagues')

    @api.one
    def _appraisal_colleagues(self):
        colleagues = self.search([('parent_id', '=', self.parent_id.id),('coach_id', '=', self.coach_id.id)])
        if colleagues:
            self.appraisal_colleagues_ids = [rec.id for rec in colleagues]

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
