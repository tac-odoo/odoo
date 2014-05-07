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

from openerp.osv import osv, fields
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

class export_line(osv.osv):
    _name = 'export.line'

    _columns = {
        'export_id': fields.many2one('export.report', 'Export'),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        #'product_desc': fields.text('Description', required=True),
        'part_no_rev': fields.char('Part No. Revision'),
        'qty': fields.float('Quantity'),
        'net_wt': fields.float('Net Wt.'),
        'gross_wt': fields.float('Gross Wt.'),
#        'uom': fields.many2one('product.uom', 'UoM',required=True),
#        'n_uom': fields.many2one('product.uom', 'Net Wt. UoM',required=True),
#        'g_uom': fields.many2one('product.uom', 'Gross Wt. UoM',required=True),
    }

export_line()

class export_report(osv.osv):
    _name = 'export.report'

    def _default_uom(self, cr, uid, context=None):
        if context is None:context = {}
        res = self.pool.get('product.uom').search(cr, uid, [('name', 'ilike', 'Nos')])
        return res and res[0] or False

    def _ng_default_uom(self, cr, uid, context=None):
        if context is None:context = {}
        res = self.pool.get('product.uom').search(cr, uid, [('name', 'ilike', 'kg')])
        return res and res[0] or False

    def _total(self, cr, uid, ids, name, args, context=None):
        """
        Process
            -total of all lines(net wt and gross wt)
        """
        result = dict([(id, {'net_wt_total': 0.0,'gross_wt_total':0.0,'total_qty':0.0,'count':0}) for id in ids])
        net_wt_total,gross_wt_total,total_qty,count = 0.0,0.0,0.0,0
        for ex in self.browse(cr, uid, ids, context=context):
            for l in ex.line_ids:
                count += 1
                net_wt_total += l.net_wt
                gross_wt_total += l.gross_wt
                total_qty  += l.qty
            result[ex.id]['net_wt_total'] = net_wt_total
            result[ex.id]['gross_wt_total'] = gross_wt_total
            result[ex.id]['total_qty'] = total_qty
            result[ex.id]['count'] = count
        return result

    _columns = {
        'name': fields.char('Name', readonly=True),
        'date': fields.datetime('Creation Date', required=True),
        'exporter_id': fields.many2one('res.partner', 'Exporter', required=True),
        'buyer_id': fields.many2one('res.partner', 'Buyer(if other than consignee)', required=True, domain=[('customer', '=', True)]),
        'consignee_id': fields.many2one('res.partner', 'Consignee', required=True, domain=[('customer', '=', True)]),
        'origin_country': fields.char('Country of Origin of Goods', required=True),
        'dest_country': fields.char('Country of Final Destination', required=True),
        'pre_carriage_by': fields.char('Pre-Carriage by'),
        'place_pre_carrier': fields.char('Place of Receipt Pre-Carrier'),
        'v_f_no': fields.char('Vessal/Flight No.'),
        'landing_port': fields.char('Port of Loading'),
        'discharge_port': fields.char('Port of Discharge'),
        'final_dest': fields.char('Final Destination'),
        'no_of_packages': fields.char('No. & kind of Pkgs.'),
        'container_no': fields.char('Marks & Nos./Container No.'),
        'depends_on': fields.selection([('delivey_order', 'Delivery Order'), ('manually', 'Manually')], 'Depends', required=True),
        'delivery_ids': fields.many2many('stock.picking.out', 'delivery_export_id', 'delivery_id', 'export_id', 'Delivery Orders', domain=[('type', '=', 'out')]),
        'line_ids': fields.one2many('export.line', 'export_id', 'Lines'),
        'inv_no': fields.char('Invoice Number', required=True),
        'inv_date': fields.date('Invoice Date'),
        'buyer_ref': fields.char("Buyer's Ref No.", required=True),
        'buyer_date': fields.date("Buyer's Date."),
        'other_ref': fields.char("Other Reference(s)."),
        'notes': fields.text('Description'),
        'total_qty': fields.function(_total, multi='c', type='float', string='Total Qty',digits_compute=dp.get_precision('Product Unit of Measure')),
        'net_wt_total': fields.function(_total, multi='c', type='float', string='Net Wt. Total',digits_compute=dp.get_precision('Product Unit of Measure')),
        'gross_wt_total': fields.function(_total, multi='c', type='float', string='Gross Wt. Total',digits_compute=dp.get_precision('Product Unit of Measure')),
        'count': fields.function(_total, multi='c', type='integer', string='count',digits_compute=dp.get_precision('Product Unit of Measure')),
        'uom': fields.many2one('product.uom', 'UoM', required=True),
        'n_uom': fields.many2one('product.uom', 'Net Wt. UoM', required=True),
        'g_uom': fields.many2one('product.uom', 'Gross Wt. UoM', required=True),

    }
    _defaults = {
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'export.report'),
        'date': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
        'uom':_default_uom,
        'n_uom':_ng_default_uom,
        'g_uom':_ng_default_uom,
        'depends_on':'manually'
    }

    def load_items(self, cr, uid, ids , context=None):
        """
        -Process
            -Add delivery lines from delivery order
        """
        exp_obj = self.pool.get('export.line')
        data = self.browse(cr, uid, ids[0])
        added_line = []
        if data.delivery_ids:
            for do in data.delivery_ids:
                for mv in do.move_lines:
                    desc = self.pool.get('product.product').name_get(cr, uid, [mv.product_id.id], context=context)[0][1]
                    added_line.append({
                                       'product_id':mv.product_id.id,
                                       'product_desc':desc,
                                       'qty':mv.product_qty or 0.0,
                                       'export_id':ids[0],
                                       })
        cr.execute(""" DELETE FROM export_line WHERE export_id = %s""" % (ids[0]))
        if added_line:
            for c in added_line:
                exp_obj.create(cr, uid, c)
        return True

    def action_print(self,cr, uid, ids, context=None):
        """
        Process
            - Action to print export report
                Before printing , required to check all data fullfill that reports.
        """
        context = context or {}
        if not ids:
            raise osv.except_osv(
                _('Error!'),_('You cannot print report this report because some miss-match values.'))

        data = self.read(cr, uid, ids[0], [], context=context)
        if not data['line_ids']:
            raise osv.except_osv(_('Warning!'),_('No Delivery lines found'))
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'export.do.order',
            'datas': {
                     'ids': [ids[0]],
                     'model': 'export.report',
                     'form': data
                     },
        }

export_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
