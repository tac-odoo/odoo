# -*- coding: utf-8 -*-

from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from openerp import tools, models, fields, api, _

class sale_order_line(models.Model):
    _inherit = 'sale.order.line'

    membership_start_date = fields.Date(
        'Membership Start Date', default=lambda self: fields.date.today(), help='Date from which membership becomes active.')

    @api.multi
    def _create_membership_line(self):
        for line in self:
            if line.product_id.membership:
                end_date = (datetime.strptime(line.membership_start_date, tools.DEFAULT_SERVER_DATE_FORMAT).date(
                )) + relativedelta(months=line.product_id.membership_duration)
                self.env['membership.membership_line'].create({
                    'partner': line.order_partner_id.id,
                    'membership_id': line.product_id.id,
                    'member_price': line.price_unit,
                    'date_from': line.membership_start_date,
                    'date_to': end_date,
                    'state': 'waiting',
                    'sale_order_line_id': line.id
                })
        return True

    @api.one
    def button_confirm(self):
        res = super(sale_order_line, self).button_confirm()
        self._create_membership_line()
        return res

    @api.multi
    def invoice_line_create(self):
        res = []
        invoice_line_ids = super(sale_order_line, self).invoice_line_create()
        res += invoice_line_ids
        for line_id in self:
            if line_id and invoice_line_ids:
                membership_line_ids = self.env['membership.membership_line'].search([('sale_order_line_id', '=', line_id.id)])
                membership_line_ids.write({
                    'date': fields.date.today(),
                    'account_invoice_line': invoice_line_ids.pop(0),
                })
        return res

class membership_line(models.Model):

    '''Membership line'''
    _inherit = 'membership.membership_line'

    sale_order_line_id = fields.Many2one('sale.order.line', 'Sale Order line', readonly=True)
    sale_order_id = fields.Many2one(string='Sale Order', related ='sale_order_line_id.order_id')

class account_invoice_line(models.Model):
    _inherit = 'account.invoice.line'

    @api.one
    def _prepare_domain_invoice_membership(self, line):
        domain = super(
            account_invoice_line, self)._prepare_domain_invoice_membreship(line)
        return ['|', ('sale_order_line_id', '!=', False)] + domain
