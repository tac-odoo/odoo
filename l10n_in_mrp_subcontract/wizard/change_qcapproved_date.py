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

class change_qcapproved_date(osv.osv_memory):
    _name = "change.qcapproved.date"
    _description = "Change QC Approved Date"

    _columns = {
        'qc_approved_date':fields.datetime('QC Approved Date', required=True),
    }

    def to_update(self, cr, uid, ids, context=None):
        """
        - Process
            - Update QC Approved Date
        """
        context = context or {}
        move_obj = self.pool.get('stock.move')

        wizard_rec = self.browse(cr, uid, ids[0])
        move_id = context and context.get('active_id', False) or False
        move_obj.write(cr ,uid, move_id, {'qc_approved_date': wizard_rec.qc_approved_date})
        return True

change_qcapproved_date()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
