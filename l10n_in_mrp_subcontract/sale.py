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
from dateutil.relativedelta import relativedelta
from datetime import datetime

class sale_order(osv.osv):
    _inherit = "sale.order"

    _columns = {
        'ex_work_date': fields.date('Ex.work Delivery Date', help = "Date should be consider as date of Goods ready for delivery"),
        'shipping_time':  fields.integer('Shipping Time(In Days)'),
        'destination_date': fields.date('Destination  Delivery Date', help="Reaching date of delivery goods(Ex.work Delivery Date + Shipping Time)"),
    }

    def onchange_shipping_time(self, cr, uid, ids, ex_work_date, shipping_time, context=None):
        return {'value':{'destination_date':(datetime.strptime(ex_work_date, '%Y-%m-%d') + relativedelta(days=shipping_time)).strftime('%Y-%m-%d')}}

    _defaults = {
        'ex_work_date': fields.date.context_today,
        'shipping_time': 7,
    }

    def _prepare_order_picking(self, cr, uid, order, context=None):
        res = super(sale_order,self)._prepare_order_picking(cr, uid, order, context=context)
        res.update({
                    'ex_work_date': order.ex_work_date,
                    'shipping_time': order.shipping_time,
                    'destination_date': order.destination_date
                    })
        return res

sale_order()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: