# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2004-2014 OpenErp S.A. (<http://odoo.com>).
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

from openerp import models, fields, api


class account_financial_report_line(models.Model):
    _name = "account.financial.report.line"
    _description = "Account Report Line"

    @api.one
    def _get_level(self):
        '''Returns the level of a record in the tree structure'''
        level = 0
        if self.parent_id:
            level = self.parent_id.level + 1
        return level

    @api.one
    def _get_children_by_order(self):
        '''returns a dictionary with the key= the ID of a record and value = all its children,
           computed recursively, and sorted by sequence. Ready for the printing'''
        res = []
        res.append(self)
        children = self.browse([('parent_id', '=', id)], order='sequence ASC')
        res += children._get_children_by_order()
        return res

    type = fields.Selection([
        ('types', 'Account Types'),
        ('tags', 'Account Tags'),
        ('sum', 'Sum Of Children'),
        ('formula', 'Formula'),
    ], 'Type', required=True)
    action = fields.Many2one('ir.actions.actions', 'Action',
                             help='Action triggered when clicking on the line')
    figures_type = fields.Selection([
        ('currency', 'Currency'),
        ('percent', 'Percent'),
        ('float', 'Float'),
    ], 'Figures Type')
    display_detail = fields.Selection([
        ('sum', 'Sum Only'),
        ('accounts', 'All Accounts'),
        ('moves', 'All Journal Items')
    ], 'Display Details')
    formula = fields.char('Formula')
    parent_id = fields.Many2one('account.financial.report.line', 'Parent')
    children_ids = fields.One2many('account.financial.report.line', 'parent_id', 'Children')
    financial_report = fields.Many2one('account.financial.report', 'Financial Report')
    level = fields.Integer(compute='_get_level', string='Level', store=True)
