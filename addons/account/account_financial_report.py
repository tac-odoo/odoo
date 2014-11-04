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


class account_financial_report(models.Model):
    _name = "account.financial.report"
    _description = "Account Report"

    title = fields.Char("Report Title")
    target_move = fields.Selection([('posted', 'All Posted Entries'), ('all', 'All Entries')],
                                   'Target Moves', default='posted', required=True)
    date_from = fields.Date("Start Date")
    date_to = fields.Date("End Date")
    filter_id = fields.Many2one('ir.filters', 'Domain', ondelete='cascade')
    group_by = fields.char('Group By')
    credit = fields.Boolean('Show Credit and Debit Columns', default=False)
    comparison = fields.Boolean('Enable Comparison', default=False)
    line = fields.Many2one('account.financial.report.line', 'First/Top Line', required=True)
