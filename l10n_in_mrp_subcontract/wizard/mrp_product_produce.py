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
from openerp.tools.translate import _

class mrp_product_produce(osv.osv_memory):
    _inherit = "mrp.product.produce"

    def calc_qty(self, cr, uid, production_id, context=None):
        """
        Calculate produce qty = Product Total qty - (Rejection Qty + Scrapped_qty + Extra Consume Moves)
        """
        prod = self.pool.get('mrp.production').browse(cr, uid,production_id
                                , context=context)
        done = 0.0
        for wo in prod.workcenter_lines:
            for mrej in wo.moves_rejection:
                done += mrej.s_rejected_qty or 0.0
        for move in prod.move_created_ids2:
            if move.product_id == prod.product_id:
                #ignore scrapped and extra consumed
                if (not move.scrapped) or (not move.extra_consumed):
                    done += move.product_qty
        if (prod.product_qty - done) <= 0:
            raise osv.except_osv(_('Warning!'), _('Click on "Force To Close" button to generate remain scrap order.'))
        return (prod.product_qty - done) or prod.product_qty

    def _get_product_qty(self, cr, uid, context=None):
        """ 
        -Process
            -call as it is,
            -ignore moves which has MARK as "extra_consumed"
        """
        if context is None:
            context = {}
        return self.calc_qty(cr, uid, context['active_id'], context=context)

    _defaults = {
         'product_qty': _get_product_qty,
         'mode': lambda *x: 'consume_produce'
    }

    def do_produce(self, cr, uid, ids, context=None):
        production_id = context.get('active_id', False)
        assert production_id, "Production Id should be specified in context as a Active ID."
        data = self.browse(cr, uid, ids[0], context=context)
        remain_qty2produce = self.calc_qty(cr, uid, context['active_id'], context=context)
        if data.product_qty > remain_qty2produce:
            raise osv.except_osv(_('Exceed The Limit!'), _('provide qty(%s) cannot be greater then producible qty(%s) '%(remain_qty2produce,data.product_qty)))
        self.pool.get('mrp.production').action_produce(cr, uid, production_id,
                            data.product_qty, data.mode, context=context)
        return {}

mrp_product_produce()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
