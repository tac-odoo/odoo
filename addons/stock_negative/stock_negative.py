# -*- coding: utf-8 -*-

from openerp.osv import fields, osv
from openerp.tools.translate import _


class stock_quant(osv.osv):
    _inherit = "stock.quant"

    def _quant_create(self, cr, uid, qty, move, lot_id=False, owner_id=False, src_package_id=False, dest_package_id=False, force_location_from=False, force_location_to=False, context=None):
        quant = {}
        if move.product_id.qty_available - qty < 0 and move.location_id.usage == 'internal':
            raise osv.except_osv(_('Warning!'), _('You can not create negative stock'))
        else:
            quant = super(stock_quant, self)._quant_create(cr, uid, qty, move, lot_id=lot_id, owner_id=owner_id, src_package_id=src_package_id, dest_package_id=dest_package_id, force_location_from=force_location_from, force_location_to=force_location_to, context=context)
        return quant
