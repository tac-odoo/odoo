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

class res_company(osv.osv):
    _inherit = "res.company"
    _columns = {
        'cst_no': fields.char('CST Number', size=32, help='Central Sales Tax Number of Company'),
        'cst_date': fields.date('CST Number Issue Date', help='Central Sales Tax Date of Company'),
        'vat_no' : fields.char('VAT Number', size=32, help="Value Added Tax Number"),
        'vat_date': fields.date('VAT Number Issue Date', help='VAT Number Issue Date'),
        'excise_no': fields.char('Excise Control Code', size=32, help="Excise Control Code"),
        'excise_date': fields.date('Excise Code Issue Date',  help="Excise Code Issue Date"),
        'range': fields.char('Range', size=64),
        'division': fields.char('Division', size=64),
        'postal_address': fields.text('Full Postal Address'),
    }
res_company()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: