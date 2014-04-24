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

{
    'name': 'Indian Manufacturing Subcontract',
    'version': '1.0',
    'category' : 'Indian Localization',
    'description':'''
		Extend the flow of manufacturing process
    ''',
    'author': 'OpenERP SA',
    'depends': ['base','sale_stock','mrp_jit','mrp_operations','l10n_in_account_tax','hr'],
    'data': ['wizard/change_receiveddate_inward_view.xml','wizard/change_qcapproved_date_view.xml',
             'wizard/common_date_updation_view.xml','wizard/mrp_partially_close_view.xml',
             'wizard/qc2reject_view.xml','wizard/stock_return_picking_view.xml',
             'mrp_view.xml','purchase_view.xml','product_view.xml', 'stock_view.xml','invoice_view.xml',
             'sale_view.xml','account_view.xml','res_company_view.xml',
             'partner_view.xml',
             'wizard/process_qty_to_reject_view.xml','wizard/process_qty_to_finished_view.xml',
             'wizard/all_in_once_qty_to_finished_view.xml','wizard/all_in_once_qty_to_cancelled_view.xml',
             'wizard/reallocate_rejected_move_view.xml','wizard/generate_service_order_view.xml',
             'wizard/qty_to_consume_view.xml','wizard/add_rawmaterial_to_consume_view.xml',
             'wizard/consignment_variation_po_view.xml','wizard/qc2xlocation_view.xml',
             'wizard/split_production_order_qty_view.xml','wizard/mrp_product_produce_view.xml',
             'wizard/costing_analysis_report_view.xml','report/report_view.xml',
             ],
    'demo': [],
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
