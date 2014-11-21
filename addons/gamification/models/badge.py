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
from openerp import models, api, fields, _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from openerp.exceptions import except_orm, Warning
from datetime import date
import logging

_logger = logging.getLogger(__name__)

class gamification_badge_user(models.Model):
    """User having received a badge"""

    _name = 'gamification.badge.user'
    _description = 'Gamification user badge'
    _order = "create_date desc"
    _rec_name = "badge_name"

    user_id = fields.Many2one('res.users', string="User", required=True, ondelete="cascade")
    sender_id = fields.Many2one('res.users', string="Sender", help="The user who has send the badge")
    badge_id = fields.Many2one('gamification.badge', string='Badge', required=True, ondelete="cascade")
    challenge_id = fields.Many2one('gamification.challenge', string='Challenge originating', help="If this badge was rewarded through a challenge")
    comment = fields.Text('Comment')
    badge_name = fields.Char(related = 'badge_id.name', string="Badge Name")
    create_date = fields.Datetime('Created', readonly=True)
    create_uid = fields.Many2one('res.users', string='Creator', readonly=True)


    @api.multi
    def _send_badge(self):
        """Send a notification to a user for receiving a badge

        Does not verify constrains on badge granting.
        The users are added to the owner_ids (create badge_user if needed)
        The stats counters are incremented
        :param ids: list(int) of badge users that will receive the badge
        """
        print"**********send_badge-goal-v8"
        res = True
        temp_obj = self.pool['email.template']
        user_obj = self.pool['res.users']
        template_id = self.pool['ir.model.data'].get_object(self._cr, self._uid, 'gamification', 'email_template_badge_received', context=self._context)

        body_html = temp_obj.render_template(self._cr, self._uid, template_id.body_html, 'gamification.badge.user', self.id, context=self._context)
        print"body : ",body_html
        print"calling message_post"
        res = self.user_id.message_post(
                       body=body_html,
                       partner_ids=[self.user_id.partner_id.id],
                       subtype='gamification.mt_badge_granted')
        print"res : ",res
        return res

    @api.model
    def create(self, vals):
        badge_rec = self.env['gamification.badge'].browse(vals.get('badge_id'))
        badge_rec.check_granting()
        return super(gamification_badge_user, self).create(vals)

class gamification_badge(models.Model):
    """Badge object that users can send and receive"""

    CAN_GRANT = 1
    NOBODY_CAN_GRANT = 2
    USER_NOT_VIP = 3
    BADGE_REQUIRED = 4
    TOO_MANY = 5

    _name = 'gamification.badge'
    _description = 'Gamification badge'
    _inherit = ['mail.thread']

    @api.multi
    def _get_owners_info(self):
        """Return:
            the list of unique res.users ids having received this badge
            the total number of time this badge was granted
            the total number of users this badge was granted to
        """
        print"++++++++++++++++++_get_owners_info : ",self
        self.write({'stat_count': 0, 'stat_count_distinct': 0, 'unique_owner_ids': []})
        
        self._cr.execute(
            """ SELECT badge_id, count(user_id) as stat_count,
                count(distinct(user_id)) as stat_count_distinct,
                array_agg(distinct(user_id)) as unique_owner_ids
                FROM gamification_badge_user
                WHERE badge_id in %s
                GROUP BY badge_id
            """, (self._ids,))
        print"+++++++cr.fetchall() : ",self._cr.fetchall()
        for (badge_id, stat_count, stat_count_distinct, unique_owner_ids) in self._cr.fetchall():
            self.write(dict(stat_count = stat_count, stat_count_distinct = stat_count_distinct, unique_owner_ids = unique_owner_ids))

    @api.multi
    def _get_badge_user_stats(self):
        print"++++++++++++++++++_get_badge_user_stats : ",self
        """Return stats related to badge users"""
        badge_user_obj = self.env['gamification.badge.user']
        first_month_day = date.today().replace(day=1).strftime(DF)
        for bid in self:
            bid.stat_my = badge_user_obj.search([('badge_id', '=', bid.id), ('user_id', '=', self._uid)], count=True)
            bid.stat_this_month = badge_user_obj.search([('badge_id', '=', bid.id), ('create_date', '>=', first_month_day)], count=True)
            bid.stat_my_this_month = badge_user_obj.search([('badge_id', '=', bid.id), ('user_id', '=', self._uid), ('create_date', '>=', first_month_day)], count=True)
            bid.stat_my_monthly_sending = badge_user_obj.search([('badge_id', '=', bid.id), ('create_uid', '=', self._uid), ('create_date', '>=', first_month_day)], count=True)

    @api.multi
    def _remaining_sending_calc(self):
        """Computes the number of badges remaining the user can send

        0 if not allowed or no remaining
        integer if limited sending
        -1 if infinite (should not be displayed)
        """
        for badge in self:
            if badge._can_grant_badge() != 1:
                # if the user cannot grant this badge at all, result is 0
                badge.remaining_sending = 0
            elif not badge.rule_max:
                # if there is no limitation, -1 is returned which means 'infinite'
                badge.remaining_sending = -1
            else:
                badge.remaining_sending = badge.rule_max_number - badge.stat_my_monthly_sending


    name = fields.Char('Badge', required=True, translate=True)
    description = fields.Text('Description')
    image = fields.Binary("Image", help="This field holds the image used for the badge, limited to 256x256")
    rule_auth = fields.Selection([
            ('everyone', 'Everyone'),
            ('users', 'A selected list of users'),
            ('having', 'People having some badges'),
            ('nobody', 'No one, assigned through challenges'),
        ],
        default='everyone',
        string="Allowance to Grant",
        help="Who can grant this badge",
        required=True)
    rule_auth_user_ids = fields.Many2many('res.users', 'rel_badge_auth_users',
        string='Authorized Users',
        help="Only these people can give this badge")
    rule_auth_badge_ids = fields.Many2many('gamification.badge',
        'gamification_badge_rule_badge_rel', 'badge1_id', 'badge2_id',
        string='Required Badges',
        help="Only the people having these badges can give this badge")
    rule_max = fields.Boolean('Monthly Limited Sending',
        help="Check to set a monthly limit per person of sending this badge")
    rule_max_number = fields.Integer('Limitation Number',
        help="The maximum number of time this badge can be sent per month per person.")
    stat_my_monthly_sending = fields.Integer(
        compute="_get_badge_user_stats",
        string='My Monthly Sending Total',
        multi='badge_users',
        help="The number of time the current user has sent this badge this month.")
    remaining_sending = fields.Integer(
        compute='_remaining_sending_calc',
        string='Remaining Sending Allowed',
        help="If a maxium is set")
    challenge_ids = fields.One2many('gamification.challenge', 'reward_id',
        string="Reward of Challenges")
    goal_definition_ids = fields.Many2many('gamification.goal.definition', 'badge_unlocked_definition_rel',
        string='Rewarded by',
        help="The users that have succeeded theses goals will receive automatically the badge.")
    owner_ids = fields.One2many('gamification.badge.user', 'badge_id',
        string='Owners', help='The list of instances of this badge granted to users')
    active = fields.Boolean('Active', default=True)

    unique_owner_ids = fields.Many2many(
        "res.users",
        compute='_get_owners_info',
        string="Unique Owners",
        help="The list of unique users having received this badge.")
    stat_count = fields.Integer(
        compute='_get_owners_info',
        string='Total', 
        required=True,
        help="The number of time this badge has been received.")
    stat_count_distinct = fields.Integer(
        compute='_get_owners_info',
        string='Number of users',
        help="The number of time this badge has been received by unique users.")

    stat_this_month = fields.Integer(
        compute='_get_badge_user_stats',
        string='Monthly total',
        help="The number of time this badge has been received this month.")
    stat_my = fields.Integer(
        compute='_get_badge_user_stats',
        string='My Total',
        help="The number of time the current user has received this badge.")
    stat_my_this_month = fields.Integer(
        compute='_get_badge_user_stats',
        string='My Monthly Total',
        help="The number of time the current user has received this badge this month.")

    @api.one
    def check_granting(self):
        """Check the user 'uid' can grant the badge 'badge_id' and raise the appropriate exception
        if not

        Do not check for SUPERUSER_ID
        """
        status_code = self._can_grant_badge()
        if status_code == self.CAN_GRANT:
            return True
        elif status_code == self.NOBODY_CAN_GRANT:
            raise except_orm(_('Warning!'), _('This badge can not be sent by users.'))
        elif status_code == self.USER_NOT_VIP:
            raise except_orm(_('Warning!'), _('You are not in the user allowed list.'))
        elif status_code == self.BADGE_REQUIRED:
            raise except_orm(_('Warning!'), _('You do not have the required badges.'))
        elif status_code == self.TOO_MANY:
            raise except_orm(_('Warning!'), _('You have already sent this badge too many time this month.'))
        else:
            _logger.exception("Unknown badge status code: %d" % int(status_code))
        return False

    @api.one
    def _can_grant_badge(self):
        """Check if a user can grant a badge to another user

        :param uid: the id of the res.users trying to send the badge
        :param badge_id: the granted badge id
        :return: integer representing the permission.
        """
        if self._uid == SUPERUSER_ID:
            return self.CAN_GRANT

        if self.rule_auth == 'nobody':
            return self.NOBODY_CAN_GRANT

        elif self.rule_auth == 'users' and self._uid not in [user.id for user in self.rule_auth_user_ids]:
            return self.USER_NOT_VIP

        elif self.rule_auth == 'having':
            all_user_badges = self.env['gamification.badge.user'].search([('user_id', '=', self._uid)])
            for required_badge in self.rule_auth_badge_ids:
                if required_badge.id not in all_user_badges:
                    return self.BADGE_REQUIRED

        if badge.rule_max and badge.stat_my_monthly_sending >= badge.rule_max_number:
            return self.TOO_MANY

        # badge.rule_auth == 'everyone' -> no check
        return self.CAN_GRANT

    @api.one
    def check_progress(self):
        try:
            model, res_id = self.pool['ir.model.data'].get_object_reference(self._cr, self._uid, 'gamification', 'badge_hidden')
        except ValueError:
            return True
        badge_user_obj = self.env['gamification.badge.user']
        if not badge_user_obj.search([('user_id', '=', uid), ('badge_id', '=', res_id)]):
            values = {
                'user_id': self._uid,
                'badge_id': res_id,
            }
            badge_user_obj.create(values)
        return True
