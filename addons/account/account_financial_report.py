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
from openerp.tools.safe_eval import safe_eval
from openerp.tools.misc import formatLang
from openerp.report import report_sxw
from datetime import timedelta, datetime
from xlwt import Workbook, easyxf
import calendar


class FormulaLine(object):
    def __init__(self, obj, type='balance'):
        fields = dict((fn, 0.0) for fn in ['balance', 'credit', 'debit'])
        if type == 'balance':
            fields = obj.get_balance()[0]
        elif type == 'sum':
            if obj._name == 'account.financial.report.line':
                fields = obj.get_sum()
            elif obj._name == 'account.move.line':
                field_names = ['balance', 'credit', 'debit']
                res = obj.compute_fields(field_names)
                if res.get(obj.id):
                    for field in field_names:
                        fields[field] = res[obj.id][field]
        self.balance = fields['balance']
        self.credit = fields['credit']
        self.debit = fields['debit']


class FormulaContext(dict):
    def __init__(self, reportLineObj, curObj, *data):
        self.reportLineObj = reportLineObj
        self.curObj = curObj
        return super(FormulaContext, self).__init__(data)

    def __getitem__(self, item):
        if self.get(item):
            return super(FormulaContext, self).__getitem__(item)
        if item == 'sum':
            res = FormulaLine(self.curObj, type='sum')
            self['sum'] = res
            return FormulaLine(self.curObj, type='sum')
        if item == 'NDays':
            d1 = datetime.strptime(self.curObj.env.context['date_from'], "%Y-%m-%d")
            d2 = datetime.strptime(self.curObj.env.context['date_to'], "%Y-%m-%d")
            res = (d2 - d1).days
            self['NDays'] = res
            return res
        line_id = self.reportLineObj.search([('code', '=', item)], limit=1)
        if line_id:
            res = FormulaLine(line_id)
            self[item] = res
            return FormulaLine(line_id)
        return super(FormulaContext, self).__getitem__(item)


def report_safe_eval(expr, globals_dict=None, locals_dict=None, mode="eval", nocopy=False, locals_builtins=False):
    try:
        res = safe_eval(expr, globals_dict, locals_dict, mode, nocopy, locals_builtins)
    except ValueError:
        res = 1
    return res


class report_account_financial_report(models.Model):
    _name = "account.financial.report"
    _description = "Account Report"

    name = fields.Char()
    debit_credit = fields.Boolean('Show Credit and Debit Columns')
    line = fields.Many2one('account.financial.report.line', 'First/Top Line')
    offset_level = fields.Integer('Level at which the report starts', default=0)
    date_filter = fields.Selection([('balance_sheet', 'Balance sheet filters'), ('profit_and_loss', 'Profit and loss filters'),
                                    ('custom', 'No preset filter')],
                                   'Type of date filters', default='custom', required=True)
    no_date_range = fields.Boolean('Not a date range report', default=False, required=True,
                                   help='For report like the balance sheet that do not work with date ranges')


class account_financial_report_line(models.Model):
    _name = "account.financial.report.line"
    _description = "Account Report Line"

    name = fields.Char('Line Name')
    code = fields.Char('Line Code')
    parent_ids = fields.Many2many('account.financial.report.line', 'parent_financial_report_lines', 'parent_id', 'child_id', string='Parents')
    children_ids = fields.Many2many('account.financial.report.line', 'parent_financial_report_lines', 'child_id', 'parent_id', string='Children')
    financial_report = fields.Many2one('account.financial.report', 'Financial Report')
    sequence = fields.Integer('Sequence')
    domain = fields.Char('Domain', default=None)  # Example : ['account_id.tags', 'in', [1, 2, 3]]
    formulas = fields.Char('Formulas')
    groupby = fields.Char('Group By', default=False)
    unfolded = fields.Boolean('Unfolded by default', default=False)
    figure_type = fields.Selection([('float', 'Float'), ('percents', 'Percents'), ('no_unit', 'No Unit')],
                                   'Type of the figure', default='float', required=True)
    closing_balance = fields.Boolean('Closing balance', default=False, required=True)
    opening_year_balance = fields.Boolean('Opening year balance', default=False, required=True)
    hidden = fields.Boolean('Should this line be hidden', default=False, required=True)
    show_domain = fields.Boolean('Show the domain', default=True, required=True)

    def get_sum(self, field_names=None):
        ''' Returns the sum of the amls in the domain '''
        if not field_names:
            field_names = ['balance', 'credit', 'debit']
        res = dict((fn, 0.0) for fn in field_names)
        if self.domain:
            amls = self.env['account.move.line'].search(report_safe_eval(self.domain))
            compute = amls.compute_fields(field_names)
            for aml in amls:
                if compute.get(aml.id):
                    for field in field_names:
                        res[field] += compute[aml.id][field]
        return res

    @api.one
    def get_balance(self, field_names=None):
        if not field_names:
            field_names = ['balance', 'credit', 'debit']
        res = dict((fn, 0.0) for fn in field_names)
        c = FormulaContext(self.env['account.financial.report.line'], self)
        if self.formulas:
            for f in self.formulas.split(';'):
                [field, formula] = f.split('=')
                field = field.strip()
                if field in field_names:
                    res[field] = report_safe_eval(formula, c, nocopy=True)
        return res

    @api.multi
    def get_lines_with_context(self, context_id, level=None):
        if isinstance(context_id, int):
            context_id = self.env['account.financial.report.context'].browse(context_id)
        if not level:
            level = context_id.financial_report_id.offset_level
        return self.with_context(
            date_from=context_id.date_from,
            date_to=context_id.date_to,
            target_move=context_id.target_move,
            unfolded_lines=context_id.unfolded_lines.ids,
            comparison=context_id.comparison,
            date_from_cmp=context_id.date_from_cmp,
            date_to_cmp=context_id.date_to_cmp,
            cash_basis=context_id.cash_basis,
            level=level,
        ).get_lines(context_id.financial_report_id)[0]

    def _format(self, value):
        if self.figure_type == 'float':
            currency_id = self.env.user.company_id.currency_id
            return formatLang(self.env, value, currency_obj=currency_id)
        if self.figure_type == 'percents':
            return str(round(value * 100, 1)) + '%'
        return round(value, 1)

    def _get_gb_name(self, gb_id):
        if self.groupby == 'account_id':
            return self.env['account.account'].browse(gb_id).name_get()[0][1]
        if self.groupby == 'user_type':
            return self.env['account.account.type'].browse(gb_id).name
        return gb_id

    @api.model
    def _build_cmp(self, balance, comp):
        if comp != 0:
            return str(balance/comp * 100) + '%'
        if balance >= 0:
            return '100.0%'
        return '-100.0%'

    @api.one
    def get_lines(self, financial_report_id):
        lines = []
        context = self.env.context
        level = context['level']
        currency_id = self.env.user.company_id.currency_id
        if self.closing_balance or financial_report_id.no_date_range:
            self = self.with_context(closing_bal=True)
        if self.opening_year_balance:
            self = self.with_context(opening_year_bal=True)

        # Computing the lines
        vals = {
            'id': self.id,
            'name': self.name,
            'type': 'line',
            'level': level,
            'unfolded': not 'unfolded_lines' in context or self.id in context['unfolded_lines'],
            'unfoldable': self.domain and self.show_domain or False,
        }

        # listing the columns
        columns = ['balance']
        if financial_report_id.debit_credit and not context['comparison']:
            if not context.get('cash_basis'):
                columns += ['credit', 'debit']
            else:
                columns += ['credit_cash_basis', 'debit_cash_basis']

        # computing the values for the lines
        if self.formulas:
            for key, value in self.get_balance(columns)[0].items():
                vals[key] = self._format(value)
                if key == 'balance':
                    balance = value
            if context['comparison']:
                cmp_line = self.with_context(date_from=context['date_from_cmp'], date_to=context['date_to_cmp'])
                value = cmp_line.get_balance(['balance'])[0]['balance']
                vals['comparison'] = self._format(value)
                vals['comparison_pc'] = self._build_cmp(balance, value)
        if not self.hidden:
            lines.append(vals)

        # if the line has a domain, computing its values
        if self.domain and (not 'unfolded_lines' in context or self.id in context['unfolded_lines']) and self.groupby and self.show_domain:
            aml_obj = self.env['account.move.line']
            amls = aml_obj.search(report_safe_eval(self.domain))

            if self.groupby:
                if len(amls) > 0:
                    select = ',COALESCE(SUM(l.debit-l.credit), 0)'
                    if financial_report_id.debit_credit and not context['comparison']:
                        select += ',SUM(l.credit),SUM(l.debit)'
                    sql = "SELECT l." + self.groupby + "%s FROM account_move_line l WHERE %s AND l.id IN %s GROUP BY l." + self.groupby
                    query = sql % (select, amls._query_get(), str(tuple(amls.ids)))
                    self.env.cr.execute(query)
                    gbs = self.env.cr.fetchall()
                    gbs_cmp = False
                    if context['comparison']:
                        aml_cmp_obj = aml_obj.with_context(date_from=context['date_from_cmp'], date_to=context['date_to_cmp'])
                        aml_cmp_ids = aml_cmp_obj.search(report_safe_eval(self.domain))
                        select = ',COALESCE(SUM(l.debit-l.credit), 0)'
                        query = sql % (select, aml_cmp_ids._query_get(), str(tuple(aml_cmp_ids.ids)))
                        self.env.cr.execute(query)
                        gbs_cmp = dict(self.env.cr.fetchall())

                    for gb in gbs:
                        vals = {'id': gb[0], 'name': self._get_gb_name(gb[0]), 'level': level + 2, 'type': self.groupby}
                        flag = False
                        for column in xrange(1, len(columns) + 1):
                            value = gb[column]
                            vals[columns[column - 1]] = self._format(value)
                            if not currency_id.is_zero(value):
                                flag = True
                        if context['comparison']:
                            if gbs_cmp.get(gb[0]):
                                vals['comparison'] = self._format(gbs_cmp[gb[0]])
                                if not currency_id.is_zero(gbs_cmp[gb[0]]):
                                    flag = True
                                del gbs_cmp[gb[0]]
                            else:
                                vals['comparison'] = self._format(0)
                            vals['comparison_pc'] = self._build_cmp(gb[1], gbs_cmp.get(gb[0], 0))
                        if flag:
                            lines.append(vals)

                    if gbs_cmp:
                        for gb, value in gbs_cmp.items():
                            vals = {'id': gb, 'name': self._get_gb_name(gb), 'level': level + 2, 'type': self.groupby,
                                    'comparison': self._format(value), 'balance': self._format(0), 'comparison_pc': '0%'}
                            if not currency_id.is_zero(gb):
                                lines.append(vals)

            else:
                if context['comparison']:
                    columns += ['comparison']
                    aml_cmp_obj = aml_obj.with_context(date_from=context['date_from_cmp'], date_to=context['date_to_cmp'])
                for aml in amls:
                    vals = {'id': aml.id, 'name': aml.name, 'type': 'aml', 'level': level + 2}
                    c = FormulaContext(self.env['account.financial.report.line'], aml)
                    flag = False
                    if self.formulas:
                        for f in self.formulas.split(';'):
                            [column, formula] = f.split('=')
                            column = column.strip()
                            if column in columns:
                                value = report_safe_eval(formula, c, nocopy=True)
                                vals[column] = self._format(value)
                                if column == 'balance':
                                    balance = value
                                if not aml.company_id.currency_id.is_zero(value):
                                    flag = True
                            if column == 'balance' and context['comparison']:
                                c_cmp = FormulaContext(self.env['account.financial.report.line'], aml_cmp_obj.browse(aml.id))
                                value = report_safe_eval(formula, c_cmp, nocopy=True)
                                vals['comparison'] = self._format(value)
                                if not aml.company_id.currency_id.is_zero(value):
                                    flag = True
                                vals['comparison_pc'] = self._build_cmp(balance, value)
                    if flag:
                        lines.append(vals)

        new_lines = self.children_ids.with_context(level=level+1).get_lines(financial_report_id)
        result = []
        if level > 0:
            result += lines
        for new_line in new_lines:
            result += new_line
        if level == 0:
            result += lines
        return result


class account_financial_report_context(models.TransientModel):
    _name = "account.financial.report.context"
    _description = "A particular context for a financial report"

    @api.depends('create_uid')
    @api.one
    def _get_multi_company(self):
        group_multi_company = self.env['ir.model.data'].xmlid_to_object('base.group_multi_company')
        if self.create_uid in group_multi_company.users.ids:
            return True
        return False

    name = fields.Char()
    financial_report_id = fields.Many2one('account.financial.report', 'Linked financial report', required=True)
    date_from = fields.Date("Start date")
    date_to = fields.Date("End date")
    target_move = fields.Selection([('posted', 'All posted entries'), ('all', 'All entries')],
                                   'Target moves', default='posted', required=True)
    unfolded_lines = fields.Many2many('account.financial.report.line', 'context_to_line', string='Unfolded lines')
    comparison = fields.Boolean('Enable comparison', default=False)
    date_from_cmp = fields.Date("Start date for comparison", default=lambda s: datetime.today() + timedelta(days=-395))
    date_to_cmp = fields.Date("End date for comparison", default=lambda s: datetime.today() + timedelta(days=-365))
    cash_basis = fields.Boolean('Enable cash basis columns', default=False)
    multi_company = fields.Boolean('Allow multi-company', compute=_get_multi_company, store=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda s: s.env.user.company_id)
    date_filter = fields.Char('Date filter used', default=None)
    date_filter_cmp = fields.Char('Compare Date filter used', default=None)

    @api.model
    def create(self, vals):
        if self.env['account.financial.report'].browse(vals['financial_report_id']).date_filter == 'profit_and_loss':
            vals.update({'date_from': datetime.today().replace(day=1)})
        else:
            vals.update({'date_from': datetime.today()})
        if self.env['account.financial.report'].browse(vals['financial_report_id']).date_filter == 'profit_and_loss':
            dt = datetime.today()
            vals.update({'date_to': dt.replace(day=calendar.monthrange(dt.year, dt.month)[1])})
        else:
            vals.update({'date_to': datetime.today()})
        return super(account_financial_report_context, self).create(vals)

    @api.model
    def get_companies(self):
        return self.env['res.company'].search([])

    @api.multi
    def remove_line(self, line_id):
        self.write({'unfolded_lines': [(3, line_id)]})

    @api.multi
    def add_line(self, line_id):
        self.write({'unfolded_lines': [(4, line_id)]})

    def get_csv(self, response):
        book = Workbook()
        report_id = self.financial_report_id
        sheet = book.add_sheet(report_id.name)

        title_style = easyxf('font: bold true; borders: bottom medium;')
        level_0_style = easyxf('font: bold true; borders: bottom medium, top medium; pattern: pattern solid;')
        level_0_style_left = easyxf('font: bold true; borders: bottom medium, top medium, left medium; pattern: pattern solid;')
        level_0_style_right = easyxf('font: bold true; borders: bottom medium, top medium, right medium; pattern: pattern solid;')
        level_1_style = easyxf('font: bold true; borders: bottom medium, top medium;')
        level_1_style_left = easyxf('font: bold true; borders: bottom medium, top medium, left medium;')
        level_1_style_right = easyxf('font: bold true; borders: bottom medium, top medium, right medium;')
        level_2_style = easyxf('font: bold true; borders: top medium;')
        level_2_style_left = easyxf('font: bold true; borders: top medium, left medium;')
        level_2_style_right = easyxf('font: bold true; borders: top medium, right medium;')
        level_3_style = easyxf()
        level_3_style_left = easyxf('borders: left medium;')
        level_3_style_right = easyxf('borders: right medium;')
        account_style = easyxf('font: italic true;')
        account_style_left = easyxf('font: italic true; borders: left medium;')
        account_style_right = easyxf('font: italic true; borders: right medium;')
        upper_line_style = easyxf('borders: top medium;')
        def_style = easyxf()

        sheet.col(0).width = 10000

        balance_y = 1
        sheet.write(0, 0, 'Name', title_style)
        if report_id.debit_credit and not self.comparison:
            sheet.write(0, 1, 'Debit', title_style)
            sheet.write(0, 2, 'Credit', title_style)
            balance_y = 3
        sheet.write(0, balance_y, 'Balance', title_style)

        x_offset = 1
        lines = report_id.line.get_lines_with_context(self)
        for x in range(0, len(lines)):
            if lines[x].get('level') == 0:
                for y in range(0, balance_y + 1):
                    sheet.write(x + x_offset, y, None, upper_line_style)
                x_offset += 1
                style_left = level_0_style_left
                style_right = level_0_style_right
                style = level_0_style
            elif lines[x].get('level') == 1:
                for y in range(0, balance_y + 1):
                    sheet.write(x + x_offset, y, None, upper_line_style)
                x_offset += 1
                style_left = level_1_style_left
                style_right = level_1_style_right
                style = level_1_style
            elif lines[x].get('level') == 2:
                style_left = level_2_style_left
                style_right = level_2_style_right
                style = level_2_style
            elif lines[x].get('level') == 3:
                style_left = level_3_style_left
                style_right = level_3_style_right
                style = level_3_style
            elif lines[x].get('type') == 'account_id':
                style_left = account_style_left
                style_right = account_style_right
                style = account_style
            else:
                style = def_style
                style_left = def_style
                style_right = def_style
            sheet.write(x + x_offset, 0, lines[x]['name'], style_left)
            if report_id.debit_credit and not self.comparison:
                sheet.write(x + x_offset, 1, lines[x].get('credit', ''), style)
                sheet.write(x + x_offset, 2, lines[x].get('debit', ''), style)
            sheet.write(x + x_offset, balance_y, lines[x].get('balance', ''), style_right)

        for y in range(0, balance_y + 1):
            sheet.write(len(lines) + x_offset, y, None, upper_line_style)

        book.save(response.stream)
