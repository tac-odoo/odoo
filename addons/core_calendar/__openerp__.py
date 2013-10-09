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
    'name': 'Calendar',
    'version': '1.0',
    'depends': ['base_setup', 'web_calendar'],
    'summary': 'Multi-Object Calendar System',
    'description': """
This is a full-featured multi-object calendar system.
=====================================================

It supports:
------------
    - Calendar of events
    - Recurring events
    - Multiple calendar from different OpenERP objects.

If you need to manage:
    - meetings, you should install the CRM module.
    - events, you should install the Event module.
    """,
    'author': 'OpenERP SA',
    'category': 'Hidden/Dependency',
    'website': 'http://www.openerp.com',
    'demo': [],
    'data': [
        'resource_view.xml',
        'core_calendar_view.xml',
        'res_partner_view.xml',
        'core_calendar_data.xml',
        'security/core_calendar_security.xml',
        'security/ir.model.access.csv',
    ],
    'js': [
        'static/lib/colorpicker/js/evol.colorpicker.js',
        'static/src/js/*.js',
    ],
    'css': [
        'static/lib/colorpicker/css/evol.colorpicker.css',
        'static/src/css/*.css',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': [],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
