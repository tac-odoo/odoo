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

class account_analytic_line(osv.osv):
    _inherit = 'account.analytic.line'
    _columns = {
        'production_id':  fields.many2one('mrp.production','Production Order'),
        'planned_cost' : fields.float('Planned Cost'),
    }

account_analytic_line()

class account_tax(osv.osv):
    _inherit = 'account.tax'

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        res = []
        for record in self.read(cr, uid, ids, ['description','name'], context=context):
            name =  record['name'] or record['description']
            res.append((record['id'],name ))
        return res

account_tax()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: