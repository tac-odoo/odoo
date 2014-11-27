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
from openerp.report import report_sxw
from datetime import timedelta


class FormulaLine(object):
    def __init__(self, obj, type='balance'):
        fields = dict((fn, 0.0) for fn in ['balance', 'credit', 'debit'])
        if type == 'balance':
            fields = obj.get_balance()[0]
        elif type == 'sum':
            if obj._name == 'account.financial.report.line':
                fields = obj.get_sum()
            elif obj._name == 'account.move.line':
                for field in ['balance', 'credit', 'debit']:
                    fields[field] = getattr(obj, field)
        self.balance = fields['balance']
        self.credit = fields['credit']
        self.debit = fields['debit']


class FormulaContext(dict):
    def __init__(self, reportLineObj, curObj, *data):
        self.reportLineObj = reportLineObj
        self.curObj = curObj
        return super(FormulaContext, self).__init__(data)

    def __getitem__(self, item):
        if item == 'sum':
            return FormulaLine(self.curObj, type='sum')
        line_id = self.reportLineObj.search([('code', '=', item)], limit=1)
        if line_id:
            return FormulaLine(line_id)
        return super(FormulaContext, self).__getitem__(item)


class report_account_financial_report(models.Model):
    _name = "account.financial.report"
    _description = "Account Report"

    name = fields.Char()
    debit_credit = fields.Boolean('Show Credit and Debit Columns')
    balance = fields.Boolean('Show Balance Column')
    line = fields.Many2one('account.financial.report.line', 'First/Top Line')

    @api.one
    @api.constrains('debit_credit', 'balance')
    def _check_columns(self):
        if not (self.debit_credit or self.balance):
            raise exceptions.ValidationError("Report needs at least one column")


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

    def _get_children_by_order(self):
        '''returns a all its children, computed recursively, and sorted by sequence. Ready for the printing'''
        res = []
        for line in self:
            res.append(line)
            if line.unfolded:
                children = line.search([('parent_id', '=', line.id)], order='sequence ASC')
                res += children._get_children_by_order()
        return res

    name = fields.Char('Line Name')
    code = fields.Char('Line Code')
    parent_id = fields.Many2one('account.financial.report.line', 'Parent')
    children_ids = fields.One2many('account.financial.report.line', 'parent_id', 'Children')
    financial_report = fields.Many2one('account.financial.report', 'Financial Report')
    level = fields.Integer(compute='_get_level', string='Level', store=True)
    sequence = fields.Integer('Sequence')
    domain = fields.Char('Domain', default=None)  # Example : ['account_id.tags', 'in', [1, 2, 3]]
    formulas = fields.Char('Formulas')
    groupby = fields.Char('Group By')
    unfolded = fields.Boolean('Unfolded by default', default=False)

    def get_sum(self, field_names=None):
        ''' Returns the sum of the amls in the domain '''
        if not field_names:
            field_names = ['balance', 'credit', 'debit']
        res = dict((fn, 0.0) for fn in field_names)
        if self.domain:
            move_line_ids = self.env['account.move.line'].search(safe_eval(self.domain))
            for aml in move_line_ids:
                for field in field_names:
                    res[field] += getattr(aml, field)
        return res

    @api.one
    def get_balance(self, field_names=None):
        if not field_names:
            field_names = ['balance', 'credit', 'debit']
        res = dict((fn, 0.0) for fn in field_names)
        if self.domain:
            move_line_ids = self.env['account.move.line'].search(safe_eval(self.domain))
            for aml in move_line_ids:
                for field in field_names:
                    res[field] += getattr(aml, field)
        c = FormulaContext(self.env['account.financial.report.line'], self)
        for f in self.formulas.split(';'):
            [field, formula] = f.split('=')
            field = field.strip()
            if field in field_names:
                res[field] = safe_eval(formula, c, nocopy=True)
        return res

    @api.multi
    def get_lines(self, financial_report_id, used_context={}):
        lines = []
        rml_parser = report_sxw.rml_parse(self.env.cr, self.env.uid, 'financial_report', context=self.env.context)
        currency_id = self.env.user.company_id.currency_id
        if isinstance(financial_report_id, int):
            financial_report_id = self.env['account.financial.report'].browse(financial_report_id)
        for line in self._get_children_by_order():
            vals = {
                'id': line.id,
                'name': line.name,
                'type': 'line',
                'level': line.level,
                'unfolded': line.unfolded,
            }
            columns = []
            if financial_report_id.balance:
                columns.append('balance')
            if financial_report_id.debit_credit:
                columns.append('credit', 'debit')
            for key, value in line.get_balance(columns)[0].items():
                vals[key] = rml_parser.formatLang(value, currency_obj=currency_id)
            #if self.financial_report_id.comparison:
                #vals['balance_cmp'] = self.pool.get('account.financial.report').browse(self.cr, self.uid, line.id, context=data['form']['comparison_context']).balance * line.sign or 0.0
            lines.append(vals)
            if line.domain and line.unfolded:
                aml_obj = self.env['account.move.line']
                amls = aml_obj.search(safe_eval(line.domain))
                if line.groupby:
                    gbs = [k[line.groupby] for k in aml_obj.read_group(safe_eval(line.domain), [line.groupby], line.groupby)]
                    gb_vals = dict((gb[0], dict((column, 0.0) for column in columns)) for gb in gbs)
                    for aml in amls:
                        c = FormulaContext(self.env['account.financial.report.line'], aml)
                        for f in line.formulas.split(';'):
                            [column, formula] = f.split('=')
                            column = column.strip()
                            if column in columns:
                                gb_vals[getattr(aml, line.groupby).id][column] += safe_eval(formula, c, nocopy=True)
                    for gb in gbs:
                        vals = {
                            'name': gb[1],
                            'level': line.level + 2,
                            'type': line.groupby,
                        }
                        for column in columns:
                            vals[column] = rml_parser.formatLang(gb_vals[gb[0]][column], currency_obj=currency_id)
                        lines.append(vals)
                else:
                    for aml in amls:
                        vals = {
                            'name': aml.name,
                            'type': 'aml',
                            'level': line.level + 2,
                        }
                        c = FormulaContext(self.env['account.financial.report.line'], aml)
                        for f in line.formulas.split(';'):
                            [column, formula] = f.split('=')
                            column = column.strip()
                            if column in columns:
                                vals[column] = rml_parser.formatLang(safe_eval(formula, c, nocopy=True), currency_obj=currency_id)
                        flag = False
                        if not aml.company_id.currency_id.is_zero(aml.balance):
                            flag = True
                        if flag:
                            lines.append(vals)
        return lines


class account_financial_report_context(models.TransientModel):
    _name = "account.financial.report.context"
    _description = "A particular context for a financial report"

    @api.onchange('financial_report_id')
    def _compute_unfolded_lines(self):
        self.write({'unfolded_lines': [(5)]})
        for line in self.financial_report_id.line._get_children_by_order():
            if line.unfolded:
                self.write({'unfolded_lines': [(4, line.id)]})

    @api.model
    def _default_account(self):
        accounts = self.env['account.account'].search(
            [('parent_id', '=', False), ('company_id', '=', self.env.user.company_id.id)],
            limit=1,
        )
        return accounts and accounts[0] or False

    @api.model
    def get_accounts(self):
        return self.env['account.account'].search([('parent_id', '=', False)])

    name = fields.Char()
    financial_report_id = fields.Many2one('account.financial.report', 'Linked Financial Report')
    date_from = fields.Date("Start Date", default=lambda s: fields.Date.today() + timedelta(days=-30))
    date_to = fields.Date("End Date", default=lambda s: fields.Date.today())
    target_move = fields.Selection([('posted', 'All Posted Entries'), ('all', 'All Entries')],
                                   'Target Moves', default='posted', required=True)
    unfolded_lines = fields.Many2many('account.financial.report.line', 'Unfolded Lines')
    chart_account_id = fields.Many2one('account.account', 'Chart of Account', required=True,
                                       domain=[('parent_id', '=', False)], default=_default_account)

    def action_open(self):
        return {
            'url': '/account/financial_report/context/' + str(self.id),
            'type': 'ir.actions.act_url'
        }
