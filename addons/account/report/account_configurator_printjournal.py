# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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


from openerp import models, fields


class AccountReportsConfiguratorPrintJournal(models.TransientModel):
    _name = 'configurator.printjournal'
    _inherit = 'configurator.journal'

    def _get_journals(self):
        return self.env['account.journal'].search_read(
            domain=[('type', 'not in', ('sale', 'purchase', 'sale_refund', 'purchase_refund'))], fields=['name']
        )

    def _get_default_journals(self):
        return self.env['account.journal'].search([('type', 'not in', ('sale', 'purchase', 'sale_refund', 'purchase_refund'))])

    journal_ids = fields.Many2many('account.journal', default=_get_default_journals)

    filter = fields.Char(default='filter_period')
    sort_selection = fields.Char(default='am.name')
