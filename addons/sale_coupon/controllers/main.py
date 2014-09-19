from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp import tools
from datetime import datetime, date
from openerp.addons.web.http import request
from openerp.tools.translate import _

import json

class Website_coupon(http.Controller):
    @http.route(['/shop/sales_coupon'], type='json', auth="public", website=True)
    def sales_coupon(self, promo, **post):
        cr, uid, context = request.cr, request.uid, request.context
        coupon_code_obj = request.registry['coupon.manager']
        sale_order_line_obj = request.registry['sale.order.line']
        coupon_manager_ids = coupon_code_obj.search(cr, uid, [('code', '=', promo)], context=context)
        coupon = coupon_code_obj.browse(cr, uid, coupon_manager_ids, context=context)

        if not coupon:
            return {'error': 'not_coupon'}

        order = request.website.sale_get_order()
        order_line = sale_order_line_obj.search(cr, SUPERUSER_ID, [('order_id', '=', order.id)], context=context)
        for order_line_obj in sale_order_line_obj.browse(cr, SUPERUSER_ID, order_line, context):
            coupon_in = coupon_code_obj.search(cr, uid, [('product_id', '=', order_line_obj.product_id.id)], context=context)
            if not coupon_in:
                return {'error': 'not_coupon'}

            if coupon.validity == 'expiration_date':
                date_expire = (datetime.strptime(coupon.expiration_date,tools.DEFAULT_SERVER_DATE_FORMAT).date())
                if date_expire < datetime.now().date():
                    return {'error': 'coupon_expired'}
                if order_line_obj.product_uom_qty == 1:
                    sale_order_line_obj.write(
                        cr, SUPERUSER_ID, [order_line_obj.id], {
                        'price_unit': 0
                    }, context=context)
                # else:
                #     price = order_line_obj.price_unit - (order_line_obj.price_unit/order_line_obj.product_uom_qty)
                #     print '-----------',price
                #     print sdgf
                #     sale_order_line_obj.write(
                #         cr, SUPERUSER_ID, [order_line_obj.id], {
                #         'price_unit': price
                #     }, context=context)
                return {'update_price': 'update_cart_price'}
            else:
                if coupon.expiration_use <= 0:
                    return {'error': 'coupon_used'}

                if order_line_obj.product_uom_qty == 1:
                    sale_order_line_obj.write(
                        cr, SUPERUSER_ID, [order_line_obj.id], {
                        'price_unit': 0
                    }, context=context)
                # else:
                #     price = order_line_obj.price_unit - (order_line_obj.price_unit/order_line_obj.product_uom_qty)
                #     print '-----------',order_line_obj.price_unit,'------,',order_line_obj.price_unit/order_line_obj.product_uom_qty
                #     print sdgf
                #     sale_order_line_obj.write(
                #         cr, SUPERUSER_ID, [order_line_obj.id], {
                #         'price_unit': price
                #     }, context=context)

                coupon_code_obj.write(
                    cr, SUPERUSER_ID, coupon.id, {
                    'expiration_use': coupon.expiration_use -1,
                    }, context=context)
                return {'update_price': 'update_cart_price'}

