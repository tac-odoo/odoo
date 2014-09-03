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
from openerp import api, fields, models
from openerp.exceptions import Warning
from openerp.tools.translate import _

class hr_grant_badge_wizard(models.TransientModel):
    _name = 'gamification.badge.user.wizard'
    _inherit = ['gamification.badge.user.wizard']

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    user_id = fields.Many2one('res.users', related='employee_id.user_id', store=True, string='User')

    @api.multi
    def action_grant_badge(self):
        """Wizard action for sending a badge to a chosen employee"""

        badge_user_obj = self.env['gamification.badge.user']

        for wiz in self:
            if not wiz.user_id:
                raise Warning(_('You can send badges only to employees linked to a user.'))

            if self._uid == wiz.user_id.id:
                raise Warning(_('You can not send a badge to yourself'))

            values = {
                'user_id': wiz.user_id.id,
                'sender_id': self._uid,
                'badge_id': wiz.badge_id.id,
                'employee_id': wiz.employee_id.id,
                'comment': wiz.comment,
            }

            badge_user = badge_user_obj.create(values)
            result = badge_user._send_badge()
        return result
