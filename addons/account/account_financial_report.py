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


class FormulaLine(object):
    def __init__(self, line):
        fields = line._get_balance()[0]
        self.balance = fields['balance']
        self.credit = fields['credit']
        self.debit = fields['debit']


class FormulaContext(dict):
    def __init__(self, reportLineObj, *data):
        self.reportLineObj = reportLineObj
        return super(FormulaContext, self).__init__(data)

    def __getitem__(self, item):
        if super(FormulaContext, self).get(item):
            return super(FormulaContext, self).__getitem__(item)
        else:
            line_id = self.reportLineObj.search([('code', '=', item)], limit=1)
            if line_id:
                return FormulaLine(line_id)
            else:
                return super(FormulaContext, self).__getitem__(item)


class report_account_financial_report(models.Model):
    _name = "account.financial.report"
    _description = "Account Report"
    _template = "account.report_financial"

    name = fields.Char("Name")
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

    @api.one
    def _get_balance(self, field_names=None):
        if not field_names:
            field_names = ['balance', 'credit', 'debit']
        res = dict((fn, 0.0) for fn in field_names)
        if self.domain:
            move_line_ids = self.env['account.move.line'].search(safe_eval(self.domain))
            for aml in move_line_ids:
                for field in field_names:
                    res[field] += getattr(aml, field)
        c = FormulaContext(self.env['account.financial.report.line'])
        for f in self.formulas.split(';'):
            [field, formula] = f.split('=')
            field = field.strip()
            if field in field_names:
                c['sum'] = res[field]
                res[field] = safe_eval(formula, c, nocopy=True)
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

    @api.multi
    def get_lines(self, financial_report_id, used_context={}):
        lines = []
        rml_parser = report_sxw.rml_parse(self.env.cr, self.env.uid, 'financial_report', context=self.env.context)
        currency_id = self.env.user.company_id.currency_id
        if isinstance(financial_report_id, int):
            financial_report_id = self.env['account.financial.report'].browse(financial_report_id)
        for line in self.with_context(used_context)._get_children_by_order():
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
            for key, value in line._get_balance(columns)[0].items():
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
                        for column in columns:
                            gb_vals[getattr(aml, line.groupby).id][column] += getattr(aml, column)
                    for gb in gbs:
                        vals = {
                            'name': gb[1],
                            'level': line.level + 1,
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
                            'level': line.level + 1,
                        }
                        for column in columns:
                            vals[column] = rml_parser.formatLang(getattr(aml, column), currency_obj=currency_id)
                        flag = False
                        if not aml.company_id.currency_id.is_zero(aml.balance):
                            flag = True
                        if flag:
                            lines.append(vals)
            # if line.display_detail == 'no_detail':
            #     #the rest of the loop is used to display the details of the financial report, so it's not needed here.
            #     continue
            # if line.type == 'accounts' and line.account_ids:
            #     account_ids = account_obj._get_children_and_consol(self.cr, self.uid, [x.id for x in line.account_ids])
            # if line.type == 'types':
            #     #domain = [('user_type', 'in', [x.id for x in line.account_type_ids])]
            #     account_ids = account_obj.with_context(used_context).search(self.domain)
        return lines
