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

class change_receiveddate_inward(osv.osv_memory):
    _name = "change.receiveddate.inward"
    _description = "Change Receive Date In Inward"

    _columns = {
        'received_date':fields.datetime('Received  Date', required=True),
    }


    def to_update(self, cr, uid, ids, context=None):
        """
        - Process
            - update variation on lines, just for only information purpose
        """
        context = context or {}
        move_obj = self.pool.get('stock.move')

        wizard_rec = self.browse(cr, uid, ids[0])
        move_id = context and context.get('active_id', False) or False
        move_obj.write(cr ,uid, move_id, {'received_date': wizard_rec.received_date})
        return True

change_receiveddate_inward()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
