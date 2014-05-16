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

import time

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc
import openerp.addons.decimal_precision as dp

class purchae_order(osv.Model):
    _inherit = 'purchase.order'
    def wkf_send_rfq(self, cr, uid, ids, context=None):
            '''
            This function opens a window to compose an email, with the edi purchase template message loaded by default
            '''
            ir_model_data = self.pool.get('ir.model.data')
            try:
                po = self.browse(cr,uid,ids[0])
                if po.state == 'draft':
                    template_id = ir_model_data.get_object_reference(cr, uid, 'sparetech_report', 'email_template_edi_sparetech_quotation')[1]
                else:
                    template_id = ir_model_data.get_object_reference(cr, uid, 'purchase', 'email_template_edi_purchase')[1]
            except ValueError:
                template_id = False
            try:
                compose_form_id = ir_model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
            except ValueError:
                compose_form_id = False 
            ctx = dict(context)
            ctx.update({
                'default_model': 'purchase.order',
                'default_res_id': ids[0],
                'default_use_template': bool(template_id),
                'default_template_id': template_id,
                'default_composition_mode': 'comment',
            })
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(compose_form_id, 'form')],
                'view_id': compose_form_id,
                'target': 'new',
                'context': ctx,
            }

class product_product(osv.Model):
    _inherit = 'product.product'

    _columns = {
        'currency_price': fields.float('Price', required=True),
        'currency_id': fields.many2one('res.currency', 'Currency'),
    }
    def update_currency_price(self, cr, uid, ids, context):
        result = {}
        currency_pool = self.pool.get('res.currency')
        prd = self.browse(cr, uid, ids)[0]
        new_price = prd.currency_price
        if prd.currency_id:
            new_price = currency_pool.compute(cr, uid, prd.currency_id.id, prd.company_id.currency_id.id, prd.currency_price)
            
        self.write(cr, uid, [prd.id], {'standard_price':new_price})
        return True

product_product()


class sale_order(osv.Model):
    _inherit = 'sale.order'
    
    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        cur_obj = self.pool.get('res.currency')
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
            }
            val = val1 = 0.0
            cur = order.pricelist_id.currency_id
            for line in order.order_line:
                val1 += line.price_subtotal
                val += self._amount_line_tax(cr, uid, line, context=context)
            res[order.id]['amount_tax'] = cur_obj.round(cr, uid, cur, val)
            res[order.id]['amount_untaxed'] = cur_obj.round(cr, uid, cur, val1)
            res[order.id]['amount_total'] = res[order.id]['amount_untaxed'] + res[order.id]['amount_tax']
        return res

    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('sale.order.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()

    _columns = {
        'amount_untaxed': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Untaxed Amount',
            store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount','markup', 'product_uom_qty'], 10),
            },
            multi='sums', help="The amount without tax.", track_visibility='always'),
        'amount_tax': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Taxes',
            store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount','markup', 'product_uom_qty'], 10),
            },
            multi='sums', help="The tax amount."),
        'amount_total': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total',
            store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount','markup', 'product_uom_qty'], 10),
            },
            multi='sums', help="The total amount."),
        }

    def _amount_line_tax(self, cr, uid, line, context=None):
        val = 0.0
        price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)*(1 + (line.markup or 0.0) / 100.0)
        for c in self.pool.get('account.tax').compute_all(cr, uid, line.tax_id, price, line.product_uom_qty, line.product_id, line.order_id.partner_id)['taxes']:
            val += c.get('amount', 0.0)
        return val

sale_order()

class sale_order_line(osv.Model):
    _inherit = 'sale.order.line'

    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        res = {}
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            price = round(line.price_unit * (1 - (line.discount or 0.0) / 100.0)*(1 + (line.markup or 0.0) / 100.0),2)
            print ">>>>>>>>>>>>>>>>>>>>>>>>>", price
            taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_uom_qty, line.product_id, line.order_id.partner_id)
            cur = line.order_id.pricelist_id.currency_id
            res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
        return res
    
    def _net_price(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = round(line.price_unit * (1 - (line.discount or 0.0) / 100.0)*(1 + (line.markup or 0.0) / 100.0),2)
        print "ASSSSSSSSSSSSSSSSSSSSSSSS", res
        return res

    _columns = {
        'markup': fields.float('Markup (%)'),
        'price_subtotal': fields.function(_amount_line, string='Subtotal', digits_compute= dp.get_precision('Account')),
        'unit_net_price': fields.function(_net_price, string='Net Unit Price', digits_compute= dp.get_precision('Account')),
    }
    _defaults = {
        'discount': 0.0,
    }

sale_order()

class res_users(osv.Model):
    _inherit = 'res.users'
    
    _columns = {
        'outgoing_mail_server_id': fields.many2one('ir.mail_server', 'Outgoing Mail Servers', help='configure for send Out Going Mail Server for current users.', required= True)
    }
res_users()

class mail_mail(osv.Model):
    _inherit = 'mail.mail'
    
    def create(self, cr, uid, values, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if 'notification' not in values and values.get('mail_message_id'):
            values['notification'] = True
            values['mail_server_id'] = user.outgoing_mail_server_id.id
        return super(mail_mail, self).create(cr, uid, values, context=context)
mail_mail()
