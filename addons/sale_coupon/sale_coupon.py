from openerp import models, fields, api, _
from datetime import datetime
import random
import hashlib

class sales_coupon(models.Model):
    _name = 'sales.coupon'
    # _rec_name= 'name'

    name = fields.Char(string='Name', required=True, help="Coupon Name")
    validity_use = fields.Selection(
        [('expiration_date', 'Expiration Date'),
         ('expiration_use', 'Expiration Use'),
        ],'Validity Use', default='expiration_date',
        required=True)
    expiration_date = fields.Date(string='Expiration Date',
                    default=lambda self: fields.datetime.now(),
                    required=True, help="give a period")
    expiration_use = fields.Float(string='Expiration Use', required=True, help="give a limit in term of use")
    # 'product_id': fields.many2many('product.product', 'sale_product_coupon_rel', 'sale_coupon_id', 'product_id', 'Product'),
    # 'product_categ_id': fields.many2many('product.category', 'sale_product_category_coupon_rel', 'sale_coupon_id', 'product_categ_id', 'Product Category'),

class coupon_manager(models.Model):
    _name = 'coupon.manager'

    code = fields.Char('Coupon Code',
        default=lambda self: 'SC' + (hashlib.sha1( str(random.getrandbits(256)).encode('utf-8')).hexdigest()[:7]).upper(),
        required=True, readonly=True, help="Coupon Code")

    partner_id = fields.Many2one('res.partner', 'Customer', required=True)
    coupon_type = fields.Many2one('sales.coupon', 'Coupon Type')
    validity = fields.Selection(
        [('expiration_date', 'Expiration Date'),
         ('expiration_use', 'Expiration Use'),
        ],'Validity', default='expiration_date',
        required=True)
    expiration_date = fields.Date(string='Expiration Date', help="give a period")
    expiration_use = fields.Float(string='Expiration Use', help="give a limit in term of use")
    product_id = fields.Many2one('product.product', 'Product', required=True)
    state = fields.Selection([
        ('current', 'Current'),
        ('used', 'Used'),
        ('expired', 'Expired'),
        ], 'Status', default='current', readonly=True, select=True)
    order_id = fields.Many2one('sale.order', 'Order Reference', readonly=True)


class sale_order_line(models.Model):
    _inherit = 'sale.order.line'

    sales_coupon_type = fields.Many2one('sales.coupon', 'Coupon Type')
    sale_coupon_manager_id = fields.Many2one('coupon.manager', 'Coupon manager', readonly=True)


    # def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
    #         uom=False, qty_uos=0, uos=False, name='', partner_id=False,
    #         lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):
    #     res = super(sale_order_line, self).product_id_change(cr, uid, ids, pricelist, product, context=context)
    #     sales_coupon_ids = self.pool.get('sales.coupon').search(cr, uid, [('product_id', '=' ,product)])
    #     # res['domain'].update({'sales_coupon_type':[('id', 'in', sales_coupon_ids)]})
    #     return res

    @api.multi
    def _create_coupon(self):
        coupon_manager_obj = self.env['coupon.manager']
        sale_coupon_obj = self.env['sales.coupon']
        for line in self:
            # sales_coupon_ids = [sales_coupon.id for sales_coupon in line.sales_coupon_type]
            for sales_coupon in line.sales_coupon_type:
                if sales_coupon:
                    coupon_manager_obj.create({
                        'partner_id': line.order_id.partner_id.id,
                        'coupon_type': line.sales_coupon_type.id,
                        'product_id': line.product_id.id,
                        'validity': sales_coupon.validity_use,
                        'expiration_date': sales_coupon.expiration_date,
                        'expiration_use': sales_coupon.expiration_use,
                        'order_id': line.order_id.id,
                    })
            coupon_code = coupon_manager_obj.search([('order_id', '=' ,line.order_id.id)])
            self.write({
                    'sale_coupon_manager_id': coupon_code.id,
                })
        return True

    @api.one
    def button_confirm(self):
        res = super(sale_order_line, self).button_confirm()
        self._create_coupon()
        return res

class product_template(models.Model):
    _inherit = 'product.template'

    coupon_type = fields.Many2one('sales.coupon', 'Coupon Type')
