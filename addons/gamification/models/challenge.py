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
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.tools import ustr, DEFAULT_SERVER_DATE_FORMAT as DF
from openerp.tools.safe_eval import safe_eval as eval

from datetime import date, datetime, timedelta
import calendar
import logging
_logger = logging.getLogger(__name__)

# display top 3 in ranking, could be db variable
MAX_VISIBILITY_RANKING = 3

def start_end_date_for_period(period, default_start_date=False, default_end_date=False):
    """Return the start and end date for a goal period based on today

    :return: (start_date, end_date), datetime.date objects, False if the period is
    not defined or unknown"""
    today = date.today()
    if period == 'daily':
        start_date = today
        end_date = start_date
    elif period == 'weekly':
        delta = timedelta(days=today.weekday())
        start_date = today - delta
        end_date = start_date + timedelta(days=7)
    elif period == 'monthly':
        month_range = calendar.monthrange(today.year, today.month)
        start_date = today.replace(day=1)
        end_date = today.replace(day=month_range[1])
    elif period == 'yearly':
        start_date = today.replace(month=1, day=1)
        end_date = today.replace(month=12, day=31)
    else:  # period == 'once':
        start_date = default_start_date  # for manual goal, start each time
        end_date = default_end_date

    if start_date and end_date:
        return (datetime.strftime(start_date, DF), datetime.strftime(end_date, DF))
    else:
        return (start_date, end_date)



class gamification_challenge(models.Model):
    """Gamification challenge

    Set of predifined objectives assigned to people with rules for recurrence and
    rewards

    If 'user_ids' is defined and 'period' is different than 'one', the set will
    be assigned to the users for each period (eg: every 1st of each month if
    'monthly' is selected)
    """

    _name = 'gamification.challenge'
    _description = 'Gamification challenge'
    _inherit = 'mail.thread'

    @api.multi
    def _get_next_report_date(self):
        """Return the next report date based on the last report date and report
        period.

        :return: a string in DEFAULT_SERVER_DATE_FORMAT representing the date"""
        for challenge in self:
            last = datetime.strptime(challenge.last_report_date, DF).date()
            if challenge.report_message_frequency == 'daily':
                next = last + timedelta(days=1)
                challenge.next_report_date = next.strftime(DF)
            elif challenge.report_message_frequency == 'weekly':
                next = last + timedelta(days=7)
                challenge.next_report_date = next.strftime(DF)
            elif challenge.report_message_frequency == 'monthly':
                month_range = calendar.monthrange(last.year, last.month)
                next = last.replace(day=month_range[1]) + timedelta(days=1)
                challenge.next_report_date = next.strftime(DF)
            elif challenge.report_message_frequency == 'yearly':
                challenge.next_report_date = last.replace(year=last.year + 1).strftime(DF)
            # frequency == 'once', reported when closed only
            else:
                challenge.next_report_date = False
    
    @api.multi
    def _get_categories(self):
        return [
            ('hr', 'Human Ressources / Engagement'),
            ('other', 'Settings / Gamification Tools'),
        ]

    @api.multi
    def _get_report_template(self):
        try:
            return self.pool['ir.model.data'].get_object_reference(self._cr, self._uid, 'gamification', 'simple_report_template')[1]
        except ValueError:
            return False

    _order = 'end_date, start_date, name, id'

    name = fields.Char('Challenge Name', required=True, translate=True)
    description = fields.Text('Description', translate=True)
    state = fields.Selection([
            ('draft', 'Draft'),
            ('inprogress', 'In Progress'),
            ('done', 'Done'),
        ], copy=False,
        string='State', required=True, track_visibility='onchange', default='draft')
    manager_id = fields.Many2one('res.users',
        string='Responsible', help="The user responsible for the challenge.", default=lambda self: self._uid)

    user_ids = fields.Many2many(comodel_name = 'res.users', 
        relation = 'gamification_challenge_users_rel',
        string='Users',
        help="List of users participating to the challenge")
    user_domain = fields.Char('User domain', help="Alternative to a list of users")

    period = fields.Selection([
            ('once', 'Non recurring'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('yearly', 'Yearly')
        ],
        string='Periodicity',
        help='Period of automatic goal assigment. If none is selected, should be launched manually.',
        required=True, default='once')
    start_date = fields.Date('Start Date',
        help="The day a new challenge will be automatically started. If no periodicity is set, will use this date as the goal start date.")
    end_date = fields.Date('End Date',
        help="The day a new challenge will be automatically closed. If no periodicity is set, will use this date as the goal end date.")

    invited_user_ids = fields.Many2many(comodel_name = 'res.users', relation = 'gamification_invited_user_ids_rel',
        string="Suggest to users")

    line_ids = fields.One2many('gamification.challenge.line', 'challenge_id',
        string='Lines',
        help="List of goals that will be set",
        required=True, copy=True)

    reward_id = fields.Many2one('gamification.badge', string="For Every Succeding User")
    reward_first_id = fields.Many2one('gamification.badge', string="For 1st user")
    reward_second_id = fields.Many2one('gamification.badge', string="For 2nd user")
    reward_third_id = fields.Many2one('gamification.badge', string="For 3rd user")
    reward_failure = fields.Boolean('Reward Bests if not Succeeded?', default=False)
    reward_realtime = fields.Boolean('Reward as soon as every goal is reached',
        help="With this option enabled, a user can receive a badge only once. The top 3 badges are still rewarded only at the end of the challenge.", default=True)

    visibility_mode = fields.Selection([
            ('personal', 'Individual Goals'),
            ('ranking', 'Leader Board (Group Ranking)'),
        ],
        string="Display Mode", required=True, default='personal')

    report_message_frequency = fields.Selection([
            ('never', 'Never'),
            ('onchange', 'On change'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('yearly', 'Yearly')
        ],
        string="Report Frequency", required=True, default='never')
    report_message_group_id = fields.Many2one('mail.group',
        string='Send a copy to',
        help='Group that will receive a copy of the report in addition to the user')
    report_template_id = fields.Many2one('email.template', string="Report Template", required=True, default=lambda self, *a, **k: self._get_report_template(*a, **k))
    remind_update_delay = fields.Integer('Non-updated manual goals will be reminded after',
        help="Never reminded if no value or zero is specified.")
    last_report_date = fields.Date('Last Report Date', default=fields.date.today())
    next_report_date = fields.Date(compute = '_get_next_report_date',
        string='Next Report Date', store=True)

    category = fields.Selection(lambda s, *a, **k: s._get_categories(*a, **k),
        string="Appears in", help="Define the visibility of the challenge through menus", required=True, default='hr')


    @api.model
    def create(self, vals):
        """Overwrite the create method to add the user of groups"""

        if vals.get('user_domain'):
            user_ids = self._get_challenger_users(vals.get('user_domain'))

            if not vals.get('user_ids'):
                vals['user_ids'] = []
            vals['user_ids'] += [(4, user_id) for user_id in user_ids]

        return super(gamification_challenge, self).create(vals)

    @api.multi
    def write(self, vals):

        if vals.get('user_domain'):
            user_ids = self._get_challenger_users(vals.get('user_domain'))

            if not vals.get('user_ids'):
                vals['user_ids'] = []
            vals['user_ids'] += [(4, user_id) for user_id in user_ids]

        write_res = super(gamification_challenge, self).write(vals)

        if vals.get('report_message_frequency', 'never') != 'never':
            # _recompute_challenge_users do not set users for challenges with no reports, subscribing them now
            for challenge in self:
                self.message_subscribe(self._cr, self._uid, [challenge.id], [user.partner_id.id for user in challenge.user_ids], context=self._context)

        if vals.get('state') == 'inprogress':
            self._recompute_challenge_users()
            self._generate_goals_from_challenge()

        elif vals.get('state') == 'done':
            self.check_challenge_reward(force=True)

        elif vals.get('state') == 'draft':
            # resetting progress
            if self.pool['gamification.goal'].search(self._cr, self._uid, [('challenge_id', 'in', self._ids), ('state', '=', 'inprogress')], context=self._context):
                raise except_orm(_("Error"), 
                                 _("You can not reset a challenge with unfinished goals."))
        return write_res


    ##### Update #####
#need to change cron timing in .xml file
    @api.model
    def _cron_update(self):
        """Daily cron check.

        - Start planned challenges (in draft and with start_date = today)
        - Create the missing goals (eg: modified the challenge to add lines)
        - Update every running challenge
        """
        # start scheduled challenges
        planned_challenge_ids = self.search([
            ('state', '=', 'draft'),
            ('start_date', '<=', fields.date.today())])
        if planned_challenge_ids:
            planned_challenge_ids.write( {'state': 'inprogress'})

        # close scheduled challenges
        planned_challenge_ids = self.search([
            ('state', '=', 'inprogress'),
            ('end_date', '>=', fields.date.today())])
        if planned_challenge_ids:
            planned_challenge_ids.write({'state': 'done'})
        # print"++++++++++++++++++++++++",self, self._ids, self._context
        if not self:
            self = self.search([('state', '=', 'inprogress')])
            # print"++++++++++++++++++++++++",self, self._ids

        # in cron mode, will do intermediate commits
        # TODO in trunk: replace by parameter
        self = self.with_context(commit_gamification=True)
        return self._update_all()

    @api.multi
    def _update_all(self):
        """Update the challenges and related goals

        :param list(int) ids: the ids of the challenges to update, if False will
        update only challenges in progress."""
        # print"++++++++++++++++++check when self is 0 in _update_all+++++",self, self._context
        if not self:
            return True

        goal_obj = self.pool['gamification.goal']

        # we use yesterday to update the goals that just ended
        yesterday = date.today() - timedelta(days=1)
        goal_ids = goal_obj.search(self._cr, self._uid, [
            ('challenge_id', 'in', self._ids),
            '|',
                ('state', '=', 'inprogress'),
                '&',
                    ('state', 'in', ('reached', 'failed')),
                    '|',
                        ('end_date', '>=', yesterday.strftime(DF)),
                        ('end_date', '=', False)
        ], context=self._context)
        # update every running goal already generated linked to selected challenges
        goal_obj.update(self._cr, self._uid, goal_ids, context=self._context)

        self._recompute_challenge_users()
        self._generate_goals_from_challenge()

        for challenge in self:
            if challenge.last_report_date != fields.date.today():
                # goals closed but still opened at the last report date
                closed_goals_to_report = goal_obj.search(self._cr, self._uid, [
                    ('challenge_id', '=', challenge.id),
                    ('start_date', '>=', challenge.last_report_date),
                    ('end_date', '<=', challenge.last_report_date)
                ])

                if challenge.next_report_date and fields.date.today() >= challenge.next_report_date:
                    challenge.report_progress()

                elif len(closed_goals_to_report) > 0:
                    # some goals need a final report
                    challenge.report_progress(subset_goal_ids=closed_goals_to_report)

        self.check_challenge_reward()
        return True

    def quick_update(self, cr, uid, challenge_id, context=None):
        # print"***********************in quick_update : ",challenge_id, self
        """Update all the goals of a specific challenge, no generation of new goals"""
        goal_ids = self.pool.get('gamification.goal').search(cr, uid, [('challenge_id', '=', challenge_id)], context=context)
        self.pool.get('gamification.goal').update(cr, uid, goal_ids, context=context)
        return True

    @api.multi
    def _get_challenger_users(self, domain):
        user_domain = eval(ustr(domain))
        return self.pool['res.users'].search(self._cr, self._uid, user_domain, context=self._context)

    @api.multi
    def _recompute_challenge_users(self):
        """Recompute the domain to add new users and remove the one no longer matching the domain"""
        for challenge in self:
            if challenge.user_domain:
                old_user_ids = [user.id for user in challenge.user_ids]
                new_user_ids = self._get_challenger_users(challenge.user_domain)
                to_remove_ids = list(set(old_user_ids) - set(new_user_ids))
                to_add_ids = list(set(new_user_ids) - set(old_user_ids))

                write_op = [(3, user_id) for user_id in to_remove_ids]
                write_op += [(4, user_id) for user_id in to_add_ids]
                if write_op:
                    challenge.write({'user_ids': write_op})
        return True

    @api.multi
    def action_start(self):
        """Start a challenge"""
        return self.write({'state': 'inprogress'})

    @api.multi
    def action_check(self):
        """Check a challenge

        Create goals that haven't been created yet (eg: if added users)
        Recompute the current value for each goal related"""
        return self._update_all()

    @api.multi
    def action_report_progress(self):
        """Manual report of a goal, does not influence automatic report frequency"""
        self.report_progress()
        return True


    ##### Automatic actions #####
    @api.multi
    def _generate_goals_from_challenge(self):
        """Generate the goals for each line and user.

        If goals already exist for this line and user, the line is skipped. This
        can be called after each change in the list of users or lines.
        :param list(int) ids: the list of challenge concerned"""

        goal_obj = self.pool['gamification.goal']
        for challenge in self:
            (start_date, end_date) = start_end_date_for_period(challenge.period)
            to_update = []

            # if no periodicity, use challenge dates
            if not start_date and challenge.start_date:
                start_date = challenge.start_date
            if not end_date and challenge.end_date:
                end_date = challenge.end_date

            for line in challenge.line_ids:

                # there is potentially a lot of users
                # detect the ones with no goal linked to this line
                date_clause = ""
                query_params = [line.id]
                if start_date:
                    date_clause += "AND g.start_date = %s"
                    query_params.append(start_date)
                if end_date:
                    date_clause += "AND g.end_date = %s"
                    query_params.append(end_date)
            
                query = """SELECT u.id AS user_id
                             FROM res_users u
                        LEFT JOIN gamification_goal g
                               ON (u.id = g.user_id)
                            WHERE line_id = %s
                              {date_clause}
                        """.format(date_clause=date_clause)

                self._cr.execute(query, query_params)
                user_with_goal_ids = self._cr.dictfetchall()

                participant_user_ids = [user.id for user in challenge.user_ids]
                user_without_goal_ids = list(set(participant_user_ids) - set([user['user_id'] for user in user_with_goal_ids]))
                user_squating_challenge_ids = list(set([user['user_id'] for user in user_with_goal_ids]) - set(participant_user_ids))
                if user_squating_challenge_ids:
                    # users that used to match the challenge 
                    goal_to_remove_ids = goal_obj.search(self._cr, self._uid, [('challenge_id', '=', challenge.id), ('user_id', 'in', user_squating_challenge_ids)], context=self._context)
                    goal_obj.unlink(self._cr, self._uid, goal_to_remove_ids, context=self._context)

                values = {
                    'definition_id': line.definition_id.id,
                    'line_id': line.id,
                    'target_goal': line.target_goal,
                    'state': 'inprogress',
                }

                if start_date:
                    values['start_date'] = start_date
                if end_date:
                    values['end_date'] = end_date

                    # the goal is initialised over the limit to make sure we will compute it at least once
                    if line.condition == 'higher':
                        values['current'] = line.target_goal - 1
                    else:
                        values['current'] = line.target_goal + 1

                if challenge.remind_update_delay:
                    values['remind_update_delay'] = challenge.remind_update_delay

                for user_id in user_without_goal_ids:
                    values.update({'user_id': user_id})
                    goal_id = goal_obj.create(self._cr, self._uid, values, context=self._context)
                    to_update.append(goal_id)

            goal_obj.update(self._cr, self._uid, to_update, context=self._context)
        return True

    ##### JS utilities #####

    @api.model
    def _get_serialized_challenge_lines(self, user_id=False, restrict_goal_ids=False, restrict_top=False):
        """Return a serialised version of the goals information if the user has not completed every goal

        :challenge: browse record of challenge to compute
        :user_id: res.users id of the user retrieving progress (False if no distinction, only for ranking challenges)
        :restrict_goal_ids: <list(int)> compute only the results for this subset if gamification.goal ids, if False retrieve every goal of current running challenge
        :restrict_top: <int> for challenge lines where visibility_mode == 'ranking', retrieve only these bests results and itself, if False retrieve all
            restrict_goal_ids has priority over restrict_top

        format list
        # if visibility_mode == 'ranking'
        {
            'name': <gamification.goal.description name>,
            'description': <gamification.goal.description description>,
            'condition': <reach condition {lower,higher}>,
            'computation_mode': <target computation {manually,count,sum,python}>,
            'monetary': <{True,False}>,
            'suffix': <value suffix>,
            'action': <{True,False}>,
            'display_mode': <{progress,boolean}>,
            'target': <challenge line target>,
            'own_goal_id': <gamification.goal id where user_id == uid>,
            'goals': [
                {
                    'id': <gamification.goal id>,
                    'rank': <user ranking>,
                    'user_id': <res.users id>,
                    'name': <res.users name>,
                    'state': <gamification.goal state {draft,inprogress,reached,failed,canceled}>,
                    'completeness': <percentage>,
                    'current': <current value>,
                }
            ]
        },
        # if visibility_mode == 'personal'
        {
            'id': <gamification.goal id>,
            'name': <gamification.goal.description name>,
            'description': <gamification.goal.description description>,
            'condition': <reach condition {lower,higher}>,
            'computation_mode': <target computation {manually,count,sum,python}>,
            'monetary': <{True,False}>,
            'suffix': <value suffix>,
            'action': <{True,False}>,
            'display_mode': <{progress,boolean}>,
            'target': <challenge line target>,
            'state': <gamification.goal state {draft,inprogress,reached,failed,canceled}>,                                
            'completeness': <percentage>,
            'current': <current value>,
        }
        """
        goal_obj = self.pool['gamification.goal']
        (start_date, end_date) = start_end_date_for_period(self.period)

        res_lines = []
        all_reached = True
        for line in self.line_ids:
            line_data = {
                'name': line.definition_id.name,
                'description': line.definition_id.description,
                'condition': line.definition_id.condition,
                'computation_mode': line.definition_id.computation_mode,
                'monetary': line.definition_id.monetary,
                'suffix': line.definition_id.suffix,
                'action': True if line.definition_id.action_id else False,
                'display_mode': line.definition_id.display_mode,
                'target': line.target_goal,
            }
            domain = [
                ('line_id', '=', line.id),
                ('state', '!=', 'draft'),
            ]
            if restrict_goal_ids:
                domain.append(('ids', 'in', restrict_goal_ids))
            else:
                # if no subset goals, use the dates for restriction
                if start_date:
                    domain.append(('start_date', '=', start_date))
                if end_date:
                    domain.append(('end_date', '=', end_date))

            if self.visibility_mode == 'personal':
                if not user_id:
                    raise except_orm(_('Error!'),_("Retrieving progress for personal challenge without user information"))
                domain.append(('user_id', '=', user_id))
                sorting = goal_obj._order
                limit = 1
            else:
                line_data.update({
                    'own_goal_id': False,
                    'goals': [],
                })
                sorting = "completeness desc, current desc"
                limit = False

            goal_ids = goal_obj.search(self._cr, self._uid, domain, order=sorting, limit=limit, context=self._context)
            ranking = 0
            for goal in goal_obj.browse(self._cr, self._uid, goal_ids, context=self._context):
                if self.visibility_mode == 'personal':
                    # limit=1 so only one result
                    line_data.update({
                        'id': goal.id,
                        'current': goal.current,
                        'completeness': goal.completeness,
                        'state': goal.state,
                    })
                    if goal.state != 'reached':
                        all_reached = False
                else:
                    ranking += 1
                    if user_id and goal.user_id.id == user_id:
                        line_data['own_goal_id'] = goal.id
                    elif restrict_top and ranking > restrict_top:
                        # not own goal and too low to be in top
                        continue

                    line_data['goals'].append({
                        'id': goal.id,
                        'user_id': goal.user_id.id,
                        'name': goal.user_id.name,
                        'rank': ranking,
                        'current': goal.current,
                        'completeness': goal.completeness,
                        'state': goal.state,
                    })
                    if goal.state != 'reached':
                        all_reached = False
            if goal_ids:
                res_lines.append(line_data)
        if all_reached:
            return []
        return res_lines

    ##### Reporting #####

    @api.multi
    def report_progress(self, users=False, subset_goal_ids=False):
        """Post report about the progress of the goals

        :param challenge: the challenge object that need to be reported
        :param users: the list(res.users) of users that are concerned by
          the report. If False, will send the report to every user concerned
          (goal users and group that receive a copy). Only used for challenge with
          a visibility mode set to 'personal'.
        :param goal_ids: the list(int) of goal ids linked to the challenge for
          the report. If not specified, use the goals for the current challenge
          period. This parameter can be used to produce report for previous challenge
          periods.
        :param subset_goal_ids: a list(int) of goal ids to restrict the report
        """
        ctx = self._context.copy()
        temp_obj = self.pool['email.template']
        if self.visibility_mode == 'ranking':
            lines_boards = self._get_serialized_challenge_lines(user_id=False, restrict_goal_ids=subset_goal_ids, restrict_top=False)

            # self = self.with_context(challenge_lines=lines_boards)
            ctx['challenge_lines'] = lines_boards
            body_html = temp_obj.render_template(self._cr, self._uid, self.report_template_id.body_html, 'gamification.challenge', self.id, context=ctx)

            # send to every follower and participant of the challenge
            self.message_post(body=body_html,
                              partner_ids=[user.partner_id.id for user in self.user_ids],
                              subtype='mail.mt_comment')
            if self.report_message_group_id:
                self.pool['mail.group'].message_post(self._cr, self._uid, challenge.report_message_group_id.id,
                    body=body_html,
                    context=self._context,
                    subtype='mail.mt_comment')

        else:
            # generate individual reports
            for user in users or self.user_ids:
                goals = self._get_serialized_challenge_lines(user.id, restrict_goal_ids=subset_goal_ids)
                if not goals:
                    continue

                # self = self.with_context(challenge_lines=goals)
                ctx['challenge_lines'] = goals
                body_html = temp_obj.render_template(self._cr, user.id,  self.report_template_id.body_html, 'gamification.challenge', self.id, context=ctx)
                

                # send message only to users, not on the challenge
                self.message_post(body=body_html,
                                  partner_ids=[(4, user.partner_id.id)],
                                  subtype='mail.mt_comment')
                if self.report_message_group_id:
                    self.pool['mail.group'].message_post(self._cr, self._uid, challenge.report_message_group_id.id,
                                                             body=body_html,
                                                             context=self._context,
                                                             subtype='mail.mt_comment')
        return self.write({'last_report_date': fields.date.today()})

    ##### Challenges #####
    # TODO in trunk, remove unused parameter user_id
    @api.multi
    def accept_challenge(self):
        print"*/*/*/*/accept_challenge "
        """The user accept the suggested challenge"""
        return self._accept_challenge(self._uid)

    @api.multi
    def _accept_challenge(self, user_id):
        print"*/*/*/*/_accept_challenge "
        user = self.pool['res.users'].browse(user_id)
        message = "%s has joined the challenge" % user.name
        self.message_post(body=message)
        self.write({'invited_user_ids': [(3, user_id)], 'user_ids': [(4, user_id)]})
        return self._generate_goals_from_challenge()

    # TODO in trunk, remove unused parameter user_id
    @api.multi
    def discard_challenge(self, user_id=None):
        print"*/*/*/*/discard_challenge "
        """The user discard the suggested challenge"""
        return self._discard_challenge(user_id=self._uid)

    @api.multi
    def _discard_challenge(self, user_id):
        print"*/*/*/*/_discard_challenge "
        user = self.pool['res.users'].browse(user_id)
        message = "%s has refused the challenge" % user.name
        self.message_post(body=message)
        return self.write({'invited_user_ids': (3, user_id)})

    @api.one
    def reply_challenge_wizard(self):
        print"*/*/*/*/reply_challenge_wizard "
        result = self.pool['ir.model.data'].get_object_reference(self._cr, self._uid, 'gamification', 'challenge_wizard')
        id = result and result[1] or False
        result = self.pool['ir.actions.act_window'].read(self._cr, self._uid, [id], context=self._context)[0]
        result['res_id'] = self.id
        return result

    @api.multi
    def check_challenge_reward(self, force=False):
        """Actions for the end of a challenge

        If a reward was selected, grant it to the correct users.
        Rewards granted at:
            - the end date for a challenge with no periodicity
            - the end of a period for challenge with periodicity
            - when a challenge is manually closed
        (if no end date, a running challenge is never rewarded)
        """
        commit = self._context.get('commit_gamification', False)
        for challenge in self:
            (start_date, end_date) = start_end_date_for_period(challenge.period, challenge.start_date, challenge.end_date)
            yesterday = date.today() - timedelta(days=1)

            rewarded_users = []
            challenge_ended = end_date == yesterday.strftime(DF) or force
            if challenge.reward_id and (challenge_ended or challenge.reward_realtime):
                # not using start_date as intemportal goals have a start date but no end_date
                reached_goals = self.pool['gamification.goal'].read_group(self._cr, self._uid, [
                    ('challenge_id', '=', challenge.id),
                    ('end_date', '=', end_date),
                    ('state', '=', 'reached')
                ], fields=['user_id'], groupby=['user_id'], context=self._context)
                for reach_goals_user in reached_goals:
                    if reach_goals_user['user_id_count'] == len(challenge.line_ids):
                        # the user has succeeded every assigned goal
                        user_id = reach_goals_user['user_id'][0]
                        if challenge.reward_realtime:
                            badges = self.env['gamification.badge.user'].search_count([
                                ('challenge_id', '=', challenge.id),
                                ('badge_id', '=', challenge.reward_id.id),
                                ('user_id', '=', user_id)])
                            if badges > 0:
                                # has already recieved the badge for this challenge
                                continue
                        challenge.reward_user(user_id)
                        rewarded_users.append(user_id)
                        if commit:
                            self._cr.commit()

            if challenge_ended:
                # open chatter message
                message_body = _("The challenge %s is finished." % challenge.name)

                if rewarded_users:
                    user_names = self.pool['res.users'].name_get(self._cr, self._uid, rewarded_users, context=self._context)
                    message_body += _("<br/>Reward (badge %s) for every succeeding user was sent to %s." % (challenge.reward_id.name, ", ".join([name for (user_id, name) in user_names])))
                else:
                    message_body += _("<br/>Nobody has succeeded to reach every goal, no badge is rewared for this challenge.")

                # reward bests
                if challenge.reward_first_id:
                    (first_user, second_user, third_user) = challenge.get_top3_users()
                    if first_user:
                        challenge.reward_user(first_user.id)
                        message_body += _("<br/>Special rewards were sent to the top competing users. The ranking for this challenge is :")
                        message_body += "<br/> 1. %s - %s" % (first_user.name, challenge.reward_first_id.name)
                    else:
                        message_body += _("Nobody reached the required conditions to receive special badges.")

                    if second_user and challenge.reward_second_id:
                        challenge.reward_user(second_user.id)
                        message_body += "<br/> 2. %s - %s" % (second_user.name, challenge.reward_second_id.name)
                    if third_user and challenge.reward_third_id:
                        challenge.reward_user(third_user.id)
                        message_body += "<br/> 3. %s - %s" % (third_user.name, challenge.reward_third_id.name)

                challenge.message_post(partner_ids=[user.partner_id.id for user in challenge.user_ids],
                    body=message_body
                    )
                if commit:
                    self._cr.commit()

        return True

    @api.multi
    def get_top3_users(self):
        """Get the top 3 users for a defined challenge

        Ranking criterias:
            1. succeed every goal of the challenge
            2. total completeness of each goal (can be over 100)
        Top 3 is computed only for users succeeding every goal of the challenge,
        except if reward_failure is True, in which case every user is
        considered.
        :return: ('first', 'second', 'third'), tuple containing the res.users
        objects of the top 3 users. If no user meets the criterias for a rank,
        it is set to False. Nobody can receive a rank is noone receives the
        higher one (eg: if 'second' == False, 'third' will be False)
        """
        goal_obj = self.pool['gamification.goal']
        (start_date, end_date) = start_end_date_for_period(self.period, self.start_date, self.end_date)
        challengers = []
        for user in self.user_ids:
            all_reached = True
            total_completness = 0
            # every goal of the user for the running period
            goal_ids = goal_obj.search(self._cr, self._uid, [
                ('challenge_id', '=', self.id),
                ('user_id', '=', user.id),
                ('start_date', '=', start_date),
                ('end_date', '=', end_date)
            ], context=self._context)
            for goal in goal_obj.browse(self._cr, self._uid, goal_ids, context=self._context):
                if goal.state != 'reached':
                    all_reached = False
                if goal.definition_condition == 'higher':
                    # can be over 100
                    total_completness += 100.0 * goal.current / goal.target_goal
                elif goal.state == 'reached':
                    # for lower goals, can not get percentage so 0 or 100
                    total_completness += 100

            challengers.append({'user': user, 'all_reached': all_reached, 'total_completness': total_completness})
        sorted_challengers = sorted(challengers, key=lambda k: (k['all_reached'], k['total_completness']), reverse=True)

        if len(sorted_challengers) == 0 or (not self.reward_failure and not sorted_challengers[0]['all_reached']):
            # nobody succeeded
            return (False, False, False)
        if len(sorted_challengers) == 1 or (not self.reward_failure and not sorted_challengers[1]['all_reached']):
            # only one user succeeded
            return (sorted_challengers[0]['user'], False, False)
        if len(sorted_challengers) == 2 or (not self.reward_failure and not sorted_challengers[2]['all_reached']):
            # only one user succeeded
            return (sorted_challengers[0]['user'], sorted_challengers[1]['user'], False)
        return (sorted_challengers[0]['user'], sorted_challengers[1]['user'], sorted_challengers[2]['user'])

    @api.one
    def reward_user(self, user_id):
        """Create a badge user and send the badge to him

        :param user_id: the user to reward
        :param badge_id: the concerned badge
        """
        badge_user_obj = self.env['gamification.badge.user']
        user_badge = badge_user_obj.create({'user_id': user_id, 'badge_id': self.reward_id.id, 'challenge_id':self._ids[0]})
        return user_badge._send_badge()


class gamification_challenge_line(models.Model):
    """Gamification challenge line

    Predifined goal for 'gamification_challenge'
    These are generic list of goals with only the target goal defined
    Should only be created for the gamification_challenge object
    """

    _name = 'gamification.challenge.line'
    _description = 'Gamification generic goal for challenge'
    _order = "sequence, id"

    @api.onchange('definition_id')
    def on_change_definition_id(self):
        if not self.definition_id:
            self.definition_id = False
            return
        self.condition = self.definition_id.condition
        self.definition_full_suffix = self.definition_id.full_suffix

    name = fields.Char(related='definition_id.name', string="Name")
    challenge_id = fields.Many2one('gamification.challenge',
        string='Challenge',
        required=True,
        ondelete="cascade")
    definition_id = fields.Many2one('gamification.goal.definition',
        string='Goal Definition',
        required=True,
        ondelete="cascade")
    target_goal = fields.Float('Target Value to Reach',
        required=True)
    sequence = fields.Integer('Sequence',
        help='Sequence number for ordering', default=1)
    condition = fields.Selection(related='definition_id.condition',readonly=True, string="Condition", selection=[('lower', '<='), ('higher', '>=')])
    definition_suffix = fields.Char(related='definition_id.suffix', readonly=True, string="Unit")
    definition_monetary = fields.Boolean(related='definition_id.monetary', readonly=True, string="Monetary")
    definition_full_suffix = fields.Char(related='definition_id.full_suffix', readonly=True, string="Suffix")