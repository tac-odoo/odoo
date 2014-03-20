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
import openerp.addons.decimal_precision as dp
from tools.amount_to_text_en import amount_to_text

class account_invoice_line(osv.osv):
    _inherit = "account.invoice.line"

    def _amount_line(self, cr, uid, ids, prop, unknow_none, unknow_dict):
        """
        -Process
            -added variation amount in line
        """
        res = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        for line in self.browse(cr, uid, ids):
            price = line.price_unit  * (1-(line.discount or 0.0)/100.0)
            taxes = tax_obj.compute_all(cr, uid, line.invoice_line_tax_id, price, line.quantity, product=line.product_id, partner=line.invoice_id.partner_id)
            res[line.id] = taxes['total'] + line.variation_amount
            if line.invoice_id:
                cur = line.invoice_id.currency_id
                res[line.id] = cur_obj.round(cr, uid, cur, res[line.id])
        return res

    _columns = {
        'pur_line_qty': fields.float('Purchase Quantity'),
        'pur_line_uom_id':  fields.many2one('product.uom', 'Purchase UoM'),
        'variation_amount': fields.float('Variation Amount(±)', digits_compute=dp.get_precision('Account')),
        'price_subtotal': fields.function(_amount_line, string='Amount', type="float",
            digits_compute= dp.get_precision('Account'), store=True),
    }

account_invoice_line()

class account_invoice(osv.osv):
    _inherit = 'account.invoice'

    _columns = {
            'do_id': fields.many2one('stock.picking', 'Delivery Order', readonly=True),
            'do_address_id': fields.many2one('res.partner', 'Delivery Address'),
            'so_date': fields.date('Sales Date'),
            #'do_carrier_id': fields.many2one('delivery.carrier', 'Carrier'),
            'do_name': fields.char('Delivery Name'),
            'do_delivery_date': fields.datetime('Delivery Date'),
            'so_id': fields.many2one('sale.order', 'Sale Order ID', readonly=True),
            'do_dispatch_doc_no': fields.char('Dispatch Document No.', size=16),
            'do_dispatch_doc_date': fields.date('Dispatch Document Date'),
            }

    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        default.update({
            'do_id':False,
            'do_address_id': False,
            #'do_carrier_id': False,
            'so_date': False,
            'do_name': False,
            'do_delivery_date': False,
            'so_id': False,
            'do_dispatch_doc_no': False,
            'do_dispatch_doc_date': False,
        })
        return super(account_invoice, self).copy(cr, uid, id, default, context)

    def _get_qty_total(self, cr, uid, ids):
        res = {}
        qty = 0.0
        for invoice in self.browse(cr, uid, ids):
            for line in invoice.invoice_line:
                qty += line.quantity
            res[invoice.id] = qty
        return res

    def amount_to_text(self, amount):
        amount_in_word = amount_to_text(amount)
        amount_in_word = amount_in_word.replace("euro", "Rupees").replace("Cents", "Paise").replace("Cent", "Paise")
        return amount_in_word

account_invoice()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: