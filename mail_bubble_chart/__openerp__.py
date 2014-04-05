# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-Today OpenERP S.A. (<http://www.openerp.com>).
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
    'name': 'Bubble Chart for Mail Messages & Comments',
    'version': '1.0',
    'category': 'Social Network',
    'sequence': 2,
    'summary': 'Bubble chart for mails, comments and recent activites on models',
    'description': """
Bubble chart for recent actions based on notifications on all models
======================================================================

Main Features
-------------
* It provides the notifications in bubbled view, 
it provides pictorial view with bubbles for each model and gives recent activities on that model
* One can see recent messages and comments on bubble and can open that recen actioned document
* User can define number of days for "recent", how much recent days activities should be displayed on bubble view.
* For each recent action on document one bubble is created, categorized in group of model.
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['base', 'base_setup', 'mail', 'web_graph'],
    'data': [
        'mail_bubble_chart_view.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'application': True,
    'images': [
    ],
    'css': [
        'static/src/css/mail_bubble_chart.css',
    ],
    'js': [
        'static/src/js/mail_bubble_chart.js',
    ],
    'qweb': [
        'static/src/xml/mail_bubble_chart.xml',
    ],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
