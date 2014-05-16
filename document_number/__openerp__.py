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
    'name': 'Document Numbering',
    'version': '1.0',
    'author': 'OpenERP SA',
    'sequence': 120,
    'category': 'Document Numbering',
    'website': 'http://www.openerp.com',
    'summary': 'Ref number, outgoing ref number',
    'description': """
Document Numbering
==================
A Physical document need to be tracked with the REF number when they are printed on the companies letterpad. using OpenERP document management you can track the document along with the ref number.

i.e.
REF/2014/HR/0010
REF/2014/ACCOUNT/0020

TODO: explain the module in detail
""",
    'depends': ['document'],
    'data': [
        'document_number_view.xml'
    ],

    'demo': [
    ],

    'installable': True,
    'application': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
