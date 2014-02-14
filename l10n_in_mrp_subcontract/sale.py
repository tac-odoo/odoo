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

from openerp.osv import fields, osv
from dateutil.relativedelta import relativedelta
from datetime import datetime
from openerp.tools.translate import _

class sale_order(osv.osv):
    _inherit = "sale.order"

    _columns = {
        'ex_work_date': fields.date('Ex.work Delivery Date', help = "Date should be consider as date of Goods ready for delivery"),
        'shipping_time':  fields.integer('Shipping Time(In Days)'),
        'destination_date': fields.date('Destination  Delivery Date', help="Reaching date of delivery goods(Ex.work Delivery Date + Shipping Time)"),
    }

    def onchange_shipping_time(self, cr, uid, ids, ex_work_date, shipping_time, context=None):
        return {'value':{'destination_date':(datetime.strptime(ex_work_date, '%Y-%m-%d') + relativedelta(days=shipping_time)).strftime('%Y-%m-%d')}}

    _defaults = {
        'ex_work_date': fields.date.context_today,
        'shipping_time': 7,
    }

    def _prepare_order_picking(self, cr, uid, order, context=None):
        """
        Process
            -call super() to get dictionary values,
            -Update values of ex_work_date,shipping_time,destination_date
        """
        res = super(sale_order,self)._prepare_order_picking(cr, uid, order, context=context)
        res.update({
                    'ex_work_date': order.ex_work_date,
                    'shipping_time': order.shipping_time,
                    'destination_date': order.destination_date
                    })
        return res


    def _prepare_order_line_procurement(self, cr, uid, order, line, move_id, date_planned, context=None):
        """
        Process
            -call super() to get dictionary values,
            -Date Planned should be Ex.work Date
        """
        res = super(sale_order,self)._prepare_order_line_procurement(cr, uid, order, line, move_id, date_planned, context=context)
        res.update({
                    'date_planned': order.ex_work_date,
                    })
        return res

    def _check_configuration_ok(self, cr, uid, products):
        product_obj = self.pool.get('product.product')
        orderpoint_obj = self.pool.get('stock.warehouse.orderpoint')
        bom_obj = self.pool.get('mrp.bom')
        warning_msg = ''
        for prdct in product_obj.browse(cr, uid, products):
            if prdct.supply_method == 'buy' and prdct.procure_method == 'make_to_stock':
                if not prdct.seller_id:
                    warning_msg += prdct.name + ':'+'Atleast define one supplier for this product.\n\n'
                if not orderpoint_obj.search(cr,uid, [('product_id','=',prdct.id),('active','=',True)]):
                    warning_msg += prdct.name + ':'+'Atleast define one Minimum Order Rule for this product.\n\n'
            if prdct.supply_method == 'produce':
                if not bom_obj._bom_find(cr, uid, prdct.id, prdct.uom_id.id):
                    warning_msg += prdct.name + ':'+'BoM(Bill Of Materials) not found for this product.\n\n'
        if warning_msg:
            raise osv.except_osv(_('Cannot confirm sales order line!'),_(warning_msg))
        return True

    def action_button_confirm(self, cr, uid, ids, context=None):
        """
        Process
            -To generate warning message, if anything wrong configuration apply on product
        """
        for order in self.browse(cr, uid, ids, context):
            assign_products = []
            for l in order.order_line:
                if l.product_id and l.product_id.type not in ('consu','service'): assign_products.append(l.product_id.id)
            self._check_configuration_ok(cr, uid, list(set(assign_products)))

        return super(sale_order,self).action_button_confirm(cr, uid, ids, context=context)

sale_order()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: