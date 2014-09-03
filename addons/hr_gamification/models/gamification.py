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

class hr_gamification_badge_user(models.Model):
    """User having received a badge"""

    _name = 'gamification.badge.user'
    _inherit = ['gamification.badge.user']

    employee_id = fields.Many2one("hr.employee", string='Employee')

    @api.multi
    @api.constrains('employee_id')
    def _check_employee_related_user(self):
        for badge_user in self:
            if badge_user.user_id and badge_user.employee_id:
                if badge_user.employee_id not in badge_user.user_id.employee_ids:
                    raise Warning(_("The selected employee does not correspond to the selected user."))
        return True

class gamification_badge(models.Model):
    _name = 'gamification.badge'
    _inherit = ['gamification.badge']

    @api.multi
    def get_granted_employees(self):
        employee_ids = []
        for badge_ids in self:
            badge_user_ids = self.env['gamification.badge.user'].search([('badge_id', '=', badge_ids.id), ('employee_id', '!=', False)])
            for badge_user in badge_user_ids:
                employee_ids.append(badge_user.employee_id.id)
        # remove duplicates
        employee_ids = list(set(employee_ids))
        print "employee_idsemployee_idsemployee_idsemployee_ids",employee_ids
        return {
            'type': 'ir.actions.act_window',
            'name': 'Granted Employees',
            'view_mode': 'kanban,tree,form',
            'view_type': 'form',
            'res_model': 'hr.employee',
            'domain': [('id', 'in', employee_ids)]
        }

class hr_employee(models.Model):
    _name = "hr.employee"
    _inherit = "hr.employee"

    @api.multi
    def _get_employee_goals(self):
        """Return the list of goals assigned to the employee"""
        for employee in self:
            employee.goal_ids = self.env['gamification.goal'].search([('user_id', '=', employee.user_id.id), ('challenge_id.category', '=', 'hr')])

    @api.multi
    def _get_employee_badges(self):
        """Return the list of badge_users assigned to the employee"""
        for employee in self:
            employee.badge_ids = self.env['gamification.badge.user'].search([
                '|',
                    ('employee_id', '=', employee.id),
                    '&',
                        ('employee_id', '=', False),
                        ('user_id', '=', employee.user_id.id)
            ])

    @api.multi
    def _has_badges(self):
        """Return the list of badge_users assigned to the employee"""
        for employee in self:
            employee_badge_ids = self.env['gamification.badge.user'].search([
                '|',
                    ('employee_id', '=', employee.id),
                    '&',
                        ('employee_id', '=', False),
                        ('user_id', '=', employee.user_id.id)
            ])
            employee.has_badges = len(employee_badge_ids) > 0

    goal_ids = fields.One2many(compute='_get_employee_goals', comodel_name='gamification.goal', string="Employee HR Goals")
    badge_ids = fields.One2many(compute='_get_employee_badges', comodel_name='gamification.badge.user', string="Employee Badges")
    has_badges = fields.Boolean(compute='_has_badges', string="Has Badges")
