# -*- coding: utf-8 -*-
import random
import hashlib
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from openerp import tools, models, fields, api, _

class sales_coupon_tupe(models.Model):
    _name = 'sales.coupon.type'
    _description = "Sales Coupon Type"

    name = fields.Char(string='Name', required=True)
    validity_duration = fields.Selection(
        [('month', 'Month'),
         ('week', 'Week'),
         ('year', 'Year'),
         ], string='Validity Duration', default='month',
        help="Validity Duration can be based on either month, week or year.")
    expiration_date = fields.Date(string='Expiration Date',
                                  default=fields.date.today(),
                                  help="The coupon will be Expired on Selected Date.")
    expiration_use = fields.Integer(
        string='Expiration Use', default='1', help="Number of Times coupon can be Used.")
    week = fields.Integer(string="Week",
                          help="Duration of Coupon valid till Number of Week")
    month = fields.Integer(string="Month",
                           help="Duration of Coupon valid till Number of Month")
    year = fields.Integer(string="Year",
                          help="Duration of Coupon valid till Number of Year")

    @api.onchange('validity_duration', 'week', 'month', 'year')
    def change_validity_duration(self):
        if self.validity_duration == 'month':
            self.expiration_date = fields.date.today() + \
                relativedelta(months=self.month)
        if self.validity_duration == 'week':
            self.expiration_date = fields.date.today() + \
                relativedelta(days=(self.week * 7))
        if self.validity_duration == 'year':
            self.expiration_date = fields.date.today() + \
                relativedelta(months=(self.year * 12))


class sales_coupon(models.Model):
    _name = 'sales.coupon'
    _description = "Sales Coupon"
    _rec_name = "code"

    @api.onchange('coupon_type')
    def onchange_coupon_id(self):
        self.expiration_date = self.coupon_type.expiration_date
        self.expiration_use = self.coupon_type.expiration_use

    @api.one
    def count_coupon(self):
        self.coupon_used = self.env['sale.order.line'].search_count(
            [('coupon_id', '=', self.id), ('is_coupon', '=', True), ('sales_coupon_type_id', '=', False)])

    code = fields.Char(string='Coupon Code',
                       default=lambda self: 'SC' +
                       (hashlib.sha1(
                           str(random.getrandbits(256)).encode('utf-8')).hexdigest()[:7]).upper(),
                       required=True, readonly=True, help="Coupon Code")
    partner_id = fields.Many2one(
        'res.partner', string='Customer', required=True)
    coupon_type = fields.Many2one('sales.coupon.type', string='Coupon Type')
    expiration_date = fields.Date(
        string='Expiration Date', help="Till this period you can use coupon")
    expiration_use = fields.Integer(
        string='Expiration Use', help="Limit of time you can use coupon")
    product_id = fields.Many2one(
        'product.product', string='Product', required=True)
    state = fields.Selection([
        ('current', 'Current'),
        ('used', 'Used'),
        ('expired', 'Expired'),
    ], string='Status', default='current', readonly=True, select=True)
    order_line_id = fields.Many2one(
        'sale.order.line', string='Order Reference', readonly=True)
    coupon_used = fields.Integer(compute="count_coupon", string="Coupon Used")

    @api.one
    def check_expiration(self):
        if self.state == 'used':
            return {'error': _('Coupon %s reached limit of usage.') % (self.code)}
        if (datetime.strptime(self.expiration_date, tools.DEFAULT_SERVER_DATE_FORMAT).date()) < datetime.now().date():
            self.state = 'expired'
        if self.state == 'expired':
            return {'error': _('Coupon %s  exist but is expired.') % (self.code)}

    @api.one
    def post_apply(self):
        if self.expiration_use <= self.coupon_used:
            self.state = 'used'
