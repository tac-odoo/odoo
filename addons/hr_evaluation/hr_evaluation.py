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
import uuid
import urlparse
from openerp import fields, api, tools, models
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp.exceptions import except_orm, Warning

class calendar_event(models.Model):
    """ Model for Calendar Event """
    _inherit = 'calendar.event'

    @api.model
    def create(self, vals):
        res = super(calendar_event, self).create(vals)
        if self.env.context.get('active_model') == 'hr_evaluation.evaluation':
            evaluation_obj = self.env['hr_evaluation.evaluation'].browse(self.env.context.get('active_id', []))
            evaluation_obj.log_meeting(res.name, res.start, res.duration)
            evaluation_obj.write({'meeting_id': res.id, 'interview_deadline': res.start_date if res.allday else res.start_datetime})
        return res

class survey_user_input(models.Model):
    _inherit = "survey.user_input"

    evaluation_id = fields.Many2one('hr_evaluation.evaluation', string='Appraisal')

    @api.multi
    def write(self, vals):
        """ Trigger the _get_tot_completed_appraisal method when user fill up the appraisal form
            and update kanban image gauge in employee evaluation.
        """
        res = super(survey_user_input, self).write(vals)
        if vals.get('state'):
            self.sudo().evaluation_id._get_tot_completed_appraisal()
        return res

class hr_evaluation(models.Model):
    _name = "hr_evaluation.evaluation"
    _inherit = ['mail.thread']
    _description = "Employee Appraisal"

    EVALUATION_STATE = [
        ('new', 'To Start'),
        ('pending', 'Appraisal Sent'),
        ('done', 'Done')
    ]

    @api.one
    def _set_default_template(self):
        model, template_id = self.env['ir.model.data'].get_object_reference('hr_evaluation', 'email_template_appraisal')
        return template_id

    @api.one
    def _set_appraisal_url(self):
        self.appraisal_url = ''
        self.email_to = ''

    @api.one
    @api.depends('state','interview_deadline')
    def _get_tot_sent_appraisal(self):
        sur_res_obj = self.env['survey.user_input']
        self.tot_sent_appraisal = sur_res_obj.search_count([
                                  ('survey_id', 'in', [self.apprasial_manager_survey_id.id, self.appraisal_colleagues_survey_id.id, self.appraisal_self_survey_id.id, self.appraisal_subordinates_survey_id.id]),
                                  ('type', '=', 'link'), ('deadline','=', self.date_close),
                                  ('evaluation_id','=',self.id)])

    @api.one
    def _get_tot_completed_appraisal(self):
        sur_res_obj = self.env['survey.user_input']
        self.tot_comp_appraisal = sur_res_obj.search_count([
                                  ('survey_id', 'in', [self.apprasial_manager_survey_id.id, self.appraisal_colleagues_survey_id.id, self.appraisal_self_survey_id.id, self.appraisal_subordinates_survey_id.id]),
                                  ('type', '=', 'link'), ('deadline','=', self.date_close), ('state', '=', 'done'),
                                  ('evaluation_id','=',self.id)])

    meeting_id = fields.Many2one('calendar.event', 'Meeting')
    interview_deadline = fields.Date("Final Interview", select=True)
    employee_id = fields.Many2one('hr.employee', required=True, string='Employee')
    department_id = fields.Many2one('hr.department', 'Department')
    evaluation = fields.Text('Evaluation Summary', help="If the evaluation does not meet the expectations, you can propose an action plan")
    state = fields.Selection(EVALUATION_STATE, 'Status', track_visibility='onchange', required=True, readonly=True, copy=False, default='new', select=True)
    date_close = fields.Date('Appraisal Deadline', select=True, required=True)
    appraisal_manager = fields.Boolean('Manger',)
    apprasial_manager_ids = fields.Many2many('hr.employee', 'evaluation_apprasial_manager_rel', 'hr_evaluation_evaluation_id')
    apprasial_manager_survey_id = fields.Many2one('survey.survey', 'Manager Appraisal', required=False)
    appraisal_colleagues = fields.Boolean('Colleagues')
    appraisal_colleagues_ids = fields.Many2many('hr.employee', 'evaluation_appraisal_colleagues_rel', 'hr_evaluation_evaluation_id')
    appraisal_colleagues_survey_id = fields.Many2one('survey.survey', "Employee's Appraisal")
    appraisal_self = fields.Boolean('Employee',)
    apprasial_employee = fields.Char('Employee Name',)
    appraisal_self_survey_id = fields.Many2one('survey.survey',string='Self Appraisal',)
    appraisal_subordinates = fields.Boolean('Collaborator')
    appraisal_subordinates_ids = fields.Many2many('hr.employee', 'evaluation_appraisal_subordinates_rel', 'hr_evaluation_evaluation_id')
    appraisal_subordinates_survey_id = fields.Many2one('survey.survey', "collaborate's Appraisal")
    color = fields.Integer('Color Index')
    display_name = fields.Char(compute='_set_display_name')
    mail_template = fields.Many2one('email.template', string="Email Template For Appraisal", default=_set_default_template)
    email_to = fields.Char('Appraisal Receiver', compute='_set_appraisal_url')
    appraisal_url = fields.Char('Appraisal URL', compute='_set_appraisal_url')
    tot_sent_appraisal = fields.Integer('Number of sent appraisal', compute='_get_tot_sent_appraisal', defualt=0, store=True)
    tot_comp_appraisal = fields.Integer('Number of completed appraisal', defualt=0)
    user_id = fields.Many2one('res.users', string='Related User', default=lambda self: self.env.uid)

    @api.one
    @api.depends('employee_id')
    def _set_display_name(self):
        self.display_name = self.employee_id.name_related

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
    @api.constrains('employee_id', 'department_id', 'date_close')
    def _check_employee_appraisal_duplication(self):
        """ Avoid duplication"""
        if self.employee_id and self.department_id and self.date_close:
            appraisal_ids = self.search([('employee_id', '=', self.employee_id.id),('department_id', '=', self.department_id.id)])
            if appraisal_ids:
                duplicat_list = [(datetime.strptime(rec.date_close, DEFAULT_SERVER_DATE_FORMAT).month,datetime.strptime(rec.date_close, DEFAULT_SERVER_DATE_FORMAT).year) for rec in appraisal_ids]
                found_duplicat_data = []
                for rec in duplicat_list:
                    if rec in found_duplicat_data:
                        raise except_orm(_('Warning'),_("You cannot create more than one appraisal for same Month & Year"))
                    else:
                        found_duplicat_data.append(rec)
        else:
            return True

    @api.one
    def create_message_subscribe_users_list(self, val):
        user_ids = [emp.user_id.id for rec in val for emp in rec if emp.user_id]
        if self.employee_id.user_id:
            user_ids.append(self.employee_id.user_id.id)
        if self.employee_id.department_id.manager_id.user_id:
            user_ids.append(self.employee_id.department_id.manager_id.user_id.id)
        if self.employee_id.parent_id.user_id:
            user_ids.append(self.employee_id.parent_id.user_id.id)
        return self.message_subscribe_users(user_ids=user_ids)

    @api.model
    def create(self, vals):
        res = super(hr_evaluation, self).create(vals)
        res.create_message_subscribe_users_list([res.apprasial_manager_ids])
        return res

    @api.one
    def update_appraisal_url(self, url, email_to, token):
        url = urlparse.urlparse(url).path[1:]
        if token:
            url = url + '/' + token
        self.appraisal_url = url
        self.email_to = email_to
        return True

    @api.one
    def create_token(self, email, url, partner_id):
        """ Create response with token """
        survey_response_obj = self.env['survey.user_input']
        token = uuid.uuid4().__str__()
        survey_response_obj.create({
            'survey_id': url.id,
            'deadline': self.date_close,
            'date_create': datetime.now(),
            'type': 'link',
            'state': 'new',
            'token': token,
            'evaluation_id': self.id,
            'partner_id': partner_id.id if partner_id else None,
            'email': email})
        return token

    @api.one
    def create_receiver_list(self, apprasial):
        """ Create one mail by recipients and __URL__ by link with identification token """
        mail_obj = self.env['mail.thread']
        for rec in apprasial:
            for emp in rec[1]:
                if emp.work_email:
                    email = tools.email_split(emp.work_email)[0]
                    partner_id = mail_obj._find_partner_from_emails(email) or emp.user_id.partner_id or None
                    token = self.create_token(email, rec[0], partner_id)[0]
                    self.update_appraisal_url(rec[0].public_url, email, token)
                    self.mail_template.send_mail(self.id, force_send=True)
        return True

    @api.one
    def button_sent_appraisal(self):
        """ Changes To Start state to Appraisal Sent.
        @return: True
        """
        if self.employee_id:
            appraisal_receiver = []
            if self.appraisal_manager and self.apprasial_manager_ids:
                appraisal_receiver.append((self.apprasial_manager_survey_id,self.apprasial_manager_ids))
            if self.appraisal_colleagues and self.appraisal_colleagues_ids:
                appraisal_receiver.append((self.appraisal_colleagues_survey_id,self.appraisal_colleagues_ids))
            if self.appraisal_subordinates and self.appraisal_subordinates_ids:
                appraisal_receiver.append((self.appraisal_subordinates_survey_id,self.appraisal_subordinates_ids))
            if self.appraisal_self and self.apprasial_employee:
                appraisal_receiver.append((self.appraisal_self_survey_id,self.employee_id))
            self.create_receiver_list(appraisal_receiver)
            if self.state == 'new':
                self.with_context(send_mail_status=True).write({'state': 'pending'})#avoid recursive process
        return True

    @api.one
    def button_done_appraisal(self):
        """ Changes Appraisal Sent state to Done.
        @return: True
        """
        return self.write({'state': 'done'})

    @api.multi
    def create_update_meeting(self, vals):
        """ Creates event when user enters date manually from the form view.
            If users edits the already entered date, created meeting is updated accordingly.
        """
        create_meeting_id = False
        if self.meeting_id and self.meeting_id.allday:
            self.meeting_id.write({'start_date': vals['interview_deadline'], 'stop_date': vals['interview_deadline']})
        elif self.meeting_id and not self.meeting_id.allday:
            date_obj = datetime.strptime(vals['interview_deadline'], DEFAULT_SERVER_DATE_FORMAT)
            set_date = datetime.strftime(date_obj, DEFAULT_SERVER_DATETIME_FORMAT)
            self.meeting_id.write({'start_datetime': set_date, 'stop_datetime': set_date})
        else:
            partner_ids = [(4,manager.user_id.partner_id.id) for manager in self.apprasial_manager_ids if manager.user_id]
            if self.employee_id.user_id:
                partner_ids.append((4,self.employee_id.user_id.partner_id.id))
            create_meeting_id = self.env['calendar.event'].create({
                'name': _('Appraisal Meeting For ') + self.employee_id.name_related,
                'start': vals['interview_deadline'],
                'stop': vals['interview_deadline'],
                'allday': True,
                'partner_ids': partner_ids,
                }
            )
            if create_meeting_id:
                self.meeting_id = create_meeting_id
        return self.log_meeting(self.meeting_id.name, self.meeting_id.start, self.meeting_id.duration)

    @api.multi
    @api.depends('employee_id')
    def name_get(self):
        result = []
        for hr_evaluation in self:
            result.append((hr_evaluation.id, '%s' % (hr_evaluation.employee_id.name_related)))
        return result

    @api.multi
    def write(self, vals):
        if vals.get('state') == 'pending' and not self.env.context.get('send_mail_status'): #avoid recursive process
            self.button_sent_appraisal()
        if vals.get('interview_deadline') and not vals.get('meeting_id'):
            if datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT) > vals.get('interview_deadline'):
                raise Warning(_("The interview date can not be in the past"))
            self.create_update_meeting(vals) #creating employee meeting and interview date
        if vals.get('apprasial_manager_ids'):
            emp_obj = self.env['hr.employee']
            # add followers
            for follower_id in emp_obj.browse(vals['apprasial_manager_ids'][0][2]):
                if follower_id.user_id:
                    self.message_subscribe_users(user_ids=[follower_id.user_id.id])
        return super(hr_evaluation, self).write(vals)

    @api.multi
    def unlink(self):
        for appraisal in self:
            if appraisal.state != 'new':
                eva_state = dict(self.EVALUATION_STATE)
                raise Warning(_("You cannot delete appraisal which is in '%s' state") % (eva_state[appraisal.state]))
        return super(hr_evaluation, self).unlink()

    @api.cr_uid_ids_context
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        """ Override read_group to always display all states. """
        if groupby and groupby[0] == "state":
            states = self.EVALUATION_STATE
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

    @api.cr_uid_ids_context
    def get_sent_appraisal(self, cr, uid, ids, context=None):
        """ Link to open sent appraisal"""
        sur_res_obj = self.pool.get('survey.user_input')
        sent_appraisal_ids = []
        for rec in self.browse(cr, uid, ids, context=context):
            sent_ids = sur_res_obj.search(cr, uid, [
                                      ('survey_id', 'in', [rec.apprasial_manager_survey_id.id, rec.appraisal_colleagues_survey_id.id, rec.appraisal_self_survey_id.id, rec.appraisal_subordinates_survey_id.id]),
                                      ('type', '=', 'link'), ('deadline','=', rec.date_close),
                                      ('evaluation_id','=',rec.id)])
            for id in sent_ids:
                sent_appraisal_ids.append(id)
        model, action_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'survey', 'action_survey_user_input')
        action = self.pool.get(model).read(cr, uid, action_id, context=context)
        action['domain'] = str([('id', 'in', sent_appraisal_ids)])  
        return action

    @api.cr_uid_ids_context
    def get_result_appraisal(self, cr, uid, ids, context=None):
        """ Link to open answers appraisal"""
        sur_res_obj = self.pool.get('survey.user_input')
        sent_appraisal_ids = []
        for rec in self.browse(cr, uid, ids, context=context):
            sent_ids = sur_res_obj.search(cr, uid, [
                                      ('survey_id', 'in', [rec.apprasial_manager_survey_id.id, rec.appraisal_colleagues_survey_id.id, rec.appraisal_self_survey_id.id, rec.appraisal_subordinates_survey_id.id]),
                                      ('type', '=', 'link'), ('deadline','=', rec.date_close),
                                      ('evaluation_id','=',rec.id), ('state', '=', 'done')])
            for id in sent_ids:
                sent_appraisal_ids.append(id)
        model, action_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'survey', 'action_survey_user_input')
        action = self.pool.get(model).read(cr, uid, action_id, context=context)
        action['domain'] = str([('id', 'in', sent_appraisal_ids)])  
        return action

    @api.cr_uid_ids_context
    def schedule_interview_date(self, cr, uid, ids, context=None):
        """ Link to open calendar view for creating employee interview and meeting"""
        if context is None:
            context = {}
        partner_ids = []
        for rec in self.browse(cr, uid, ids, context=context):
            for manager in rec.apprasial_manager_ids:
                if manager.user_id:
                    partner_ids.append(manager.user_id.partner_id.id)
            if rec.employee_id.user_id:
                partner_ids.append(rec.employee_id.user_id.partner_id.id)
        res = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid, 'calendar', 'action_calendar_event', context)
        res['context'] = {
            'default_partner_ids': partner_ids,
        }
        meeting_ids = self.pool.get('calendar.event').search(cr, uid, [('partner_ids', 'in', partner_ids)])
        res['domain'] = str([('id','in',meeting_ids)])
        return res

    @api.one
    def log_meeting(self, meeting_subject, meeting_date, duration):
        if not duration:
            duration = _('unknown')
        else:
            duration = str(duration)
        message = _("Meeting scheduled at '%s'<br> Subject: %s <br> Duration: %s hour(s)") % (meeting_date, meeting_subject, duration)
        return self.message_post(body=message)

class hr_employee(models.Model):
    _inherit = "hr.employee"

    evaluation_date = fields.Date('Next Appraisal Date', help="The date of the next appraisal is computed by the appraisal plan's dates (first appraisal + periodicity).")
    appraisal_manager = fields.Boolean('Manager')
    apprasial_manager_ids = fields.Many2many('hr.employee', 'apprasial_manager_rel', 'hr_evaluation_evaluation_id')
    apprasial_manager_survey_id = fields.Many2one('survey.survey', 'Manager Appraisal')
    appraisal_colleagues = fields.Boolean('Colleagues')
    appraisal_colleagues_ids = fields.Many2many('hr.employee', 'appraisal_colleagues_rel', 'hr_evaluation_evaluation_id')
    appraisal_colleagues_survey_id = fields.Many2one('survey.survey', "Employee's Appraisal")
    appraisal_self = fields.Boolean('Employee')
    apprasial_employee = fields.Char('Employee Name')
    appraisal_self_survey_id = fields.Many2one('survey.survey', 'Self Appraisal')
    appraisal_subordinates = fields.Boolean('Collaborator')
    appraisal_subordinates_ids = fields.Many2many('hr.employee', 'appraisal_subordinates_rel', 'hr_evaluation_evaluation_id')
    appraisal_subordinates_survey_id = fields.Many2one('survey.survey', "collaborate's Appraisal")
    appraisal_repeat = fields.Boolean('Repeat', default=False)
    appraisal_repeat_number = fields.Integer('Appraisal Cycle', default=1)
    appraisal_repeat_delay = fields.Selection([('year','Year'),('month','Month')], 'Repeat Every', copy=False, default='year')
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

    @api.model
    def run_employee_evaluation(self, automatic=False, use_new_cursor=False):  # cronjob
        now = parser.parse(datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT))
        obj_evaluation = self.env['hr_evaluation.evaluation']
        next_date = datetime.now()
        emp_ids = self.search([('evaluation_date', '<=', datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT))])
        for emp in emp_ids:
            if emp.appraisal_repeat_delay == 'month':
                next_date = (now + relativedelta(months=emp.appraisal_repeat_number)).strftime(DEFAULT_SERVER_DATE_FORMAT)
            else:
                next_date = (now + relativedelta(months=emp.appraisal_repeat_number * 12)).strftime(DEFAULT_SERVER_DATE_FORMAT)
            emp.write({'evaluation_date': next_date})
            vals = {'employee_id': emp.id,
                    'date_close': now,
                    'department_id': emp.department_id.id,
                    'appraisal_manager': emp.appraisal_manager,
                    'apprasial_manager_ids': [(4,manager.id) for manager in emp.apprasial_manager_ids],
                    'apprasial_manager_survey_id' : emp.apprasial_manager_survey_id.id,
                    'appraisal_colleagues': emp.appraisal_colleagues,
                    'appraisal_colleagues_ids': [(4,colleagues.id) for colleagues in emp.appraisal_colleagues_ids],
                    'appraisal_colleagues_survey_id': emp.appraisal_colleagues_survey_id.id,
                    'appraisal_self': emp.appraisal_self,
                    'apprasial_employee': emp.name,
                    'appraisal_self_survey_id': emp.appraisal_self_survey_id.id,
                    'appraisal_subordinates': emp.appraisal_subordinates,
                    'appraisal_subordinates_ids': [(4,subordinates.id) for subordinates in emp.appraisal_subordinates_ids],
                    'appraisal_subordinates_survey_id': emp.appraisal_subordinates_survey_id.id
            }
            obj_evaluation.create(vals)
        return True

