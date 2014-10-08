# -*- coding: utf-8 -*-
from openerp import models, fields, api, _

class sales_coupon_config_settings(models.TransientModel):
    _inherit = 'sale.config.settings'

    module_website_sale_coupon = fields.Boolean(string='Allow presale voucher',
        help='- Allocates a coupon code to Customer which can be applied on successive purchase(s) of a perticular Product.\n'
        '- This will install the module website_sal_coupon in the database.')
