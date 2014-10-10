import time
import uuid, urlparse
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dateutil import parser
from openerp import fields, api, tools, models, _
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
            evaluation_obj.log_meeting(res.name, res.start)
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
    _order = 'date_close, interview_deadline'

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
    @api.depends('state', 'interview_deadline')
    def _get_tot_sent_appraisal(self):
        sur_res_obj = self.env['survey.user_input']
        self.tot_sent_appraisal = sur_res_obj.search_count([
            ('survey_id', 'in', [self.apprasial_manager_survey_id.id, self.appraisal_colleagues_survey_id.id, self.appraisal_self_survey_id.id, self.appraisal_subordinates_survey_id.id]),
            ('type', '=', 'link'), ('deadline', '=', self.date_close), ('evaluation_id', '=', self.id)])

    @api.one
    def _get_tot_completed_appraisal(self):
        sur_res_obj = self.env['survey.user_input']
        self.tot_comp_appraisal = sur_res_obj.search_count([
            ('survey_id', 'in', [self.apprasial_manager_survey_id.id, self.appraisal_colleagues_survey_id.id, self.appraisal_self_survey_id.id, self.appraisal_subordinates_survey_id.id]),
            ('type', '=', 'link'), ('deadline', '=', self.date_close), ('state', '=', 'done'),
            ('evaluation_id', '=', self.id)])

    meeting_id = fields.Many2one('calendar.event', 'Meeting')
    interview_deadline = fields.Date("Final Interview", select=True)
    employee_id = fields.Many2one('hr.employee', required=True, string='Employee')
    department_id = fields.Many2one('hr.department', 'Department')
    evaluation = fields.Text('Evaluation Summary', help="If the evaluation does not meet the expectations, you can propose an action plan")
    state = fields.Selection(EVALUATION_STATE, 'Status', track_visibility='onchange', required=True, readonly=True, copy=False, default='new', select=True)
    date_close = fields.Date('Appraisal Deadline', select=True, required=True)
    appraisal_manager = fields.Boolean('Manager')
    apprasial_manager_ids = fields.Many2many('hr.employee', 'evaluation_apprasial_manager_rel', 'hr_evaluation_evaluation_id')
    apprasial_manager_survey_id = fields.Many2one('survey.survey', 'Manager Appraisal', required=False)
    appraisal_colleagues = fields.Boolean('Colleagues')
    appraisal_colleagues_ids = fields.Many2many('hr.employee', 'evaluation_appraisal_colleagues_rel', 'hr_evaluation_evaluation_id')
    appraisal_colleagues_survey_id = fields.Many2one('survey.survey', "Employee's Appraisal")
    appraisal_self = fields.Boolean('Employee')
    apprasial_employee = fields.Char('Employee Name')
    appraisal_self_survey_id = fields.Many2one('survey.survey', string='Self Appraisal')
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

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id:
            self.department_id = self.employee_id.department_id
            self.appraisal_manager = self.employee_id.appraisal_manager
            self.apprasial_manager_ids = self.employee_id.apprasial_manager_ids
            self.apprasial_manager_survey_id = self.employee_id.apprasial_manager_survey_id
            self.appraisal_colleagues = self.employee_id.appraisal_colleagues
            self.appraisal_colleagues_ids = self.employee_id.appraisal_colleagues_ids
            self.appraisal_colleagues_survey_id = self.employee_id.appraisal_colleagues_survey_id
            self.appraisal_self = self.employee_id.appraisal_self
            self.apprasial_employee = self.employee_id.apprasial_employee or self.employee_id.name
            self.appraisal_self_survey_id = self.employee_id.appraisal_self_survey_id
            self.appraisal_subordinates = self.employee_id.appraisal_subordinates
            self.appraisal_subordinates_ids = self.employee_id.appraisal_subordinates_ids
            self.appraisal_subordinates_survey_id = self.employee_id.appraisal_subordinates_survey_id

    @api.one
    @api.constrains('employee_id', 'department_id', 'date_close')
    def _check_employee_appraisal_duplication(self):
        """ Avoid duplication"""
        if self.employee_id and self.department_id and self.date_close:
            date_closed = datetime.strptime(self.date_close, DEFAULT_SERVER_DATE_FORMAT)
            appraisal_ids = self.search([
                ('employee_id', '=', self.employee_id.id), ('department_id', '=', self.department_id.id),
                ('date_close', '<=', time.strftime('%Y-' + str(date_closed.month) + '-' + str(date_closed.day))),
                ('date_close', '>=', time.strftime('%Y-' + str(date_closed.month) + '-01'))])
            if len(appraisal_ids) > 1:
                raise except_orm(_('Warning'), _("You cannot create more than one appraisal for same Month & Year"))

    @api.one
    def create_message_subscribe_users_list(self, subscribe_users):
        user_ids = [emp.user_id.id for emp in subscribe_users if emp.user_id]
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
        if res.apprasial_manager_ids:
            res.create_message_subscribe_users_list(res.apprasial_manager_ids)
        return res

    @api.multi
    def write(self, vals):
        emp_obj = self.env['hr.employee']
        for evl_rec in self:
            if self.state == 'new' and vals.get('state') == 'done':
                raise Warning(_("You can not move directly in done state."))
            #avoid recursive process
            if vals.get('state') == 'pending' and not evl_rec._context.get('send_mail_status'):
                evl_rec.button_sent_appraisal()
            if vals.get('interview_deadline') and not vals.get('meeting_id'):
                if datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT) > vals.get('interview_deadline'):
                    raise Warning(_("The interview date can not be in the past"))
                #creating employee meeting and interview date
                evl_rec.create_update_meeting(vals)
            if vals.get('apprasial_manager_ids'):
                # add followers
                for follower_id in emp_obj.browse(vals['apprasial_manager_ids'][0][2]):
                    if follower_id.user_id:
                        evl_rec.message_subscribe_users(user_ids=[follower_id.user_id.id])
        return super(hr_evaluation, self).write(vals)

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
            'date_create': datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT),
            'type': 'link',
            'state': 'new',
            'token': token,
            'evaluation_id': self.id,
            'partner_id': partner_id.id if partner_id else None,
            'email': email})
        return token

    @api.one
    def create_receiver_list(self, appraisal_receiver):
        """ Create one mail by recipients and __URL__ by link with identification token """
        mail_obj = self.env['mail.thread']
        find_no_email = [employee.name for record in appraisal_receiver for employee in record['employee_ids'] if not employee.work_email]
        if find_no_email:
            raise Warning(_("Following employees do not have configured an email address. \n- %s") % ('\n- ').join(find_no_email))
        for record in appraisal_receiver:
            for emp in record['employee_ids']:
                email = tools.email_split(emp.work_email) and tools.email_split(emp.work_email)[0] or False
                if email:
                    partner_id = mail_obj._find_partner_from_emails(email) or emp.user_id.partner_id or None
                    token = self.create_token(email, record['survey_id'], partner_id)[0]
                    self.update_appraisal_url(record['survey_id'].public_url, email, token)
                    self.mail_template.send_mail(self.id, force_send=False)
        return True

    @api.one
    def button_sent_appraisal(self):
        """ Changes To Start state to Appraisal Sent."""
        if self.employee_id:
            appraisal_receiver = []
            if self.appraisal_manager and self.apprasial_manager_ids:
                appraisal_receiver.append({'survey_id': self.apprasial_manager_survey_id, 'employee_ids': self.apprasial_manager_ids})
            if self.appraisal_colleagues and self.appraisal_colleagues_ids:
                appraisal_receiver.append({'survey_id': self.appraisal_colleagues_survey_id, 'employee_ids': self.appraisal_colleagues_ids})
            if self.appraisal_subordinates and self.appraisal_subordinates_ids:
                appraisal_receiver.append({'survey_id': self.appraisal_subordinates_survey_id, 'employee_ids': self.appraisal_subordinates_ids})
            if self.appraisal_self and self.apprasial_employee:
                appraisal_receiver.append({'survey_id': self.appraisal_self_survey_id, 'employee_ids': self.employee_id})
            if appraisal_receiver:
                self.create_receiver_list(appraisal_receiver)
            else:
                raise Warning(_("Employee do not have configured evaluation plan."))
            if self.state == 'new':
                #avoid recursive process
                self.with_context(send_mail_status=True).write({'state': 'pending'})
        return True

    @api.multi
    def button_done_appraisal(self):
        """ Changes Appraisal Sent state to Done."""
        return self.write({'state': 'done'})

    @api.multi
    def create_update_meeting(self, vals):
        """ Creates event when user enters date manually from the form view.
            If users edits the already entered date, created meeting is updated accordingly.
        """
        if self.meeting_id and self.meeting_id.allday:
            self.meeting_id.write({'start_date': vals['interview_deadline'], 'stop_date': vals['interview_deadline']})
        elif self.meeting_id and not self.meeting_id.allday:
            date_obj = datetime.strptime(vals['interview_deadline'], DEFAULT_SERVER_DATE_FORMAT)
            set_date = datetime.strftime(date_obj, DEFAULT_SERVER_DATETIME_FORMAT)
            self.meeting_id.write({'start_datetime': set_date, 'stop_datetime': set_date})
        else:
            partner_ids = [(4, manager.user_id.partner_id.id) for manager in self.apprasial_manager_ids if manager.user_id]
            if self.employee_id.user_id:
                partner_ids.append((4, self.employee_id.user_id.partner_id.id))
            self.meeting_id = self.env['calendar.event'].create({
                'name': _('Appraisal Meeting For ') + self.employee_id.name_related,
                'start': vals['interview_deadline'],
                'stop': vals['interview_deadline'],
                'allday': True,
                'partner_ids': partner_ids,
            })
        return self.log_meeting(self.meeting_id.name, self.meeting_id.start)

    @api.multi
    @api.depends('employee_id')
    def name_get(self):
        result = []
        for hr_evaluation in self:
            result.append((hr_evaluation.id, '%s' % (hr_evaluation.employee_id.name_related)))
        return result

    @api.multi
    def unlink(self):
        for appraisal in self:
            if appraisal.state != 'new':
                eva_state = dict(self.EVALUATION_STATE)
                raise Warning(_("You cannot delete appraisal which is in '%s' state") % (eva_state[appraisal.state]))
        return super(hr_evaluation, self).unlink()

    @api.v7
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

    @api.multi
    def get_sent_appraisal(self):
        """ Link to open sent appraisal"""
        sur_res_obj = self.env['survey.user_input']
        sent_appraisal_ids = []
        for evaluation in self:
            sent_survey_ids = sur_res_obj.search([('survey_id', 'in', [
                evaluation.apprasial_manager_survey_id.id, evaluation.appraisal_colleagues_survey_id.id,
                evaluation.appraisal_self_survey_id.id, evaluation.appraisal_subordinates_survey_id.id]),
                ('type', '=', 'link'), ('deadline', '=', evaluation.date_close), ('evaluation_id', '=', evaluation.id)])
            sent_appraisal_ids = [sent_survey_id.id for sent_survey_id in sent_survey_ids]
        action = self.env.ref('survey.action_survey_user_input').read()[0]
        action['domain'] = str([('id', 'in', sent_appraisal_ids)])
        return action

    @api.multi
    def get_result_appraisal(self):
        """ Link to open answers appraisal"""
        sur_res_obj = self.env['survey.user_input']
        sent_appraisal_ids = []
        for evaluation in self:
            result_survey_ids = sur_res_obj.search([('survey_id', 'in', [
                evaluation.apprasial_manager_survey_id.id, evaluation.appraisal_colleagues_survey_id.id,
                evaluation.appraisal_self_survey_id.id, evaluation.appraisal_subordinates_survey_id.id]),
                ('type', '=', 'link'), ('deadline', '=', evaluation.date_close),
                ('evaluation_id', '=', evaluation.id), ('state', '=', 'done')])
            sent_appraisal_ids = [result_survey_id.id for result_survey_id in result_survey_ids]
        action = self.env.ref('survey.action_survey_user_input').read()[0]
        action['domain'] = str([('id', 'in', sent_appraisal_ids)])
        return action

    @api.multi
    def schedule_interview_date(self):
        """ Link to open calendar view for creating employee interview and meeting"""
        partner_ids = []
        for evaluation in self:
            for manager in evaluation.apprasial_manager_ids:
                if manager.user_id:
                    partner_ids.append(manager.user_id.partner_id.id)
            if evaluation.employee_id.user_id:
                partner_ids.append(evaluation.employee_id.user_id.partner_id.id)
        res = self.env.ref('calendar.action_calendar_event').read()[0]
        partner_ids.append(self.env['res.users'].browse(self._uid).partner_id.id)
        res['context'] = {
            'default_partner_ids': partner_ids,
        }
        meeting_ids = self.env['calendar.event'].search([('partner_ids', 'in', partner_ids)])
        res['domain'] = str([('id', 'in', [meeting.id for meeting in meeting_ids])])
        return res

    @api.one
    def log_meeting(self, meeting_subject, meeting_date):
        message = _("Subject: %s <br> Meeting scheduled at '%s'<br>") % (meeting_subject, meeting_date.split(' ')[0])
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
    appraisal_repeat = fields.Boolean('Periodic Appraisal', default=False)
    appraisal_repeat_number = fields.Integer('Repeat Every', default=1)
    appraisal_repeat_delay = fields.Selection([('year', 'Year'), ('month', 'Month')], 'Repeat Every', copy=False, default='year')
    appraisal_count = fields.Integer(compute='_appraisal_count', string='Appraisal Interviews')

    @api.one
    def _appraisal_count(self):
        Evaluation = self.env['hr_evaluation.evaluation']
        self.appraisal_count = Evaluation.search_count([('employee_id', '=', self.id)])

    @api.onchange('appraisal_manager')
    def onchange_manager_appraisal(self):
        self.apprasial_manager_ids = [self.parent_id.id]

    @api.onchange('appraisal_self')
    def onchange_self_employee(self):
        self.apprasial_employee = self.name

    @api.onchange('appraisal_colleagues')
    def onchange_colleagues(self):
        if self.department_id.id:
            self.appraisal_colleagues_ids = self.search([('department_id', '=', self.department_id.id), ('id', '!=', self.parent_id.id)])

    @api.onchange('appraisal_subordinates')
    def onchange_subordinates(self):
        manager = set()
        for emp in self.search([]):
            if emp.parent_id:
                manager.add(emp.parent_id.id)
        self.appraisal_subordinates_ids = list(manager)

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
                    'apprasial_manager_ids': [(4, manager.id) for manager in emp.apprasial_manager_ids] or [(4, emp.parent_id.id)],
                    'apprasial_manager_survey_id': emp.apprasial_manager_survey_id.id,
                    'appraisal_colleagues': emp.appraisal_colleagues,
                    'appraisal_colleagues_ids': [(4, colleagues.id) for colleagues in emp.appraisal_colleagues_ids],
                    'appraisal_colleagues_survey_id': emp.appraisal_colleagues_survey_id.id,
                    'appraisal_self': emp.appraisal_self,
                    'apprasial_employee': emp.apprasial_employee or emp.name,
                    'appraisal_self_survey_id': emp.appraisal_self_survey_id.id,
                    'appraisal_subordinates': emp.appraisal_subordinates,
                    'appraisal_subordinates_ids': [(4, subordinates.id) for subordinates in emp.appraisal_subordinates_ids],
                    'appraisal_subordinates_survey_id': emp.appraisal_subordinates_survey_id.id}
            obj_evaluation.create(vals)
        return True
