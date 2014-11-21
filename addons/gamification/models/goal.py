# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from openerp import SUPERUSER_ID

from openerp import models, fields, api, _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from openerp.tools.safe_eval import safe_eval
from openerp.exceptions import except_orm, Warning, RedirectWarning
import logging
import time
from datetime import date, datetime, timedelta

_logger = logging.getLogger(__name__)


class gamification_goal_definition(models.Model):
    """Goal definition

    A goal definition contains the way to evaluate an objective
    Each module wanting to be able to set goals to the users needs to create
    a new gamification_goal_definition
    """
    _name = 'gamification.goal.definition'
    _description = 'Gamification goal definition'

    @api.multi
    def _get_suffix(self):
        for goal in self:
            if goal.suffix and not goal.monetary:
                goal.full_suffix = goal.suffix
            elif goal.monetary:
                # use the current user's company currency
                user = self.pool['res.users'].browse(self._uid)
                if goal.suffix:
                    goal.full_suffix = "%s %s" % (user.company_id.currency_id.symbol, goal.suffix)
                else:
                    goal.full_suffix = user.company_id.currency_id.symbol
            else:
                goal.full_suffix = ""

    name = fields.Char('Goal Definition', required=True, translate=True)
    description = fields.Text('Goal Description')
    monetary = fields.Boolean('Monetary Value', help="The target and current value are defined in the company currency.", default=False)
    suffix = fields.Char('Suffix', help="The unit of the target and current values", translate=True)
    full_suffix = fields.Char(compute='_get_suffix', string="Full Suffix", help="The currency and suffix field")
    computation_mode = fields.Selection([
            ('manually', 'Recorded manually'),
            ('count', 'Automatic: number of records'),
            ('sum', 'Automatic: sum on a field'),
            ('python', 'Automatic: execute a specific Python code'),
        ],
        string="Computation Mode",
        help="Defined how will be computed the goals. The result of the operation will be stored in the field 'Current'.",
        required=True, default='manually')
    display_mode = fields.Selection([
            ('progress', 'Progressive (using numerical values)'),
            ('boolean', 'Exclusive (done or not-done)'),
        ],
        string="Displayed as", required=True, default='progress')
    model_id = fields.Many2one('ir.model',
        string='Model',
        help='The model object for the field to evaluate')
    model_inherited_model_ids = fields.Many2many(
        related='model_id.inherited_model_ids', obj="ir.model",
        string="Inherited models", readonly="True")#relation="ir.model",
    field_id = fields.Many2one('ir.model.fields',
        string='Field to Sum',
        help='The field containing the value to evaluate')
    field_date_id = fields.Many2one('ir.model.fields',
        string='Date Field',
        help='The date to use for the time period evaluated')
    domain = fields.Char("Filter Domain",
        help="Domain for filtering records. General rule, not user depending, e.g. [('state', '=', 'done')]. The expression can contain reference to 'user' which is a browse record of the current user if not in batch mode.",
        required=True, default="[]")

    batch_mode = fields.Boolean('Batch Mode',
        help="Evaluate the expression in batch instead of once for each user")
    batch_distinctive_field = fields.Many2one('ir.model.fields',
        string="Distinctive field for batch user",
        help="In batch mode, this indicates which field distinct one user form the other, e.g. user_id, partner_id...")
    batch_user_expression = fields.Char("Evaluted expression for batch mode",
        help="The value to compare with the distinctive field. The expression can contain reference to 'user' which is a browse record of the current user, e.g. user.id, user.partner_id.id...")
    compute_code = fields.Text('Python Code',
        help="Python code to be executed for each user. 'result' should contains the new current value. Evaluated user can be access through object.user_id.")
    condition = fields.Selection([
            ('higher', 'The higher the better'),
            ('lower', 'The lower the better')
        ],
        string='Goal Performance',
        help='A goal is considered as completed when the current value is compared to the value to reach',
        required=True, default='higher')
    action_id = fields.Many2one('ir.actions.act_window', string="Action",
        help="The action that will be called to update the goal value.")
    res_id_field = fields.Char("ID Field of user",
        help="The field name on the user profile (res.users) containing the value for res_id for action.")

    def number_following(self, cr, uid, model_name="mail.thread", context=None):
        """Return the number of 'model_name' objects the user is following

        The model specified in 'model_name' must inherit from mail.thread
        """
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return self.pool.get('mail.followers').search(cr, uid, [('res_model', '=', model_name), ('partner_id', '=', user.partner_id.id)], count=True, context=context)

    @api.multi
    def _check_domain_validity(self):
        # take admin as should always be present
        superuser = self.pool['res.users'].browse(self._cr, self._uid, SUPERUSER_ID, context=self._context)
        for definition in self:
            if definition.computation_mode not in ('count', 'sum'):
                continue

            obj = self.pool[definition.model_id.model]
            try:
                domain = safe_eval(definition.domain, {'user': superuser})
                # demmy search to make sure the domain is valid
                obj.search(self._cr, self._uid, domain, context=self._context, count=True)
            except (ValueError, SyntaxError), e:
                msg = e.message or (e.msg + '\n' + e.text)
                raise except_orm(
                    _('Error!'),
                    _("The domain for the definition %s seems incorrect, please check it.\n\n%s" % (definition.name, msg)))
        return True

    @api.model
    def create(self, vals):
        definition_res = super(gamification_goal_definition, self).create(vals)
        if vals.get('computation_mode') in ('count', 'sum'):
            definition_res._check_domain_validity()
        return definition_res

    @api.multi
    def write(self, vals):
        res = super(gamification_goal_definition, self).write(vals)
        if vals.get('computation_mode', 'count') in ('count', 'sum') and (vals.get('domain') or vals.get('model_id')):
            self._check_domain_validity()

        return res

    @api.onchange('model_id')
    def on_change_model_id(self):
        """Prefill field model_inherited_model_ids"""
        if not self.model_id:
            self.model_inherited_model_ids = []
        # model = self.pool['ir.model'].browse(self._cr, self._uid, model_id, context=self._context)
        # format (6, 0, []) to construct the domain ('model_id', 'in', m and m[0] and m[0][2])
        self.model_inherited_model_ids = [(6, 0, [m.id for m in self.model_id.inherited_model_ids])]


class gamification_goal(models.Model):
    """Goal instance for a user

    An individual goal for a user on a specified time period"""

    _name = 'gamification.goal'
    _description = 'Gamification goal instance'


    # @api.depends('completeness')
    # def _get_completion(self):
    #     print"++++++++_get_completion++++++"
    #     """Return the percentage of completeness of the goal, between 0 and 100"""
    #     for goal in self:
    #         if goal.definition_condition == 'higher':
    #             if goal.current >= goal.target_goal:
    #                 goal.completeness = 100.0
    #             else:
    #                 goal.completeness = round(100.0 * goal.current / goal.target_goal, 2)
    #         elif goal.current < goal.target_goal:
    #             # a goal 'lower than' has only two values possible: 0 or 100%
    #             goal.completeness = 100.0
    #         else:
    #             goal.completeness = 0.0

    @api.onchange('definition_id')
    def on_change_definition_id(self):
        if not self.definition_id:
            self.definition_id = False
            return
        self.write({'computation_mode': self.definition_id.computation_mode, 
                    'definition_condition': self.definition_id.condition})

    definition_id = fields.Many2one('gamification.goal.definition', string='Goal Definition', required=True, ondelete="cascade")
    user_id = fields.Many2one('res.users', string='User', required=True, auto_join=True, ondelete="cascade")
    line_id = fields.Many2one('gamification.challenge.line', string='Challenge Line', ondelete="cascade")
    challenge_id = fields.Many2one(related='line_id.challenge_id',
        string="Challenge",
        store=True, readonly=True,
        help="Challenge that generated the goal, assign challenge to users to generate goals with a value in this field.")
    #         relation='gamification.challenge',
    start_date = fields.Date('Start Date', default=fields.date.today())
    end_date = fields.Date('End Date')  # no start and end = always active
    target_goal = fields.Float('To Reach',
        required=True,
        track_visibility='always')  # no goal = global index
    current = fields.Float('Current Value', required=True, track_visibility='always', default=0)
    # completeness = fields.Float(compute='_get_completion', store=True, string='Completeness')
    state = fields.Selection([
            ('draft', 'Draft'),
            ('inprogress', 'In progress'),
            ('reached', 'Reached'),
            ('failed', 'Failed'),
            ('canceled', 'Canceled'),
        ],
        string='State',
        required=True,
        track_visibility='always', default='draft')
    to_update = fields.Boolean('To update')
    closed = fields.Boolean('Closed goal', help="These goals will not be recomputed.")

    computation_mode = fields.Selection(related='definition_id.computation_mode', string="Computation mode")
    remind_update_delay = fields.Integer('Remind delay',
        help="The number of days after which the user assigned to a manual goal will be reminded. Never reminded if no value is specified.")
    last_update = fields.Date('Last Update',
        help="In case of manual goal, reminders are sent if the goal as not been updated for a while (defined in challenge). Ignored in case of non-manual goal or goal not linked to a challenge.")

    definition_description = fields.Text(related='definition_id.description', string='Definition Description', readonly=True, store=True)
    definition_condition = fields.Selection(related='definition_id.condition', string='Definition Condition', readonly=True, store=True)
    definition_suffix = fields.Char(related='definition_id.full_suffix', string="Suffix", readonly=True,store=True)
    definition_display = fields.Selection(related='definition_id.display_mode', string="Display Mode", readonly=True, 
        store=True)

    _order = 'start_date desc, end_date desc, definition_id, id'

    @api.one
    def _check_remind_delay(self):
        print"++++++++++++++++++++++++++++++++",self
        """Verify if a goal has not been updated for some time and send a
        reminder message of needed.

        :return: data to write on the goal object
        """
        if self.remind_update_delay and self.last_update:
            delta_max = timedelta(days=self.remind_update_delay)
            last_update = datetime.strptime(self.last_update, DF).date()
            if date.today() - last_update > delta_max:
                # generate a remind report
                temp_obj = self.pool['email.template']
                template_id = self.pool['ir.model.data'].get_object(self._cr, self._uid, 'gamification', 'email_template_goal_reminder', context=self._context)
                body_html = temp_obj.render_template(self._cr, self._uid, template_id.body_html, 'gamification.goal', self.id, context=self._context)
                self.pool['mail.thread'].message_post(self._cr, self._uid, 0, body=body_html, partner_ids=[self.user_id.partner_id.id], context=self._context, subtype='mail.mt_comment')
                return {'to_update': True}
        return {}

    @api.multi
    def update(self):
        """Update the goals to recomputes values and change of states

        If a manual goal is not updated for enough time, the user will be
        reminded to do so (done only once, in 'inprogress' state).
        If a goal reaches the target value, the status is set to reached
        If the end date is passed (at least +1 day, time not considered) without
        the target value being reached, the goal is set as failed."""
        print"***********update*********"
        print"++++ids : ",self, self._context
        commit = self._context.get('commit_gamification', False)

        goals_by_definition = {}
        all_goals = {}
        for goal in self:
            if goal.state in ('draft', 'canceled'):
                # draft or canceled goals should not be recomputed
                continue

            goals_by_definition.setdefault(goal.definition_id, []).append(goal)
            all_goals[goal] = goal
        print"----all_goals : ",all_goals
        print"++++++++++++++++++++for"
        for definition, goals in goals_by_definition.items():
            print"----goal : ",goals
            print"----definition : ",definition
            goals_to_write = dict((goal, {}) for goal in goals)
            if definition.computation_mode == 'manually':
                for goal in goals:
                    goals_to_write[goal].update(goal._check_remind_delay())
            elif definition.computation_mode == 'python':
                # TODO batch execution
                for goal in goals:
                    # execute the chosen method
                    cxt = {
                        'self': self.pool['gamification.goal'],
                        'object': goal,
                        'pool': self.pool,
                        'cr': self._cr,
                        'context': self._context, # copy context to prevent side-effects of eval
                        'uid': self._uid,
                        'date': date, 'datetime': datetime, 'timedelta': timedelta, 'time': time
                    }
                    code = definition.compute_code.strip()
                    safe_eval(code, cxt, mode="exec", nocopy=True)
                    # the result of the evaluated codeis put in the 'result' local variable, propagated to the context
                    result = cxt.get('result')
                    if result is not None and type(result) in (float, int, long):
                        if result != goal.current:
                            goals_to_write[goal]['current'] = result
                    else:
                        _logger.exception(_('Invalid return content from the evaluation of code for definition %s' % definition.name))

            else:  # count or sum

                obj = self.pool[definition.model_id.model]
                field_date_name = definition.field_date_id and definition.field_date_id.name or False

                if definition.computation_mode == 'count' and definition.batch_mode:
                    # batch mode, trying to do as much as possible in one request
                    general_domain = safe_eval(definition.domain)
                    field_name = definition.batch_distinctive_field.name
                    subqueries = {}
                    for goal in goals:
                        start_date = field_date_name and goal.start_date or False
                        end_date = field_date_name and goal.end_date or False
                        subqueries.setdefault((start_date, end_date), {}).update({goal.id:safe_eval(definition.batch_user_expression, {'user': goal.user_id})})

                    # the global query should be split by time periods (especially for recurrent goals)
                    for (start_date, end_date), query_goals in subqueries.items():
                        subquery_domain = list(general_domain)
                        subquery_domain.append((field_name, 'in', list(set(query_goals.values()))))
                        if start_date:
                            subquery_domain.append((field_date_name, '>=', start_date))
                        if end_date:
                            subquery_domain.append((field_date_name, '<=', end_date))

                        if field_name == 'id':
                            # grouping on id does not work and is similar to search anyway
                            user_ids = obj.search(self._cr, self._uid, subquery_domain, context=self._context)
                            user_values = [{'id': user_id, 'id_count': 1} for user_id in user_ids]
                        else:
                            user_values = obj.read_group(self._cr, self._uid, subquery_domain, fields=[field_name], groupby=[field_name], context=self._context)
                        # user_values has format of read_group: [{'partner_id': 42, 'partner_id_count': 3},...]
                        for goal in [g for g in goals if g.id in query_goals.keys()]:
                            for user_value in user_values:
                                queried_value = field_name in user_value and user_value[field_name] or False
                                if isinstance(queried_value, tuple) and len(queried_value) == 2 and isinstance(queried_value[0], (int, long)):
                                    queried_value = queried_value[0]
                                if queried_value == query_goals[goal.id]:
                                    new_value = user_value.get(field_name+'_count', goal.current)
                                    if new_value != goal.current:
                                        goals_to_write[goal]['current'] = new_value

                else:
                    for goal in goals:
                        # eval the domain with user replaced by goal user object
                        domain = safe_eval(definition.domain, {'user': goal.user_id})

                        # add temporal clause(s) to the domain if fields are filled on the goal
                        if goal.start_date and field_date_name:
                            domain.append((field_date_name, '>=', goal.start_date))
                        if goal.end_date and field_date_name:
                            domain.append((field_date_name, '<=', goal.end_date))

                        if definition.computation_mode == 'sum':
                            field_name = definition.field_id.name
                            # TODO for master: group on user field in batch mode
                            res = obj.read_group(self._cr, self._uid, domain, [field_name], [], context=self._context)
                            print"+-+-+-+-res : ",res
                            new_value = res and res[0][field_name] or 0.0

                        else:  # computation mode = count
                            new_value = obj.search(self._cr, self._uid, domain, context=self._context, count=True)
                            print"--new_value : ",new_value
                        # avoid useless write if the new value is the same as the old one
                        if new_value != goal.current:
                            goals_to_write[goal]['current'] = new_value

            print"----goals_to_write : ",goals_to_write
            print"---------------------last for"
            for goal_rec, value in goals_to_write.items():
                print"--goal_id : ",goal_rec
                if not value:
                    continue
                goal = all_goals[goal_rec]
                print"----goal : ",goal

                # check goal target reached
                if (goal.definition_id.condition == 'higher' and value.get('current', goal.current) >= goal.target_goal) \
                  or (goal.definition_id.condition == 'lower' and value.get('current', goal.current) <= goal.target_goal):
                    value['state'] = 'reached'

                # check goal failure
                elif goal.end_date and str(fields.date.today()) > goal.end_date:
                    value['state'] = 'failed'
                    value['closed'] = True
                if value:
                    goal.write(value)
            if commit:
                self._cr.commit()
        return True

    @api.one
    def action_start(self):
        """Mark a goal as started.

        This should only be used when creating goals manually (in draft state)"""
        self.write({'state': 'inprogress'})
        return self.update()

    @api.one
    def action_reach(self):
        """Mark a goal as reached.

        If the target goal condition is not met, the state will be reset to In
        Progress at the next goal update until the end date."""
        return self.write({'state': 'reached'})

    @api.one
    def action_fail(self):
        """Set the state of the goal to failed.

        A failed goal will be ignored in future checks."""
        return self.write({'state': 'failed'})

    @api.one
    def action_cancel(self):
        """Reset the completion after setting a goal as reached or failed.

        This is only the current state, if the date and/or target criterias
        match the conditions for a change of state, this will be applied at the
        next goal update."""
        return self.write({'state': 'inprogress'})

    @api.model
    def create(self, vals):
        """Overwrite the create method to add a 'no_remind_goal' field to True"""
        self = self.with_context(no_remind_goal=True)
        return super(gamification_goal, self).create(vals)

    @api.multi
    def write(self, vals):
        """Overwrite the write method to update the last_update field to today

        If the current value is changed and the report frequency is set to On
        change, a report is generated
        """
        vals['last_update'] = fields.date.today()
        result = super(gamification_goal, self).write(vals)
        for goal in self:
            if goal.state != "draft" and ('definition_id' in vals or 'user_id' in vals):
                # avoid drag&drop in kanban view
                raise except_orm(_('Error!'), _('Can not modify the configuration of a started goal'))

            if vals.get('current'):
                if 'no_remind_goal' in self._context:
                    # new goals should not be reported
                    continue

                if goal.challenge_id and goal.challenge_id.report_message_frequency == 'onchange':
                    goal.challenge_id.report_progress(users=[goal.user_id])
        return result

    def get_action(self, cr, uid, goal_id, context=None):
        """Get the ir.action related to update the goal

        In case of a manual goal, should return a wizard to update the value
        :return: action description in a dictionnary
        """
        print"+-+-------------------+++++++++++++++++++++++++++-----------------"
        goal = self.browse(cr, uid, goal_id, context=context)

        if goal.definition_id.action_id:
            # open a the action linked to the goal
            action = goal.definition_id.action_id.read()[0]

            if goal.definition_id.res_id_field:
                current_user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
                action['res_id'] = safe_eval(goal.definition_id.res_id_field, {'user': current_user})

                # if one element to display, should see it in form mode if possible
                action['views'] = [(view_id, mode) for (view_id, mode) in action['views'] if mode == 'form'] or action['views']
            return action

        if goal.computation_mode == 'manually':
            # open a wizard window to update the value manually
            action = {
                'name': _("Update %s") % goal.definition_id.name,
                'id': goal_id,
                'type': 'ir.actions.act_window',
                'views': [[False, 'form']],
                'target': 'new',
                'context': {'default_goal_id': goal_id, 'default_current': goal.current},
                'res_model': 'gamification.goal.wizard'
            }
            return action

        return False

#TODO: need to migrate
from openerp.osv import osv, fields
class gamification_goal_demo(osv.Model):
    _inherit='gamification.goal'

    def _get_completion(self, cr, uid, ids, field_name, arg, context=None):
        print"++++++++_get_completion++++++"
        """Return the percentage of completeness of the goal, between 0 and 100"""
        res = dict.fromkeys(ids, 0.0)
        for goal in self.browse(cr, uid, ids, context=context):
            if goal.definition_condition == 'higher':
                if goal.current >= goal.target_goal:
                    res[goal.id] = 100.0
                else:
                    res[goal.id] = round(100.0 * goal.current / goal.target_goal, 2)
            elif goal.current < goal.target_goal:
                # a goal 'lower than' has only two values possible: 0 or 100%
                res[goal.id] = 100.0
            else:
                res[goal.id] = 0.0
        return res

    _columns = {
        'completeness': fields.function(_get_completion, type='float', string='Completeness'),
                }