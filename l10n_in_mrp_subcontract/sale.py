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
import openerp.addons.decimal_precision as dp
from openerp import SUPERUSER_ID
from openerp.tools.translate import _

class taxes_by_products(osv.osv):
    _name = 'taxes.by.products'
    _columns = {
        'order_id': fields.many2one('sale.order', 'Order Reference'),
        'product_id': fields.many2one('product.product', 'Product'),
        'name': fields.char('Tax Description', size=64),
        'price_unit': fields.float('Base Amount', digits_compute=dp.get_precision('Account')),
        'amount': fields.float('Tax Amount', digits_compute=dp.get_precision('Account')),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of invoice tax."),
        'base_code_id': fields.many2one('account.tax.code', 'Base Code', help="The account basis of the tax declaration."),
        'base_amount': fields.float('Base Code Amount', digits_compute=dp.get_precision('Account')),
        'tax_code_id': fields.many2one('account.tax.code', 'Tax Code', help="The tax basis of the tax declaration."),
        'tax_amount': fields.float('Tax Code Amount', digits_compute=dp.get_precision('Account')),
    }

taxes_by_products()

class sale_order(osv.osv):
    _inherit = "sale.order"

    def _get_taxes_by_products_detail(self, cr, uid, ids,context=None):
        """ 
        Taxes products wise
        @ Return:
            1) Product 2
                -Tax    Base Amount    Tax Amount
            2) Product 2
                -Tax    Base Amount    Tax Amount
            ----
                --------
        """
        res = {}
        context = context or {}
        if not ids: return res
        tax_obj = self.pool.get('account.tax')
        tax_product_obj = self.pool.get('taxes.by.products')
        for order in self.browse(cr, uid, ids, context=context):
            unlink_ids = [x.id for x in order.taxes_by_products_detail]
            tax_product_obj.unlink(cr, SUPERUSER_ID, unlink_ids, context=context)
        for order in self.browse(cr, uid, ids, context=context):
            for line in order.order_line:
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_uom_qty, line.product_id, line.order_id.partner_id)
                count = 0
                for tax in taxes.get('taxes', []):
                    count += 1
                    if count == 1: tax.update({'product_id':line.product_id and line.product_id.id or False})
                    tax.update({'order_id':order.id})
                    for rmv in ['ref_base_sign','ref_tax_code_id','account_paid_id', 'base_sign', 'include_base_amount', 
                                'account_analytic_paid_id', 'ref_base_code_id','account_collected_id', 'account_analytic_collected_id',
                                 'parent_id, tax_sign', 'ref_tax_sign']:
                        tax.has_key(rmv) and tax.pop(rmv)
                    tax_product_obj.create(cr, uid, tax,context=context)
        return True


    def _amount_line_tax(self, cr, uid, line, context=None):
        val = 0.0
        for c in self.pool.get('account.tax').compute_all(cr, uid, line.tax_id, line.price_unit * (1-(line.discount or 0.0)/100.0), line.product_uom_qty, line.product_id, line.order_id.partner_id)['taxes']:
            val += c.get('amount', 0.0)
        return val

    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        cur_obj = self.pool.get('res.currency')
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
                'extra_charges':0.0,
            }
            val = val1 = other_charges = 0.0
            cur = order.pricelist_id.currency_id
            for line in order.order_line:
                val1 += line.price_subtotal
                val += self._amount_line_tax(cr, uid, line, context=context)

            other_charges = (order.package_and_forwording + order.freight + order.insurance + order.extra_charges)
            res[order.id]['amount_tax'] = cur_obj.round(cr, uid, cur, val)
            res[order.id]['amount_untaxed'] = cur_obj.round(cr, uid, cur, val1)
            res[order.id]['amount_total'] = res[order.id]['amount_untaxed'] + res[order.id]['amount_tax'] + other_charges + order.round_off
        return res

    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('sale.order.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()

    _columns = {
        'ex_work_date': fields.date('Ex.work Delivery Date', help = "Date should be consider as date of Goods ready for delivery"),
        'shipping_time':  fields.integer('Shipping Time(In Days)'),
        'destination_date': fields.date('Destination  Delivery Date', help="Reaching date of delivery goods(Ex.work Delivery Date + Shipping Time)"),
        'taxes_by_products_detail': fields.one2many('taxes.by.products', 'order_id',string='Taxes By Products',readonly=True),

        'package_and_forwording': fields.float('Packaging & Forwarding', states={'confirmed':[('readonly', True)], 'approved':[('readonly', True)], 'done':[('readonly', True)]}),
        'insurance': fields.float('Insurance', states={'confirmed':[('readonly', True)], 'approved':[('readonly', True)], 'done':[('readonly', True)]}),
        'freight': fields.float('Freight', states={'confirmed':[('readonly', True)], 'approved':[('readonly', True)], 'done':[('readonly', True)]}),
        'extra_charges': fields.float('Other Charges', states={'confirmed':[('readonly', True)], 'approved':[('readonly', True)], 'done':[('readonly', True)]}),
        'round_off': fields.float('Round Off', states={'confirmed':[('readonly', True)], 'approved':[('readonly', True)], 'done':[('readonly', True)]}, help="Round Off Amount"),

        'amount_untaxed': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Untaxed Amount',
            store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['package_and_forwording','insurance', 'freight' 'extra_charges','round_off', 'order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            }, multi="sums", help="The amount without tax", track_visibility='always'),
        'amount_tax': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Taxes',
            store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['package_and_forwording','insurance', 'freight' 'extra_charges','round_off', 'order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            }, multi="sums", help="The tax amount"),
        'amount_total': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Total',
            store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['package_and_forwording','insurance', 'freight' 'extra_charges','round_off', 'order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            }, multi="sums",help="The total amount"),
#        'other_charges': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='P&F+Freight+Insurance',
#            store={
#                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['package_and_forwording','insurance', 'freight' 'extra_charges','round_off', 'order_line'], 10),
#                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
#            }, multi="sums", help="Computed as Packing & Forwarding + Freight + Insurance"),

    }

    def onchange_shipping_time(self, cr, uid, ids, ex_work_date, shipping_time, context=None):
        return {'value':{'destination_date':(datetime.strptime(ex_work_date, '%Y-%m-%d') + relativedelta(days=shipping_time)).strftime('%Y-%m-%d')}}


    _defaults = {
        'ex_work_date': fields.date.context_today,
        'shipping_time': 7,
        'note': """
·Price : 
·Incoterm : 
·Payment terms : 
·Insurance : 
·Packing & Forwarding Charges : 
·Freight : 
·Taxes : 
"""
    }

    def write(self, cr, uid, ids, vals, context=None):
        """ To update taxes lines"""
        context = context or {}
        res = super(sale_order,self).write(cr, uid, ids, vals,context=context)
        if isinstance(ids,int):
            ids = [ids]
        if vals and vals.get('order_line'):
            self._get_taxes_by_products_detail(cr, uid, ids, context=context)
        return res

    def create(self, cr, uid, vals, context=None):
        """ To update taxes lines"""
        context = context or {}
        new_id = super(sale_order,self).create(cr, uid, vals,context=context)
        self._get_taxes_by_products_detail(cr, uid, [new_id], context=context)
        return new_id
    
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
                    warning_msg += 'Atleast define one Minimum Order Rule for ('+prdct.name+')product.\n\n'
            if prdct.supply_method == 'produce':
                if not bom_obj._bom_find(cr, uid, prdct.id, prdct.uom_id.id):
                    warning_msg += 'BoM(Bill Of Materials) not found for ('+prdct.name+') product.\n\n'
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

    def _prepare_invoice(self, cr, uid, order, lines, context=None):
        """
        -Process
            add all fields to invoice for reference and report purpose.
        """
        stock_obj = self.pool.get('stock.picking')
        res = super(sale_order, self)._prepare_invoice(cr, uid, order, lines, context=context)
        do_ids = stock_obj.search(cr, uid, [('sale_id','=',order.id)])
        res.update({'comment':''})
        if do_ids:
            do_data = stock_obj.browse(cr, uid, do_ids[0])
            res.update({
                    'do_id': do_ids[0],
                    'do_address_id': order.partner_id.id,
                    'so_date': order.date_order,
                    #'do_carrier_id': picking.carrier_id and picking.carrier_id.id,
                    'do_name': do_data.name,
                    'do_delivery_date': order.ex_work_date,
                    'so_id': order.id,

                    'package_and_forwording':order.package_and_forwording, 
                    'insurance':order.insurance,
                    'freight':order.freight,
                    'extra_charges':order.extra_charges,
                    'round_off':order.round_off,
                })
        return res
sale_order()

class sale_order_line(osv.osv):
    _inherit = "sale.order.line"

    _columns = {
        'symbol': fields.related('order_id', 'currency_id','symbol', type="char",string="in",readonly=True),
    }

sale_order_line()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
