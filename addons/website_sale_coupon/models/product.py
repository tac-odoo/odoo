# -*- coding: utf-8 -*-
from openerp import models, fields, api, _

class product_template(models.Model):
    _inherit = 'product.template'

    coupon_type = fields.Many2one('sales.coupon.type', string="Coupon Type")
