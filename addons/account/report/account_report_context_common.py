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

from openerp import models, fields, api, _
from xlwt import Workbook, easyxf
from openerp.exceptions import Warning


class account_report_context_common(models.TransientModel):
    _name = "account.report.context.common"
    _description = "A particular context for a financial report"

    @api.model
    def _get_context_by_report_name(self, name):
        if name == 'financial_report':
            return self.env['account.financial.report.context']

    @api.depends('create_uid')
    @api.one
    def _get_multi_company(self):
        group_multi_company = self.env['ir.model.data'].xmlid_to_object('base.group_multi_company')
        if self.create_uid in group_multi_company.users.ids:
            return True
        return False

    name = fields.Char()
    date_from = fields.Date("Start date")
    date_to = fields.Date("End date")
    target_move = fields.Selection([('posted', 'All posted entries'), ('all', 'All entries')],
                                   'Target moves', default='posted', required=True)
    multi_company = fields.Boolean('Allow multi-company', compute=_get_multi_company, store=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda s: s.env.user.company_id)
    date_filter = fields.Char('Date filter used', default=None)

    @api.model
    def get_companies(self):
        return self.env['res.company'].search([])

    @api.multi
    def remove_line(self, line_id):
        raise Warning(_('remove_line not implemented'))

    @api.multi
    def add_line(self, line_id):
        raise Warning(_('add_line not implemented'))

    def get_columns_names(self):
        raise Warning(_('get_columns_names not implemented'))

    # def get_csv(self, response):
    #     book = Workbook()
    #     report_id = self.financial_report_id
    #     sheet = book.add_sheet(report_id.name)

    #     title_style = easyxf('font: bold true; borders: bottom medium;')
    #     level_0_style = easyxf('font: bold true; borders: bottom medium, top medium; pattern: pattern solid;')
    #     level_0_style_left = easyxf('font: bold true; borders: bottom medium, top medium, left medium; pattern: pattern solid;')
    #     level_0_style_right = easyxf('font: bold true; borders: bottom medium, top medium, right medium; pattern: pattern solid;')
    #     level_1_style = easyxf('font: bold true; borders: bottom medium, top medium;')
    #     level_1_style_left = easyxf('font: bold true; borders: bottom medium, top medium, left medium;')
    #     level_1_style_right = easyxf('font: bold true; borders: bottom medium, top medium, right medium;')
    #     level_2_style = easyxf('font: bold true; borders: top medium;')
    #     level_2_style_left = easyxf('font: bold true; borders: top medium, left medium;')
    #     level_2_style_right = easyxf('font: bold true; borders: top medium, right medium;')
    #     level_3_style = easyxf()
    #     level_3_style_left = easyxf('borders: left medium;')
    #     level_3_style_right = easyxf('borders: right medium;')
    #     account_style = easyxf('font: italic true;')
    #     account_style_left = easyxf('font: italic true; borders: left medium;')
    #     account_style_right = easyxf('font: italic true; borders: right medium;')
    #     upper_line_style = easyxf('borders: top medium;')
    #     def_style = easyxf()

    #     sheet.col(0).width = 10000

    #     balance_y = 1
    #     sheet.write(0, 0, 'Name', title_style)
    #     if report_id.debit_credit and not self.comparison:
    #         sheet.write(0, 1, 'Debit', title_style)
    #         sheet.write(0, 2, 'Credit', title_style)
    #         balance_y = 3
    #     sheet.write(0, balance_y, 'Balance', title_style)

    #     x_offset = 1
    #     lines = report_id.line.get_lines_with_context(self)
    #     for x in range(0, len(lines)):
    #         if lines[x].get('level') == 0:
    #             for y in range(0, balance_y + 1):
    #                 sheet.write(x + x_offset, y, None, upper_line_style)
    #             x_offset += 1
    #             style_left = level_0_style_left
    #             style_right = level_0_style_right
    #             style = level_0_style
    #         elif lines[x].get('level') == 1:
    #             for y in range(0, balance_y + 1):
    #                 sheet.write(x + x_offset, y, None, upper_line_style)
    #             x_offset += 1
    #             style_left = level_1_style_left
    #             style_right = level_1_style_right
    #             style = level_1_style
    #         elif lines[x].get('level') == 2:
    #             style_left = level_2_style_left
    #             style_right = level_2_style_right
    #             style = level_2_style
    #         elif lines[x].get('level') == 3:
    #             style_left = level_3_style_left
    #             style_right = level_3_style_right
    #             style = level_3_style
    #         elif lines[x].get('type') == 'account_id':
    #             style_left = account_style_left
    #             style_right = account_style_right
    #             style = account_style
    #         else:
    #             style = def_style
    #             style_left = def_style
    #             style_right = def_style
    #         sheet.write(x + x_offset, 0, lines[x]['name'], style_left)
    #         if report_id.debit_credit and not self.comparison:
    #             sheet.write(x + x_offset, 1, lines[x].get('credit', ''), style)
    #             sheet.write(x + x_offset, 2, lines[x].get('debit', ''), style)
    #         sheet.write(x + x_offset, balance_y, lines[x].get('balance', ''), style_right)

    #     for y in range(0, balance_y + 1):
    #         sheet.write(len(lines) + x_offset, y, None, upper_line_style)

    #     book.save(response.stream)
