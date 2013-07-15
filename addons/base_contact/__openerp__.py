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
    'name': 'Contacts Management',
    'version': '1.0',
    'category': 'Customer Relationship Management',
    'complexity': "expert",
    'description': """
This module allows you to manage your contacts
==============================================

It lets you define groups of contacts sharing some common information, like:
    * Last Name / First Name
    * Birthdate
    * Nationality
    * Native Language

It also adds new menu items located in
    Messaging / Organizer / Contact Groups
    Sales / Customer / Contacts

    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['base', 'process', 'contacts'],
    'init_xml': [],
    'update_xml': [
        #'security/ir.model.access.csv',
        'base_contact_view.xml',
    ],
    'demo_xml': [
    ],
    'test': [
        #'test/base_contact_tests.yml',
    ],
    'css': [
        'static/src/css/base_contact.css',
    ],
    'installable': True,
    'auto_install': False,
    #'certificate': '0031287885469',
    'images': ['images/base_contact1.jpeg', 'images/base_contact2.jpeg', 'images/base_contact3.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
