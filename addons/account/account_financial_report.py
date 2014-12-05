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
from datetime import timedelta, datetime
from xlwt import Workbook, easyxf


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
        line_id = self.reportLineObj.search([('code', '=', item)], limit=1)
        if line_id:
            res = FormulaLine(line_id)
            self[item] = res
            return FormulaLine(line_id)
        return super(FormulaContext, self).__getitem__(item)


class report_account_financial_report(models.Model):
    _name = "account.financial.report"
    _description = "Account Report"

    name = fields.Char()
    debit_credit = fields.Boolean('Show Credit and Debit Columns')
    balance = fields.Boolean('Show Balance Column')
    line = fields.Many2one('account.financial.report.line', 'First/Top Line')
    offset_level = fields.Integer('Level at which the report starts', default=0)

    @api.one
    @api.constrains('debit_credit', 'balance')
    def _check_columns(self):
        if not (self.debit_credit or self.balance):
            raise exceptions.ValidationError("Report needs at least one column")


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

    def get_sum(self, field_names=None):
        ''' Returns the sum of the amls in the domain '''
        if not field_names:
            field_names = ['balance', 'credit', 'debit']
        res = dict((fn, 0.0) for fn in field_names)
        if self.domain:
            amls = self.env['account.move.line'].search(safe_eval(self.domain))
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
        for f in self.formulas.split(';'):
            [field, formula] = f.split('=')
            field = field.strip()
            if field in field_names:
                res[field] = safe_eval(formula, c, nocopy=True)
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

    @api.one
    def get_lines(self, financial_report_id):
        lines = []
        context = self.env.context
        line = self
        level = context['level']
        rml_parser = report_sxw.rml_parse(self.env.cr, self.env.uid, 'financial_report', context=context)
        currency_id = self.env.user.company_id.currency_id
        # Computing the lines
        vals = {
            'id': line.id,
            'name': line.name,
            'type': 'line',
            'level': level,
            'unfolded': not 'unfolded_lines' in context or line.id in context['unfolded_lines'],
            'unfoldable': line.domain and True or False,
        }
        # listing the columns
        columns = []
        if financial_report_id.balance:
            columns.append('balance')
        if financial_report_id.debit_credit:
            if not context.get('cash_basis'):
                columns += ['credit', 'debit']
            else:
                columns += ['credit_cash_basis', 'debit_cash_basis']
        # computing the values for the lines
        for key, value in line.get_balance(columns)[0].items():
            vals[key] = rml_parser.formatLang(value, currency_obj=currency_id)
        if context['comparison']:
            cmp_line = line.with_context(date_from=context['date_from_cmp'], date_to=context['date_to_cmp'])
            value = cmp_line.get_balance(['balance'])[0]['balance']
            vals['comparison'] = rml_parser.formatLang(value, currency_obj=currency_id)
        lines.append(vals)
        # if the line has a domain, computing its values
        if line.domain and (not 'unfolded_lines' in context or line.id in context['unfolded_lines']) and line.groupby:
            aml_obj = self.env['account.move.line']
            amls = aml_obj.search(safe_eval(line.domain))

            if line.groupby:
                if len(amls) > 0:
                    select = ''
                    if financial_report_id.balance:
                        select += ',COALESCE(SUM(l.debit-l.credit), 0)'
                    if financial_report_id.debit_credit:
                        select += ',SUM(l.credit),SUM(l.debit)'
                    sql = "SELECT l."+line.groupby + select + \
                                """ FROM account_move_line l
                                WHERE %s 
                                AND l.id IN %s GROUP BY l.""" + \
                                line.groupby

                    query = sql % (amls._query_get(), str(tuple(amls.ids)))
                    self.env.cr.execute(query)
                    gbs = self.env.cr.fetchall()
                    # if context['comparison']:
                    #     aml_cmp_obj = aml_obj.with_context(date_from=context['date_from_cmp'], date_to=context['date_to_cmp'])

                    for gb in gbs:
                        vals = {
                            'id': gb[0],
                            'name': gb[0],
                            'level': level + 2,
                            'type': line.groupby,
                        }
                        if line.groupby == 'account_id':
                            vals['name'] = self.env['account.account'].browse(gb[0]).name_get()[0][1]
                        flag = False
                        for column in xrange(1, 4):
                            value = gb[column]
                            vals[columns[column - 1]] = rml_parser.formatLang(value, currency_obj=currency_id)
                            if not currency_id.is_zero(value):
                                flag = True
                        if flag:
                            lines.append(vals)

            else:
                if context['comparison']:
                    columns += ['comparison']
                    aml_cmp_obj = aml_obj.with_context(date_from=context['date_from_cmp'], date_to=context['date_to_cmp'])
                for aml in amls:
                    vals = {
                        'id': aml.id,
                        'name': aml.name,
                        'type': 'aml',
                        'level': level + 2,
                    }
                    c = FormulaContext(self.env['account.financial.report.line'], aml)
                    flag = False
                    for f in line.formulas.split(';'):
                        [column, formula] = f.split('=')
                        column = column.strip()
                        if column in columns:
                            value = safe_eval(formula, c, nocopy=True)
                            vals[column] = rml_parser.formatLang(value, currency_obj=currency_id)
                            if not aml.company_id.currency_id.is_zero(value):
                                flag = True
                        if column == 'balance' and context['comparison']:
                            c_cmp = FormulaContext(self.env['account.financial.report.line'], aml_cmp_obj.browse(aml.id))
                            value = safe_eval(formula, c_cmp, nocopy=True)
                            vals['comparison'] = rml_parser.formatLang(value, currency_obj=currency_id)
                            if not aml.company_id.currency_id.is_zero(value):
                                flag = True
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

    @api.onchange('financial_report_id')
    def _compute_unfolded_lines(self):
        self.write({'unfolded_lines': [(5)]})
        for line in self.financial_report_id.line._get_children_by_order():
            if line.unfolded:
                self.write({'unfolded_lines': [(4, line.id)]})

    name = fields.Char()
    financial_report_id = fields.Many2one('account.financial.report', 'Linked financial report')
    date_from = fields.Date("Start date", default=lambda s: datetime.today() + timedelta(days=-30))
    date_to = fields.Date("End date", default=lambda s: datetime.today())
    target_move = fields.Selection([('posted', 'All posted entries'), ('all', 'All entries')],
                                   'Target moves', default='posted', required=True)
    unfolded_lines = fields.Many2many('account.financial.report.line', 'context_to_line', string='Unfolded lines')
    comparison = fields.Boolean('Enable comparison', default=False)
    date_from_cmp = fields.Date("Start date for comparison", default=lambda s: datetime.today() + timedelta(days=-395))
    date_to_cmp = fields.Date("End date for comparison", default=lambda s: datetime.today() + timedelta(days=-365))
    cash_basis = fields.Boolean('Enable cash basis columns', default=False)
    multi_company = fields.Boolean('Allow multi-company', compute=_get_multi_company, store=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda s: s.env.user.company_id)

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
        sheet = book.add_sheet(self.financial_report_id.name)

        title_style = easyxf('font: bold true;', 'borders: bottom thick;')

        sheet.col(1).width = 10000

        sheet.write(0, 0, 'Name', title_style)
        sheet.write(0, 1, 'Debit', title_style)
        sheet.write(0, 2, 'Credit', title_style)
        sheet.write(0, 3, 'Balance', title_style)

        x_offset = 1

        lines = self.financial_report_id.line.get_lines_with_context(self)
        for x in range(0, len(lines)):
            sheet.write(x_offset + x, 0, lines[x]['name'])
            sheet.write(x_offset + x, 1, lines[x]['credit'])
            sheet.write(x_offset + x, 2, lines[x]['debit'])
            sheet.write(x_offset + x, 3, lines[x]['balance'])
        x_offset += len(lines)

        book.save(response.stream)
