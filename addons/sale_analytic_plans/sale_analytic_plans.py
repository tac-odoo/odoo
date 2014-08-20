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

from lxml import etree
from openerp.osv import fields, osv
from openerp.osv.orm import setup_modifiers

class sale_order_line(osv.osv):
    _inherit = 'sale.order.line'
    _columns = {
        'analytics_id': fields.many2one('account.analytic.plan.instance', 'Analytic Distribution'),
    }
    def invoice_line_create(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        line_obj = self.pool.get('account.invoice.line')
        create_ids = super(sale_order_line, self).invoice_line_create(cr, uid, ids, context=context)
        i = 0
        for line in self.browse(cr, uid, ids, context=context):
            line_obj.write(cr, uid, [create_ids[i]], {'analytics_id': line.analytics_id.id})
            i = i + 1
        return create_ids


class sale_order(osv.Model):
    _inherit = 'sale.order'
    
    def fields_view_get(self, cr, user, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(sale_order, self).fields_view_get(cr, user, view_id, view_type, context, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        nodes = doc.xpath("//field[@class='sale_project']")
        for node in nodes:
            node.set('invisible', '1')
            setup_modifiers(node, res['fields'][node.get('name')])
        res['arch'] = etree.tostring(doc)
        return res


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
