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

from openerp import models, fields, api, exceptions
from openerp.tools.safe_eval import safe_eval
from openerp.tools.translate import _
import re
import time


class report_account_financial_report(models.Model):
    _name = "report.account.report_financial"
    _description = "Account Report"
    _template = "account.report_financial"

    name = fields.Char("Name")
    title = fields.Char("Report Title")
    target_move = fields.Selection([('posted', 'All Posted Entries'), ('all', 'All Entries')],
                                   'Target Moves', default='posted', required=True)
    date_from = fields.Date("Start Date")
    date_to = fields.Date("End Date")
    debit_credit = fields.Boolean('Show Credit and Debit Columns')
    balance = fields.Boolean('Show Balance Column')
    cash_basis = fields.Boolean('Allow Cash Basis Method')
    comparison = fields.Boolean('Enable Comparison')
    line = fields.Many2one('account.financial.report.line', 'First/Top Line')

    @api.one
    @api.constrains('debit_credit', 'balance', 'comparison')
    def _check_columns(self):
        if not (self.debit_credit or self.balance or self.comparison):
            raise exceptions.ValidationError("Report needs at least one column")

    def _get_account(self, data):
        if data.get('form', False) and data['form'].get('chart_account_id', False):
            return self.env['account.account'].browse(data['form']['chart_account_id']).name
        return ''

    def _get_target_move(self, data):
        if self.target_move == 'all':
            return _('All Entries')
        return _('All Posted Entries')

    def _get_start_date(self, data):
        if data.get('form', False) and data['form'].get('date_from', False):
            return data['form']['date_from']
        return ''

    def _get_end_date(self, data):
        if data.get('form', False) and data['form'].get('date_to', False):
            return data['form']['date_to']
        return ''

    @api.multi
    def render_html(self, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('account.report_financial')
        report_id = self.browse(data['form']['account_report_id'][0])
        docargs = {
            'doc_ids': report_id.id,
            'doc_model': report.model,
            'docs': report_id,
            'get_lines': report_id.line.get_lines,
            'get_account': self._get_account,
            'get_target_move': self._get_target_move,
            'get_start_date': self._get_start_date,
            'get_end_date': self._get_end_date,
            'time': time,
            'data': data,
            'formatLang': lambda val, currency_obj=None, date=None: val,
        }
        return report_obj.render('account.report_financial', docargs)


class account_financial_report_line(models.Model):
    _name = "account.financial.report.line"
    _description = "Account Report Line"

    @api.one
    @api.depends('parent_id')
    def _get_level(self):
        '''Sets the level of a record in the tree structure'''
        level = 0
        if self.parent_id:
            level = self.parent_id.level + 1
        self.level = level

    @api.multi
    def _get_children_by_order(self):
        '''returns a all its children, computed recursively, and sorted by sequence. Ready for the printing'''
        res = []
        for line in self:
            res.append(line)
            if line.show:
                children = line.search([('parent_id', '=', line.id)], order='sequence ASC')
                res += children._get_children_by_order()
        return res

    @api.one
    def _get_balance(self, field_names):
        account_obj = self.env['account.account']
        res = dict((fn, 0.0) for fn in field_names)
        if self.type == 'types':
            # it's the sum the leaf accounts with such an account type
            report_types = [x.id for x in self.account_type_ids]
            account_ids = account_obj.search([('user_type', 'in', report_types), ('type', '!=', 'view')])
            for a in account_ids:
                for field in field_names:
                    res[field] += getattr(a, field)
        elif self.type == 'sum':
            # it's the sum of the children of this account.report
            res2 = self.children_ids._get_balance(field_names)
            for value in res2:
                for field in field_names:
                    res[field] += value[field]
        elif self.type == 'formula':
            # a formula is used to tell what should be displayed
            for field in field_names:
                formula = '0'
                for form in self.formulas:
                    if form.column == field:
                        formula = form.formula
                formula = self.formula
                formula.replace('#Days', '1')
                formula.replace('#Month', '1')
                blocks = re.findall('\[.*\]', self.formula)
                for block in blocks:
                    split_block = block.split(',')
                    report_code = split_block[0]
                    column = 'balance'
                    if len(split_block) == 2:
                        column = split_block[1]
                    target_report = self.search([('code', '=', report_code)], limit=1)
                    value = target_report._get_balance(column)
                    formula.replace(block, value)
                res[field] += safe_eval(formula)
        return res

    @api.one
    @api.constrains('formulas')
    def _check_formulas(self):
        counters = {
            'debit': 0,
            'credit': 0,
            'balance': 0,
            'Comparison': 0,
        }
        for formula in self.formulas:
            counters[formula.column] += 1
            if counters[formula.column] > 1:
                raise exceptions.ValidationError("A report line can only have one formula per column")

    name = fields.Char('Line Name')
    code = fields.Char('Line Code')
    type = fields.Selection([
        ('types', 'Account Types'),
        ('tags', 'Account Tags'),
        ('filter', 'Domain'),
        ('sum', 'Sum Of Children'),
        ('formula', 'Formula'),
    ], 'Type', required=True, default='sum')
    action = fields.Selection([
        ('unclickable', 'Unclickable'),
        ('move_lines', 'Display the move lines for this account'),
        ('unreconciled', 'Display the unreconciled lines for this account'),
        ('move', 'Display the move in details'),
    ], 'Onclick Action', default='unclickable')
    figures_type = fields.Selection([
        ('currency', 'Currency'),
        ('percent', 'Percent'),
        ('float', 'Float'),
    ], 'Figures Type')
    display_detail = fields.Selection([
        ('sum', 'Sum Only'),
        ('accounts', 'All Accounts'),
        ('moves', 'All Journal Items'),
        ('no_detail', 'No Detail'),
    ], 'Display Details')
    parent_id = fields.Many2one('account.financial.report.line', 'Parent')
    children_ids = fields.One2many('account.financial.report.line', 'parent_id', 'Children')
    financial_report = fields.Many2one('report.account.report_financial', 'Financial Report')
    level = fields.Integer(compute='_get_level', string='Level', store=True)
    sequence = fields.Integer('Sequence')
    account_type_ids = fields.Many2many('account.account.type', 'account_account_financial_report_line_type',
                                        'line_id', 'account_type_id', 'Account Types')
    sign = fields.Selection([
        (-1, 'Reverse balance sign'),
        (1, 'Preserve balance sign')
    ], 'Sign on Reports', required=True, default=1,
       help="For accounts that are typically more debited than credited and that you would like to "
            "print as negative amounts in your reports, you should reverse the sign of the balance; e.g.: "
            "Expense account. The same applies for accounts that are typically more credited than debited "
            "and that you would like to print as positive amounts in your reports; e.g.: Income account.")
    ir_filter_id = fields.Many2one('ir.filters', 'Domain', ondelete='cascade')
    group_by = fields.Char('Group By')
    formulas = fields.Many2many('account.financial.report.line.formula', 'account_formula_line',
                                'line_id', 'formula_id', 'Formulas')
    show = fields.Boolean('Show Content', default=False)

    @api.multi
    def get_lines_from_js(self, financial_report_id):
        return self.get_lines({'form': {'used_context': {}, 'account_report_id': [financial_report_id]}})[1:]

    def get_lines(self, data):
        lines = []
        account_obj = self.env['account.account']
        financial_report = self.env['report.account.report_financial'].browse(data['form']['account_report_id'][0])[0]
        data['form']['used_context'].update(state=financial_report.target_move)
        for line in self.with_context(data['form']['used_context'])._get_children_by_order():
            vals = {
                'id': line.id,
                'name': line.name,
                'type': 'line',
                'level': line.level,
                'account_type': line.type == 'sum' and 'view' or False,  # used to underline the financial line balances
                'show': line.show
            }
            columns = []
            if financial_report.balance:
                columns.append('balance')
            if financial_report.debit_credit:
                columns.append('credit', 'debit')
            for key, value in line._get_balance(columns)[0].items():
                if key == 'balance':
                    vals[key] = value * line.sign or 0.0
                else:
                    vals[key] = value
            #if self.financial_report.comparison:
                #vals['balance_cmp'] = self.pool.get('account.financial.report').browse(self.cr, self.uid, line.id, context=data['form']['comparison_context']).balance * line.sign or 0.0
            lines.append(vals)
            account_ids = []
            if line.display_detail == 'no_detail':
                #the rest of the loop is used to display the details of the financial report, so it's not needed here.
                continue
            # if line.type == 'accounts' and line.account_ids:
            #     account_ids = account_obj._get_children_and_consol(self.cr, self.uid, [x.id for x in line.account_ids])
            if line.type == 'types':
                domain = [('user_type', 'in', [x.id for x in line.account_type_ids])]
                account_ids = account_obj.with_context(data['form']['used_context']).search(domain)
            if account_ids and line.show:
                for account in account_ids:
                    #if there are accounts to display, we add them to the lines with a level equals to their level in
                    #the COA + 1 (to avoid having them with a too low level that would conflicts with the level of data
                    #financial reports for Assets, liabilities...)
                    flag = False
                    vals = {
                        'id': account.id,
                        'name': account.code + ' ' + account.name,
                        'type': 'account',
                        'level': min(account.level + 1, 6),
                        'account_type': account.type,
                        'action': line.action,
                    }
                    if financial_report.balance:
                        vals['balance'] = account.balance != 0 and account.balance * line.sign or account.balance
                    if financial_report.debit_credit:
                        vals['debit'] = account.debit
                        vals['credit'] = account.credit
                    if not account.company_id.currency_id.is_zero(vals['balance']):
                        flag = True
                    # if financial_report.comparison:
                    #     account_id = account_obj.with_context(data['form']['comparison_context']).browse(account.id)
                    #     vals['balance_cmp'] = account_id.balance * line.sign or 0.0
                    #     if not account.company_id.currency_id.is_zero(vals['balance_cmp']):
                    #         flag = True
                    if flag:
                        lines.append(vals)
        return lines


class account_financial_report_line_formula(models.Model):
    _name = "account.financial.report.line.formula"
    _description = "Matching formulas with columns"

    @api.one
    @api.constrains('formula')
    def _check_formula(self):
        formula = self.formula
        if self.type == 'formula':
            blocks = re.findall('\[.*\]', formula)
            for block in blocks:
                split_block = block.split(',')
                if len(split_block) < 1 or len(split_block) > 2:
                    raise exceptions.ValidationError(block + " must have 1 or 2 arguments")
                else:
                    report_line_obj = self.env['account.financial.report.line']
                    if report_line_obj.search_count([('code', '=', split_block[0])]) < 1:
                        raise exceptions.ValidationError("First argument must be a report code in " + block)
                    if len(split_block) == 2 and split_block[1] not in ['balance', 'credit', 'debit', 'comparison']:
                        raise exceptions.ValidationError("Second argument must be a column name in " + block)
                formula.replace(block, '1')
            formula.replace('#Days', '1')
            formula.replace('#Months', '1')
            try:
                int(safe_eval(formula))
            except Exception:
                raise exceptions.ValidationError("Invalid formula")

    column = fields.Selection([('balance', 'Balance'), ('credit', 'Credit'),
                               ('debit', 'Debit'), ('comparison', 'Comparison')],
                              'Column Name')
    formula = fields.Char('Formula')
