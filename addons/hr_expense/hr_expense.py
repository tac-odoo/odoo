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

import time

from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning

import openerp.addons.decimal_precision as dp


class hr_expense_sheet(models.Model):

    @api.model
    def _employee_get(self):
        employee = self.env['hr.employee'].search([('user_id', '=', self._uid)], limit=1)
        if employee:
            return employee.id
        return False

    @api.multi
    @api.depends('line_ids.unit_amount', 'line_ids.unit_quantity', 'line_ids.state')
    def _amount(self):
        for expense in self:
            total = 0.0
            for line in expense.line_ids:
                total += line.unit_amount * line.unit_quantity
            expense.amount = total

    _name = "hr_expense.sheet"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = "Expense Sheet"
    _order = "id desc"
    _track = {
        'state': {
            'hr_expense.mt_expense_approved': lambda self, cr, uid, obj, ctx=None: obj.state == 'accepted',
            'hr_expense.mt_expense_refused': lambda self, cr, uid, obj, ctx=None: obj.state == 'cancelled',
            'hr_expense.mt_expense_confirmed': lambda self, cr, uid, obj, ctx=None: obj.state == 'confirm',
        },
    }

    name = fields.Char(string='Expense Sheet', readonly=True, states={'draft':[('readonly', False)], 'confirm':[('readonly', False)]})
    date = fields.Date(string='Date', readonly=True, states={'draft':[('readonly', False)], 'confirm':[('readonly', False)]}, default=fields.Date.context_today)
    journal_id = fields.Many2one('account.journal', string='Force Journal', help = "The journal used when the expense is done.")
    employee_payable_account_id = fields.Many2one('account.account', string='Employee Account', help="Employee payable account")
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, states={'draft':[('readonly', False)], 'confirm':[('readonly', False)]}, default=lambda self: self._employee_get())
    user_id = fields.Many2one('res.users', string='User', required=True, default=lambda self: self.env.user)
    date_confirm = fields.Date(string='Confirmation Date', copy=False,
                                help="Date of the confirmation of the sheet expense. It's filled when the button Confirm is pressed.")
    date_valid = fields.Date(string='Validation Date', copy=False,
                              help="Date of the acceptation of the sheet expense. It's filled when the button Accept is pressed.")
    user_valid = fields.Many2one('res.users', string='Validation By', readonly=True, copy=False,
                                  states={'draft':[('readonly', False)], 'confirm':[('readonly', False)]})
    account_move_id = fields.Many2one('account.move', string='Ledger Posting', copy=False, track_visibility="onchange")
    line_ids = fields.One2many('hr_expense.expense', 'expense_id', string='Expense Lines', copy=True,
                                readonly=True, states={'draft':[('readonly', False)]} )
    note = fields.Text('Note')
    amount = fields.Float(compute='_amount', string='Total Amount', digits=dp.get_precision('Account'), store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True, states={'draft':[('readonly', False)], 'confirm':[('readonly', False)]}, default=lambda self:self.env.user.company_id.currency_id.id)
    department_id = fields.Many2one('hr.department', string='Department', readonly=True, states={'draft':[('readonly', False)], 'confirm':[('readonly', False)]})
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    state = fields.Selection([
        ('draft', 'New'),
        ('cancelled', 'Refused'),
        ('confirm', 'Waiting Approval'),
        ('accepted', 'Approved'),
        ('done', 'Waiting Payment'),
        ('paid', 'Paid'),
        ],
        string='Status', readonly=True, track_visibility='onchange', copy=False, default='draft', required=True,
        help='When the expense request is created the status is \'Draft\'.\n It is confirmed by the user and request is sent to admin, the status is \'Waiting Confirmation\'.\
        \nIf the admin accepts it, the status is \'Accepted\'.\n If the accounting entries are made for the expense request, the status is \'Waiting Payment\'.')

    @api.multi
    def unlink(self):
        for expense in self:
            if expense.state != 'draft':
                raise Warning(_('You can only delete draft expenses!'))
        return super(hr_expense_sheet, self).unlink()

    @api.onchange('currency_id','company_id')
    def onchange_currency_id(self):
        account_journal = self.env['account.journal'].search([('type', '=', 'purchase'), ('currency', '=', self.currency_id.id), ('company_id', '=', self.company_id.id)], limit=1)
        if account_journal:
            self.journal_id = account_journal.id

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id:
            self.department_id = self.employee_id.department_id.id
            self.company_id = self.employee_id.company_id.id

    @api.multi
    def expense_confirm(self):
        if not self.line_ids:
            raise except_orm(_('Error!'), _('You cannot submit expense which has no expense line.'))
        if self.employee_id and self.employee_id.parent_id.user_id:
            self.message_subscribe_users(user_ids=self.employee_id.parent_id.user_id.ids)
        return self.write({'state': 'confirm', 'date_confirm': time.strftime('%Y-%m-%d')})

    @api.multi
    def expense_accept(self):
        for expense in self:
            if expense.state not in ['done','paid']:
                expense.signal_workflow('confirm')
                expense_state = False
                for expense_line in expense.line_ids:
                    if expense_line.state == 'accepted':
                        expense_state = True
                expense.signal_workflow('validate')
                if not expense_state:
                    raise Warning(_('You cannot submit expense sheet which has no expense approved by hr manager.'))
                return expense.write({'state': 'accepted', 'date_valid': time.strftime('%Y-%m-%d'), 'user_valid': expense._uid})

    @api.multi
    def expense_canceled(self):
        return self.write({'state': 'cancelled'})

    @api.multi
    def account_move_get(self):
        '''
        This method prepare the creation of the account move related to the given expense.
        :return: mapping between fieldname and value of account move to create
        '''
        journal_id = False
        if self.journal_id:
            journal_id = self.journal_id.id
        else:
            journal_id = self.env['account.journal'].search([('type', '=', 'purchase'), ('company_id', '=', self.company_id.id)], limit=1)
            if not journal_id:
                raise except_orm(_('Error!'), _("No expense journal found. Please make sure you have a journal with type 'purchase' configured."))
            journal_id = journal_id.id
        return self.env['account.move'].account_move_prepare(journal_id, date=self.date_confirm, ref=self.name, company_id=self.company_id.id)

    @api.model
    def line_get_convert(self, res, part, date):
        partner_id  = self.env['res.partner']._find_accounting_partner(part).id
        return {
            'date_maturity': res.get('date_maturity', False),
            'partner_id': partner_id,
            'name': res['name'][:64],
            'date': date,
            'debit': res['price']>0 and res['price'],
            'credit': res['price']<0 and -res['price'],
            'account_id': res['account_id'],
            'analytic_lines': res.get('analytic_lines', False),
            'amount_currency': res['price']>0 and abs(res.get('amount_currency', False)) or -abs(res.get('amount_currency', False)),
            'currency_id': res.get('currency_id', False),
            'tax_code_id': res.get('tax_code_id', False),
            'tax_amount': res.get('tax_amount', False),
            'ref': res.get('ref', False),
            'quantity': res.get('quantity',1.00),
            'product_id': res.get('product_id', False),
            'product_uom_id': res.get('uos_id', False),
            'analytic_account_id': res.get('account_analytic_id', False),
        }

    @api.multi
    def compute_expense_totals(self, company_currency, account_move_lines):
        '''
        internal method used for computation of total amount of an expense in the company currency and
        in the expense currency, given the account_move_lines that will be created. It also do some small
        transformations at these account_move_lines (for multi-currency purposes)
        
        :param account_move_lines: list of dict
        :rtype: tuple of 3 elements (a, b ,c)
            a: total in company currency
            b: total in hr.expense currency
            c: account_move_lines potentially modified
        '''
        total = 0.0
        total_currency = 0.0
        for i in account_move_lines:
            if self.currency_id.id != company_currency:
                i['currency_id'] = self.currency_id.id
                i['amount_currency'] = i['price']
                i['price'] = self.currency_id.with_context(date=self.date_confirm or time.strftime('%Y-%m-%d')).compute(company_currency, i['price'])
            else:
                i['amount_currency'] = False
                i['currency_id'] = False
            total -= i['price']
            total_currency -= i['amount_currency'] or i['price']
        return total, total_currency, account_move_lines
    
    @api.multi
    def action_move_create(self):
        '''
        main function that is called when trying to create the accounting entries related to an expense
        '''
        if not self.employee_payable_account_id:
            raise except_orm(_('Error!'), _('No employee account payable found for the expense '))

        company_currency = self.company_id.currency_id.id
        diff_currency_p = self.currency_id.id != company_currency

        #create the move that will contain the accounting entries
        move = self.env['account.move'].create(self.account_move_get())
        
        #one account.move.line per expense line (+taxes..)
        expense_move_line = self.move_line_get()
        
        #create one more move line, a counterline for the total on payable account
        total, total_currency, expense_move_line = self.compute_expense_totals(company_currency, expense_move_line)
        
        acc = self.employee_payable_account_id.id or False
        expense_move_line.append({
                'type': 'dest',
                'name': '/',
                'price': total,
                'account_id': acc,
                'date_maturity': self.date_confirm,
                'amount_currency': diff_currency_p and total_currency or False,
                'currency_id': diff_currency_p and self.currency_id.id or False, 
                'ref': self.name
                })

        lines = []
        for move_line in expense_move_line:
            line_convert = self.line_get_convert(move_line, self.employee_id.company_id.partner_id, self.date_confirm)
            lines.append((0,0,line_convert))
        journal_id = move.journal_id
        # post the journal entry if 'Skip 'Draft' State for Manual Entries' is checked
        if journal_id.entry_posted:
            move.button_validate()
        move.line_id = lines
        self.write({'account_move_id': move.id, 'state': 'done'})
        return True

    @api.multi
    def move_line_get(self):
        res = []
        for line in self.line_ids:
            move_line = {}
            if line.state == 'accepted':
                move_line = self.move_line_get_item(line)
            elif line.state == 'confirm':
                line.write({'state':'cancel'})
            if not move_line:
                continue
            res.append(move_line)
            tax_l = []
            base_tax_amount = line.total_amount
            taxes = line.expense_tax_id.compute_all(line.unit_amount, line.unit_quantity, line.product_id, self.user_id.partner_id)['taxes']
            for tax in taxes:
                tax_code_id = tax['base_code_id']
                if not tax_code_id:
                    continue
                res[-1]['tax_code_id'] = tax_code_id
                is_price_include = False
                for tax_price in line.expense_tax_id:
                    is_price_include = tax_price.price_include
                if is_price_include:
                    ## We need to deduce the price for the tax
                    res[-1]['price'] = res[-1]['price']  - (tax['amount'] * tax['base_sign'] or 0.0)
                    # tax amount countains base amount without the tax
                    base_tax_amount = (base_tax_amount - tax['amount']) * tax['base_sign']
                else:
                    base_tax_amount = base_tax_amount * tax['base_sign']

                assoc_tax = {
                             'type':'tax',
                             'name':tax['name'],
                             'price_unit': tax['price_unit'],
                             'quantity': 1,
                             'price':  tax['amount'] * tax['base_sign'] or 0.0,
                             'account_id': tax['account_collected_id'] or move_line['account_id'],
                             'tax_code_id': tax['tax_code_id'],
                             'tax_amount': tax['amount'] * tax['base_sign'],
                             }
                tax_l.append(assoc_tax)
            res[-1]['tax_amount'] = self.currency_id.compute(base_tax_amount, self.company_id.currency_id)
            res += tax_l
        return res

    @api.model
    def move_line_get_item(self, line):
        if line.product_id:
            acc = line.product_id.property_account_expense
            if not acc:
                acc = line.product_id.categ_id.property_account_expense_categ
            if not acc:
                raise except_orm(_('Error!'), _('No purchase account found for the product %s (or for his category), please configure one.') % (line.product_id.name))
        else:
            acc = self.env['ir.property'].with_context(force_company=line.expense_id.company_id.id).get('property_account_expense_categ', 'product.category')
            if not acc:
                raise except_orm(_('Error!'), _('Please configure Default Expense account for Product purchase: `property_account_expense_categ`.'))
        return {
            'type':'src',
            'name': line.name.split('\n')[0][:64],
            'price_unit':line.unit_amount,
            'quantity':line.unit_quantity,
            'price':line.total_amount,
            'account_id':acc.id,
            'product_id':line.product_id.id,
            'uos_id':line.uom_id.id,
            'account_analytic_id':line.analytic_account.id,
        }

    @api.multi
    def action_view_move(self):
        '''
        This function returns an action that display existing account.move of given expense ids.
        '''
        assert self.ensure_one(), 'This option should only be used for a single id at a time'
        try:
            view_id = self.env.ref('account.view_move_form').id
        except ValueError, e:
            view_id = False
        result = {
            'name': _('Expense Account Move'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': self.account_move_id.id,
        }
        return result


class product_template(models.Model):
    _inherit = "product.template"
    
    can_be_expensed = fields.Boolean(string='Can be Expensed', help="Specify if the product can be selected in an HR expense line.")
    
class hr_expense_expense(models.Model):
    _name = "hr_expense.expense"
    _description = "Expense"
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    @api.multi
    @api.depends('unit_quantity','unit_amount')
    def _amount(self):
        total = 0.0
        for expense in self:
            total += expense.unit_amount * expense.unit_quantity
        self.total_amount = total

    @api.model
    def _get_uom_id(self):
        return self.env.ref('product.product_uom_unit').id

    name = fields.Char(string='Description', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    expense_id = fields.Many2one('hr_expense.sheet', string='Expense', ondelete='cascade')
    total_amount = fields.Float(string='Total', store=True, compute='_amount', digits=dp.get_precision('Account'))
    unit_amount = fields.Float(string='Unit Price', digits=dp.get_precision('Product Price'))
    unit_quantity = fields.Float(string='Quantity', digits= dp.get_precision('Product Unit of Measure'), default=1)
    product_id = fields.Many2one('product.product', string='Product', domain=[('can_be_expensed','=',True)])
    uom_id = fields.Many2one('product.uom', string='Unit of Measure', required=True, default=lambda self: self._get_uom_id())
    analytic_account = fields.Many2one('account.analytic.account', string='Analytic account')
    ref = fields.Char(string='Reference')
    sequence = fields.Integer(string='Sequence')
    employee_id = fields.Many2one('hr.employee', string="Employee", related='expense_id.employee_id', store=True, required=True)
    state = fields.Selection([
        ('draft', 'New'),
        ('confirm', 'Submitted'),
        ('accepted', 'Approved'),
        ('cancel', 'Cancelled'),
        ],
        string='Status', readonly=True, track_visibility='onchange', copy=False, required=True, default='draft')
    expense_tax_id = fields.Many2many('account.tax','expense_line_tax', 'expense_line_id', 'tax_id',string='Taxes')

    _order = "sequence, date"

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.unit_amount = self.product_id.price_get('standard_price')[self.product_id.id]
            self.uom_id = self.product_id.uom_id.id

    @api.onchange('product_id','uom_id')
    def onchange_uom(self):
        res = {'value':{}}
        if self.product_id:
            if self.uom_id.category_id.id != self.product_id.uom_id.category_id.id:
                res['warning'] = {'title': _('Warning'), 'message': _('Selected Unit of Measure does not belong to the same category as the product Unit of Measure')}
                self.uom_id = self.product_id.uom_id.id
            return res

    @api.multi
    def expense_line_new_to_confirm_status(self):
        expense_sheet = self.env['hr_expense.sheet']
        expense_sheet_ids = expense_sheet.search([('state','in', ['draft','confirm'])], limit=1)
        for expense in self:
            if expense.state == 'draft':
                if not expense_sheet_ids :
                    property_account_payable = expense.employee_id.address_home_id.property_account_payable.id
                    expense.write({'expense_id': expense_sheet.create({'employee_payable_account_id': property_account_payable}).id, 'state':'confirm'})
                else :
                    expense.write({'expense_id':expense_sheet_ids.id, 'state':'confirm'})

    @api.multi
    def expense_line_submit_to_approved_status(self):
        return self.write({'state':'accepted'})

    @api.multi
    def expense_line_submit_to_canceled_status(self):
        return self.write({'state':'cancel'})

    @api.multi
    def unlink(self):
        for expense in self:
            if expense.state not in ['draft','cancel']:
                raise Warning(_('You can delete new or cancelled expenses!'))
        return super(hr_expense_expense, self).unlink()

class account_move_line(models.Model):
    _inherit = "account.move.line"

    @api.multi
    def reconcile(self, type='auto', writeoff_acc_id=False, writeoff_period_id=False, writeoff_journal_id=False):
        res = super(account_move_line, self).reconcile(type=type, writeoff_acc_id=writeoff_acc_id, writeoff_period_id=writeoff_period_id, writeoff_journal_id=writeoff_journal_id)
        #when making a full reconciliation of account move lines 'ids', we may need to recompute the state of some hr.expense
        account_move_ids = [aml.move_id.id for aml in self]
        if account_move_ids:
            expenses = self.env['hr_expense.sheet'].search([('account_move_id', 'in', account_move_ids)])
            for expense in expenses:
                if expense.state == 'done':
                    #making the postulate it has to be set paid, then trying to invalidate it
                    new_status_is_paid = True
                    for aml in expense.account_move_id.line_id:
                        if aml.account_id.type == 'payable' and not expense.company_id.currency_id.is_zero(aml.amount_residual):
                            new_status_is_paid = False
                    if new_status_is_paid:
                        expense.write({'state': 'paid'})
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
