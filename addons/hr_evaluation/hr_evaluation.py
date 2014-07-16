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

class hr_evaluationStage(models.Model):
    _name = 'hr_evaluation.stage'
    _description = 'Evaluation Stage'
    _order = 'sequence'

    sequence = fields.Integer('Sequence')
    name = fields.Char('Stage Name', required=True, translate=True)

class hr_evaluation(models.Model):
    _name = "hr_evaluation.evaluation"
    _inherit = ['mail.thread']
    _description = "Employee Appraisal"

    @api.model
    def _get_default_stage_id(self):
        """ Gives default stage_id """
        stage_obj = self.env['hr_evaluation.stage']
        ids = stage_obj.search([])
        return ids and ids[0] or False

    interview_deadline = fields.Date("Final Interview", select=True)
    employee_id = fields.Many2one('hr.employee', required=True, string='Employee')
    department_id = fields.Many2one('hr.department', 'Department')
    note_summary = fields.Text('Appraisal Summary')
    evaluation = fields.Text('Evaluation Summary', help="If the evaluation does not meet the expectations, you can propose an action plan")
    stage_id = fields.Many2one('hr_evaluation.stage', 'Status', readonly=True, copy=False, default=_get_default_stage_id)
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
#    def button_plan_in_progress(self, cr, uid, ids, context=None):
#        hr_eval_inter_obj = self.pool.get('hr.evaluation.interview')
#        if context is None:
#            context = {}
#        for evaluation in self.browse(cr, uid, ids, context=context):
#            wait = False
#            for phase in evaluation.plan_id.phase_ids:
#                children = []
#                if phase.action == "bottom-up":
#                    children = evaluation.employee_id.child_ids
#                elif phase.action in ("top-down", "final"):
#                    if evaluation.employee_id.parent_id:
#                        children = [evaluation.employee_id.parent_id]
#                elif phase.action == "self":
#                    children = [evaluation.employee_id]
#                for child in children:
#
#                    int_id = hr_eval_inter_obj.create(cr, uid, {
#                        'evaluation_id': evaluation.id,
#                        'phase_id': phase.id,
#                        'deadline': (parser.parse(datetime.now().strftime('%Y-%m-%d')) + relativedelta(months=+1)).strftime('%Y-%m-%d'),
#                        'user_id': child.user_id.id,
#                    }, context=context)
#                    if phase.wait:
#                        wait = True
#                    if not wait:
#                        hr_eval_inter_obj.survey_req_waiting_answer(cr, uid, [int_id], context=context)
#
#                    if (not wait) and phase.mail_feature:
#                        body = phase.mail_body % {'employee_name': child.name, 'user_signature': child.user_id.signature,
#                            'eval_name': phase.survey_id.title, 'date': time.strftime('%Y-%m-%d'), 'time': time}
#                        sub = phase.email_subject
#                        if child.work_email:
#                            vals = {'state': 'outgoing',
#                                    'subject': sub,
#                                    'body_html': '<pre>%s</pre>' % body,
#                                    'email_to': child.work_email,
#                                    'email_from': evaluation.employee_id.work_email}
#                            self.pool.get('mail.mail').create(cr, uid, vals, context=context)
#
#        self.write(cr, uid, ids, {'state': 'wait'}, context=context)
#        return True
#
#    def button_final_validation(self, cr, uid, ids, context=None):
#        request_obj = self.pool.get('hr.evaluation.interview')
#        self.write(cr, uid, ids, {'state': 'progress'}, context=context)
#        for evaluation in self.browse(cr, uid, ids, context=context):
#            if evaluation.employee_id and evaluation.employee_id.parent_id and evaluation.employee_id.parent_id.user_id:
#                self.message_subscribe_users(cr, uid, [evaluation.id], user_ids=[evaluation.employee_id.parent_id.user_id.id], context=context)
#            if len(evaluation.survey_request_ids) != len(request_obj.search(cr, uid, [('evaluation_id', '=', evaluation.id), ('state', 'in', ['done', 'cancel'])], context=context)):
#                raise osv.except_osv(_('Warning!'), _("You cannot change state, because some appraisal forms have not been completed."))
#        return True
#
#    def button_done(self, cr, uid, ids, context=None):
#        self.write(cr, uid, ids, {'state': 'done', 'date_close': time.strftime('%Y-%m-%d')}, context=context)
#        return True
#
#    def button_cancel(self, cr, uid, ids, context=None):
#        interview_obj = self.pool.get('hr.evaluation.interview')
#        evaluation = self.browse(cr, uid, ids[0], context)
#        interview_obj.survey_req_cancel(cr, uid, [r.id for r in evaluation.survey_request_ids])
#        self.write(cr, uid, ids, {'state': 'cancel'}, context=context)
#        return True
#
#    def button_draft(self, cr, uid, ids, context=None):
#        self.write(cr, uid, ids, {'state': 'draft'}, context=context)
#        return True
#
#    def write(self, cr, uid, ids, vals, context=None):
#        if vals.get('employee_id'):
#            employee_id = self.pool.get('hr.employee').browse(cr, uid, vals.get('employee_id'), context=context)
#            if employee_id.parent_id and employee_id.parent_id.user_id:
#                vals['message_follower_ids'] = [(4, employee_id.parent_id.user_id.partner_id.id)]
#        if 'date' in vals:
#            new_vals = {'deadline': vals.get('date')}
#            obj_hr_eval_iterview = self.pool.get('hr.evaluation.interview')
#            for evaluation in self.browse(cr, uid, ids, context=context):
#                for survey_req in evaluation.survey_request_ids:
#                    obj_hr_eval_iterview.write(cr, uid, [survey_req.id], new_vals, context=context)
#        return super(hr_evaluation, self).write(cr, uid, ids, vals, context=context)

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
    @api.depends('parent_id','coach_id')
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

    @api.one
    def _appraisal_count(self):
        Evaluation = self.env['hr_evaluation.evaluation']
        for rec in self:
            self.appraisal_count = Evaluation.search_count([('employee_id', '=', rec.id)],)


#        for i in self:
#            print i
        #return {
       #     employee_id: Evaluation.search_count([('employee_id', '=', 1)],)
       #     for employee_id in self
        #}
#    def run_employee_evaluation(self, cr, uid, automatic=False, use_new_cursor=False, context=None):  # cronjob
#        now = parser.parse(datetime.now().strftime('%Y-%m-%d'))
#        obj_evaluation = self.pool.get('hr_evaluation.evaluation')
#        emp_ids = self.search(cr, uid, [('evaluation_plan_id', '<>', False), ('evaluation_date', '=', False)], context=context)
#        for emp in self.browse(cr, uid, emp_ids, context=context):
#            first_date = (now + relativedelta(months=emp.evaluation_plan_id.month_first)).strftime('%Y-%m-%d')
#            self.write(cr, uid, [emp.id], {'evaluation_date': first_date}, context=context)
#
#        emp_ids = self.search(cr, uid, [('evaluation_plan_id', '<>', False), ('evaluation_date', '<=', time.strftime("%Y-%m-%d"))], context=context)
#        for emp in self.browse(cr, uid, emp_ids, context=context):
#            next_date = (now + relativedelta(months=emp.evaluation_plan_id.month_next)).strftime('%Y-%m-%d')
#            self.write(cr, uid, [emp.id], {'evaluation_date': next_date}, context=context)
#            plan_id = obj_evaluation.create(cr, uid, {'employee_id': emp.id, 'plan_id': emp.evaluation_plan_id.id}, context=context)
#            obj_evaluation.button_plan_in_progress(cr, uid, [plan_id], context=context)
#        return True





#class hr_evaluation_interview(osv.Model):
#    _name = 'hr.evaluation.interview'
#    _inherit = 'mail.thread'
#    _rec_name = 'user_to_review_id'
#    _description = 'Appraisal Interview'
#    _columns = {
#        'request_id': fields.many2one('survey.user_input', 'Survey Request', ondelete='cascade', readonly=True),
#        'evaluation_id': fields.many2one('hr_evaluation.evaluation', 'Appraisal Plan', required=True),
#        'phase_id': fields.many2one('hr_evaluation.plan.phase', 'Appraisal Phase', required=True),
#        'user_to_review_id': fields.related('evaluation_id', 'employee_id', type="many2one", relation="hr.employee", string="Employee to evaluate"),
#        'user_id': fields.many2one('res.users', 'Interviewer'),
#        'state': fields.selection([('draft', "Draft"),
#                                   ('waiting_answer', "In progress"),
#                                   ('done', "Done"),
#                                   ('cancel', "Cancelled")],
#                                  string="State", required=True, copy=False),
#        'survey_id': fields.related('phase_id', 'survey_id', string="Appraisal Form", type="many2one", relation="survey.survey"),
#        'deadline': fields.related('request_id', 'deadline', type="datetime", string="Deadline"),
#    }
#    _defaults = {
#        'state': 'draft'
#    }
#
#    def create(self, cr, uid, vals, context=None):
#        phase_obj = self.pool.get('hr_evaluation.plan.phase')
#        survey_id = phase_obj.read(cr, uid, vals.get('phase_id'), fields=['survey_id'], context=context)['survey_id'][0]
#
#        if vals.get('user_id'):
#            user_obj = self.pool.get('res.users')
#            partner_id = user_obj.read(cr, uid, vals.get('user_id'), fields=['partner_id'], context=context)['partner_id'][0]
#        else:
#            partner_id = None
#
#        user_input_obj = self.pool.get('survey.user_input')
#
#        if not vals.get('deadline'):
#            vals['deadline'] = (datetime.now() + timedelta(days=28)).strftime(DF)
#
#        ret = user_input_obj.create(cr, uid, {'survey_id': survey_id,
#                                              'deadline': vals.get('deadline'),
#                                              'type': 'link',
#                                              'partner_id': partner_id}, context=context)
#        vals['request_id'] = ret
#        return super(hr_evaluation_interview, self).create(cr, uid, vals, context=context)
#
#    def name_get(self, cr, uid, ids, context=None):
#        if not ids:
#            return []
#        reads = self.browse(cr, uid, ids, context=context)
#        res = []
#        for record in reads:
#            name = record.survey_id.title
#            res.append((record['id'], name))
#        return res
#
#    def survey_req_waiting_answer(self, cr, uid, ids, context=None):
#        request_obj = self.pool.get('survey.user_input')
#        for interview in self.browse(cr, uid, ids, context=context):
#            request_obj.action_survey_resent(cr, uid, [interview.id], context=context)
#            self.write(cr, uid, interview.id, {'state': 'waiting_answer'}, context=context)
#        return True
#
#    def survey_req_done(self, cr, uid, ids, context=None):
#        for id in self.browse(cr, uid, ids, context=context):
#            flag = False
#            wating_id = 0
#            if not id.evaluation_id.id:
#                raise osv.except_osv(_('Warning!'), _("You cannot start evaluation without Appraisal."))
#            records = id.evaluation_id.survey_request_ids
#            for child in records:
#                if child.state == "draft":
#                    wating_id = child.id
#                    continue
#                if child.state != "done":
#                    flag = True
#            if not flag and wating_id:
#                self.survey_req_waiting_answer(cr, uid, [wating_id], context=context)
#        self.write(cr, uid, ids, {'state': 'done'}, context=context)
#        return True
#
#    def survey_req_cancel(self, cr, uid, ids, context=None):
#        self.write(cr, uid, ids, {'state': 'cancel'}, context=context)
#        return True
#
#    def action_print_survey(self, cr, uid, ids, context=None):
#        """ If response is available then print this response otherwise print survey form (print template of the survey) """
#        context = dict(context or {})
#        interview = self.browse(cr, uid, ids, context=context)[0]
#        survey_obj = self.pool.get('survey.survey')
#        response_obj = self.pool.get('survey.user_input')
#        response = response_obj.browse(cr, uid, interview.request_id.id, context=context)
#        context.update({'survey_token': response.token})
#        return survey_obj.action_print_survey(cr, uid, [interview.survey_id.id], context=context)
#
#    def action_start_survey(self, cr, uid, ids, context=None):
#        context = dict(context or {})
#        interview = self.browse(cr, uid, ids, context=context)[0]
#        survey_obj = self.pool.get('survey.survey')
#        response_obj = self.pool.get('survey.user_input')
#        # grab the token of the response and start surveying
#        response = response_obj.browse(cr, uid, interview.request_id.id, context=context)
#        context.update({'survey_token': response.token})
#        return survey_obj.action_start_survey(cr, uid, [interview.survey_id.id], context=context)
