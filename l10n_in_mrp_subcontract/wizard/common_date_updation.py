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

class common_date_updation(osv.osv_memory):
    _name = "common.date.updation"
    _description = "Date"

    _columns = {
        'date_to_update':fields.datetime('Date', required=True),
    }

    def to_update(self, cr, uid, ids, context=None):
        """
        - Process
            - common update date wizard
            - update dates from context values.
        """
        context = context or {}
        wizard_rec = self.browse(cr, uid, ids[0])
        pick_obj = self.pool.get('stock.picking.in')
        record_id = context and context.get('active_id', False) or False
        active_model = context and context.get('active_model', False) or False
        fields_name = context and context.get('fields_name', False) or False
        active_obj = self.pool.get(active_model)
        update_dates = fields_name.split(',')

        #[''] not pass
        if not filter(None, update_dates): return True
        update_v = {}
        for fields in update_dates:
            update_v.update({fields: wizard_rec.date_to_update})
        active_obj.write(cr ,uid, record_id, update_v)
        #Update only when GRN made with diffrent recieved date, Its auto update moves received date.
        if active_model == 'stock.picking.in' and record_id:
            pick = pick_obj.browse(cr, uid, record_id, context=context)
            for move in pick.move_lines:
                move.write({fields: wizard_rec.date_to_update})
        return True

common_date_updation()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
