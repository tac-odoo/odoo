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

class mrp_product_produce(osv.osv_memory):
    _inherit = "mrp.product.produce"

    def _get_product_qty(self, cr, uid, context=None):
        """ 
        -Process
            -call as it is,
            -ignore moves which has MARK as "extra_consumed"
        """
        if context is None:
            context = {}
        prod = self.pool.get('mrp.production').browse(cr, uid,
                                context['active_id'], context=context)
        done = 0.0
        for move in prod.move_created_ids2:
            if move.product_id == prod.product_id:
                #ignore scrapped and extra consumed
                if (not move.scrapped) or (not move.extra_consumed):
                    done += move.product_qty
        return (prod.product_qty - done) or prod.product_qty

mrp_product_produce()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
