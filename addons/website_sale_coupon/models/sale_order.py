# -*- coding: utf-8 -*-
from openerp import tools, models, fields, api, _

class sale_order(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def check_coupon(self):
        self.has_coupon = any([(not l.is_coupon and l.coupon_id) for order in self for l in order.order_line])

    has_coupon = fields.Boolean(compute="check_coupon")


class sale_order_line(models.Model):
    _inherit = 'sale.order.line'

    sales_coupon_type_id = fields.Many2one('sales.coupon.type', string='Coupon Type')
    coupon_id = fields.Many2one(
        'sales.coupon', string='Sales Coupon', readonly=True)
    is_coupon = fields.Boolean()

    def _prepare_coupon_so_line(self, coupon):
        return {
            'order_id': self.order_id.id,
            'name': _('Coupon : %s , Product: %s') % (coupon.code, self.product_id.name),
            'price_unit': - self.price_unit,
            'coupon_id': coupon.id,
            'is_coupon': True,
        }

    @api.multi
    def apply_coupon(self, promocode):
        sales_coupon_obj = self.env['sales.coupon']
        for line in self:
            for coupon in sales_coupon_obj.search([('code', '=', promocode), ('product_id', '=', line.product_id.id)]):
                if line.coupon_id:
                    return {'error': _('Coupon %s already applied.') % (promocode)}
                check_expiration = coupon.check_expiration()[0]
                if check_expiration:
                    return check_expiration
                line.write({'coupon_id': coupon.id, 'is_coupon': True})
                line.create(line._prepare_coupon_so_line(coupon))
                coupon.post_apply()
                return {'update_price': 'update_cart_price'}

    @api.multi
    def product_id_change(self, pricelist, product, qty=0,
                          uom=False, qty_uos=0, uos=False, name='', partner_id=False,
                          lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False):
        res = super(sale_order_line, self).product_id_change(pricelist, product)
        products = self.env['product.product'].browse(product)
        if products.product_tmpl_id.coupon_type:
            res['value'].update(
             {'sales_coupon_type_id': products.product_tmpl_id.coupon_type.id})
        return res

    def _prepare_coupon(self):
        return{
            'partner_id': self.order_id.partner_id.id,
            'coupon_type': self.sales_coupon_type_id.id,
            'product_id': self.product_id.id,
            'expiration_date': self.sales_coupon_type_id.expiration_date,
            'expiration_use': self.sales_coupon_type_id.expiration_use,
            'order_line_id': self.id,
        }

    @api.multi
    def _generate_coupon(self):
        sales_coupon_obj = self.env['sales.coupon']
        for line in self:
            if line.sales_coupon_type_id.id and not line.coupon_id:
                sales_coupon_obj.create(line._prepare_coupon())
                coupon_code = sales_coupon_obj.search(
                    [('order_line_id', '=', line.id)])
                line.write({'coupon_id': coupon_code.id})
        return True

    @api.multi
    def unlink(self):
        line = self.coupon_id and self.search([('order_id', '=', self.order_id.id), ('coupon_id', '=', self.coupon_id.id), ('id', 'not in', self.ids)])
        if line:
            super(sale_order_line, line).unlink()
        return super(sale_order_line, self).unlink()

    @api.multi
    def button_confirm(self):
        res = super(sale_order_line, self).button_confirm()
        self._generate_coupon()
        return res
