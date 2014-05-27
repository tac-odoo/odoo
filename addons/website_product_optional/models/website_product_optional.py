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


class ProductOptional(osv.Model):
    _name = "product.optional"
    _description = "Product Optional"

    _columns = {
        'name': fields.text('Description', translate=True),
        'product_id': fields.many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], required=True),
        'price_unit': fields.float('Unit Price', required=True, digits_compute=dp.get_precision('Product Price')),
        'quantity': fields.float('Quantity', required=True, digits_compute=dp.get_precision('Product UoS')),
        'category_id': fields.many2one('product.category.optional', 'Category'),
    }

    _defaults = {
        'quantity': 1,
    }

    def on_change_product_id(self, cr, uid, ids, product, context=None):
        vals = {}
        product_obj = self.pool.get('product.product').browse(cr, uid, product, context=context)
        vals.update({
            'price_unit': product_obj.lst_price,
            'name': product_obj.name,
        })
        return {'value': vals}


class ProductCategoryOptional(osv.Model):
    _name = "product.category.optional"
    _description = "Product Category Optional"

    _columns = {
        'name': fields.char('Name', required=True, translate=True),
        'code': fields.char('Code', required=True, translate=True),
    }


class ProductTemplate(osv.Model):
    _inherit = "product.template"

    _columns = {
        'optional_product_ids': fields.many2many('product.optional', string='Optional Products'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
