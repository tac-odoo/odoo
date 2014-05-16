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

from osv import osv
from osv import fields


class document_out_category(osv.osv):
    _name = 'document.out.category'
    _columns = {
        'name': fields.char('Category'),
        'sequence_id': fields.many2one('ir.sequence', 'Sequence')
    }

    def create(self, cr, uid, vals, context=None):
        id = super(document_out_category, self).create(cr, uid, vals, context)

        if id:
            # TODO: create a sequence automatically and link with the category
            pass

document_out_category()


class document_out(osv.osv):
    _name = 'document.out'

    _columns = {
        'name': fields.char('Ref. Number'),
        'partner_id':fields.many2one('res.partner', 'Issued To'),
        'description': fields.text('Purpose'),
        'category_id': fields.many2one('document.out.category', 'Category'),
        'date_issue': fields.datetime('Issued On'),
        'date_prepare': fields.datetime('Prepared On'),
        'state': fields.selection([('draft', 'Draft'), ('progress','In Process'), ('issued','Issued')], string='State')
    }

    _defaults = {
        'state':'draft'
    }
document_out()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
