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
import re


class account_financial_report(models.Model):
    _name = "account.financial.report"
    _description = "Account Report"

    title = fields.Char("Report Title")
    target_move = fields.Selection([('posted', 'All Posted Entries'), ('all', 'All Entries')],
                                   'Target Moves', default='posted', required=True)
    date_from = fields.Date("Start Date")
    date_to = fields.Date("End Date")
    group_by = fields.Char('Group By')
    debit_credit = fields.Boolean('Show Credit and Debit Columns')
    comparison = fields.Boolean('Enable Comparison')
    line = fields.Many2one('account.financial.report.line', 'First/Top Line')


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
        children = self.search([('parent_id', '=', self.id)], order='sequence ASC')
        res += children._get_children_by_order()
        return res

    @api.one
    @api.constrains('type', 'formula')
    def _check_formula(self):
        formula = self.formula
        if self.type == 'formula':
            blocks = re.findall('\[.*\]', formula)
            for block in blocks:
                split_block = block.split(',')
                if len(split_block) < 1 or len(split_block) > 2:
                    raise exceptions.ValidationError(block + "doesn't have 1 or 2 arguments")
                else:
                    if self.search_count([('code', '=', split_block[0])]) < 1:
                        raise exceptions.ValidationError("First argument must be a report code in " + block)
                    if len(split_block) == 2 and split_block[1] not in ['balance', 'credit', 'debit', 'comparison']:
                        raise exceptions.ValidationError("Second argument must be a column name in " + block)
                formula.replace(block, '1')
            formula.replace('#Days', '1')
            formula.replace('#Months', '1')
            try:
                int(safe_eval(formula))
            except Exception, e:
                raise exceptions.ValidationError("Invalid formula")

    @api.one
    def _get_balance(self, field_names, args):
        '''returns the balance (or other fields) computed for this record. If the record is of type :
               'accounts' : it's the sum of the linked accounts
               'account_type' : it's the sum of leaf accoutns with such an account_type
               'account_report' : it's the amount of the related report
               'sum' : it's the sum of the children of this record (aka a 'view' record)'''
        account_obj = self.env['account.account']
        res = dict((fn, 0.0) for fn in field_names)
        if self.type == 'account_type':
            # it's the sum the leaf accounts with such an account type
            report_types = [x.id for x in self.account_type_ids]
            account_ids = account_obj.search([('user_type', 'in', report_types), ('type', '!=', 'view')])
            for a in account_ids:
                for field in field_names:
                    res[field] += getattr(a, field)
        elif self.type == 'sum':
            # it's the sum of the children of this account.report
            res2 = self.children_ids._get_balance(field_names, False)
            for value in res2:
                for field in field_names:
                    res[field] += value[field]
        elif self.type == 'formula':
            # a formula is used to tell what should be displayed
            formula = self.formula
            formula.replace(' #Days ', )
            formula.replace(' #Month ', )
            blocks = re.findall('\[.*\]', self.formula)
            for block in blocks:
                split_block = block.split(',')
                



    name = fields.Char('Line Name')
    code = fields.Char('Line Code')
    type = fields.Selection([
        ('types', 'Account Types'),
        ('tags', 'Account Tags'),
        ('filter', 'Domain'),
        ('sum', 'Sum Of Children'),
        ('formula', 'Formula'),
    ], 'Type', required=True)
    balance = fields.Integer(compute='_get_balance', string='Balance', multi='balance')
    debit = fields.Integer(compute='_get_balance', string='Debit', multi='balance')
    credit = fields.Integer(compute='_get_balance', string='Credit', multi="balance")
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
        ('moves', 'All Journal Items'),
        ('no_detail', 'No Detail'),
    ], 'Display Details')
    formula = fields.Char('Formula')
    parent_id = fields.Many2one('account.financial.report.line', 'Parent')
    children_ids = fields.One2many('account.financial.report.line', 'parent_id', 'Children')
    financial_report = fields.Many2one('account.financial.report', 'Financial Report')
    level = fields.Integer(compute='_get_level', string='Level', store=True)
    sequence = fields.Integer('Sequence')
    account_type_ids = fields.Many2many('account.account.type', 'account_account_financial_report_line_type', 'line_id', 'account_type_id', 'Account Types')
    sign = fields.Selection([
        (-1, 'Reverse balance sign'),
        (1, 'Preserve balance sign')
    ], 'Sign on Reports', required=True,
       help="For accounts that are typically more debited than credited and that you would like to "
            "print as negative amounts in your reports, you should reverse the sign of the balance; e.g.: "
            "Expense account. The same applies for accounts that are typically more credited than debited "
            "and that you would like to print as positive amounts in your reports; e.g.: Income account.")
    ir_filter_id = fields.Many2one('ir.filters', 'Domain', ondelete='cascade')

    def get_lines(self, data):
        lines = []
        account_obj = self.env['account.account']
        currency_obj = self.env['res.currency']
        for line in self.with_context(data['form']['used_context'])._get_children_by_order():
            vals = {
                'name': line.name,
                'balance': line.balance * line.sign or 0.0,
                'type': 'line',
                'level': line.level,
                'account_type': line.type =='sum' and 'view' or False,#used to underline the financial line balances
            }
            if self.financial_report.debit_credit:
                vals['debit'] = line.debit
                vals['credit'] = line.credit
            #if self.financial_report.comparison:
                #vals['balance_cmp'] = self.pool.get('account.financial.report').browse(self.cr, self.uid, line.id, context=data['form']['comparison_context']).balance * line.sign or 0.0
            lines.append(vals)
            account_ids = []
            if line.display_detail == 'no_detail':
                #the rest of the loop is used to display the details of the financial report, so it's not needed here.
                continue
            # if line.type == 'accounts' and line.account_ids:
            #     account_ids = account_obj._get_children_and_consol(self.cr, self.uid, [x.id for x in line.account_ids])
            # elif line.type == 'account_type' and line.account_type_ids:
            #     account_ids = account_obj.search(self.cr, self.uid, [('user_type', 'in', [x.id for x in line.account_type_ids])])
            if line.type == 'types':
                account_ids = account_obj.search([('user_type', 'in', [x.id for x in line.account_type_ids])])
            if account_ids:
                for account in account_ids:
                    #if there are accounts to display, we add them to the lines with a level equals to their level in
                    #the COA + 1 (to avoid having them with a too low level that would conflicts with the level of data
                    #financial reports for Assets, liabilities...)
                    flag = False
                    vals = {
                        'name': account.code + ' ' + account.name,
                        'balance':  account.balance != 0 and account.balance * line.sign or account.balance,
                        'type': 'account',
                        'level': line.display_detail == 'detail_with_hierarchy' and min(account.level + 1, 6) or 6,#account.level + 1
                        'account_type': account.type,
                    }
                    if self.financial_report.debit_credit:
                        vals['debit'] = account.debit
                        vals['credit'] = account.credit
                    if not currency_obj.is_zero(self.cr, self.uid, account.company_id.currency_id, vals['balance']):
                        flag = True
                    if self.financial_report.comparison:
                        vals['balance_cmp'] = account_obj.browse(self.cr, self.uid, account.id, context=data['form']['comparison_context']).balance * line.sign or 0.0
                        if not currency_obj.is_zero(self.cr, self.uid, account.company_id.currency_id, vals['balance_cmp']):
                            flag = True
                    if flag:
                        lines.append(vals)
        return line
