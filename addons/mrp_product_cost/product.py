# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014-today OpenERP SA (<http://www.openerp.com>).
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


class product_product(osv.Model):
    _inherit = "product.product"

    _columns = {
        "manufacturing_cost": fields.boolean('Compute Price Based on Manufacturing Cost', help="Select it if you want update cost price periodically regarding the production cost.")
    }

    def process_workcenter_cost(self, cr, uid, workcenter, context=None):
        """
        calculate cost of routing defined on BoM
        :param wrk: dictionary containing Work Center details
        :type wrk: dictionary,
        :return: cost of routing/workcenter
        """
        workcenter_rec = self.pool.get('mrp.workcenter').browse(cr, uid, workcenter['workcenter_id'], context=context)
        cost_cycle = workcenter['cycle'] * workcenter_rec.costs_cycle
        cost_hour = workcenter['hour'] * workcenter_rec.costs_hour
        return cost_cycle + cost_hour

    def button_compute_cost_price(self, cr, uid, ids, context=None):
        """
        Calculate the cost of the selected product, action to execute.
        Multi level boms
        :param ids: identifiers of the product to calculate cost price
        :return: True
        """
        if context is None:
            context = {}
        ids = self.search(cr, uid, [('manufacturing_cost', '=', True), ('id', 'in', ids)], context=context)
        #  let's build the flat list of bom_ids dependancy
        bom_to_update = []
        bom_obj = self.pool.get('mrp.bom')
        for product in self.browse(cr, uid, ids, context=context):
            bom_ids = [bom_id for bom_id in [bom_obj._bom_find(cr, uid, product.id, product.uom_id.id)] if bom_id]
            while bom_ids:
                find_bom_ids = []
                for bom_id in bom_ids:
                    if bom_id in bom_to_update:
                        bom_to_update.remove(bom_id)
                    bom_to_update.append(bom_id)
                    bom = bom_obj.browse(cr, uid, bom_id, context=context)
                    if bom.bom_lines:
                        bom_products = bom_obj._bom_explode(cr, uid, bom, bom.product_qty)
                        product_ids = [prod['product_id'] for prod in bom_products[0] if prod]
                        find_bom_ids += [bom_obj._bom_find(cr, uid, product.id, product.uom_id.id)
                                     for product in self.browse(cr, uid, product_ids, context=context)
                                     if product and product.manufacturing_cost]
                bom_ids = [bom_id for bom_id in find_bom_ids if bom_id]  # remove False

        if not bom_to_update:
            return True
        # process computation backward as leaf boms should be heading
        bom_to_update.reverse()
        uom_obj = self.pool.get('product.uom')
        for bom in bom_obj.browse(cr, uid, bom_to_update, context=context):
            if not bom.bom_lines and bom.type == 'phantom':
                cost = 0.0
            elif not bom.bom_lines and not bom.type == 'phantom':
                product_rec = self.browse(cr, uid, bom.product_id.id, context=context)
                cost = product_rec.standard_price
            else:
                product = bom.product_id
                factor = bom.product_uom.factor / product.uom_id.factor
                # sub bom price
                cost = 0.0
                sub_boms = bom_obj._bom_explode(cr, uid, bom, 1/bom.product_qty)
                for sub_bom in (sub_boms and sub_boms[0]):
                    sub_prod = self.browse(cr, uid, sub_bom['product_id'], context=context)
                    sub_prod_qty = sub_bom['product_qty'] / factor
                    sub_price = uom_obj._compute_price(cr, uid, sub_prod.uom_id.id, sub_prod.standard_price, to_uom_id=sub_bom['product_uom'])
                    cost += sub_prod_qty * sub_price
                #To calculate cost of routing defined on BoM
                for workcenter in (sub_boms and sub_boms[1]):
                    cost += self.process_workcenter_cost(cr, uid, workcenter, context=context)
            self.write(cr, uid, bom.product_id.id, {'standard_price': cost}, context=context)
        return True
