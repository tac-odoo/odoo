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

import calendar
from datetime import date
from dateutil import relativedelta

from openerp import tools
from openerp.osv import osv, fields

class sale_order(osv.osv):
    _inherit = 'sale.order'
    _columns = {
        'categ_ids': fields.many2many('crm.case.categ', 'sale_order_category_rel', 'order_id', 'category_id', 'Tags', \
            domain="['|', ('section_id', '=', section_id), ('section_id', '=', False), ('object_id.model', '=', 'crm.lead')]", context="{'object_name': 'crm.lead'}"),
        
    }
    

class crm_case_section(osv.osv):
    _inherit = 'crm.case.section'
    
    def _get_amount_forecast(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for sale_team in self.browse(cr, uid, ids, context):
            res[sale_team.id] = sale_team.invoiced_target < sale_team.invoiced_forecast
        return res

    def _forecast_search(self, cr, uid, obj, name, args, context=None):
        if len(args) == 0: return []
        if args[0][2] == True:
            where = "invoiced_target < invoiced_forecast"
        else:
            where = "invoiced_target >= invoiced_forecast"
        cr.execute('select id from crm_case_section where ' + where)
        ids = [id[0] for id in cr.fetchall()]
        return [('id','in', ids)]

    _columns = {
        'invoiced_forecast': fields.integer(string='Invoice Forecast',
            help="Forecast of the invoice revenue for the current month. This is the amount the sales \n"
                    "team should invoice this month. It is used to compute the progression ratio \n"
                    " of the current and forecast revenue on the kanban view."),
        'invoiced_target': fields.integer(string='Invoice Target',
            help="Target of invoice revenue for the current month. This is the amount the sales \n"
                    "team estimates to be able to invoice this month."),
        'is_under_performing': fields.function(_get_amount_forecast, type='boolean', string="Under-performing", fnct_search=_forecast_search)
    }

