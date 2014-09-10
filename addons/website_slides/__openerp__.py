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
    'name': 'Odoo Presentation',
    'version': '1.0',
    'summary': 'Publish Presentations, Videos, Documents and Infographic',
    'category': 'website',
    'description': """
Publish Presentations, Videos, Documents and Infographic Online
================================================================
You can upload presentations, videos, documents and infographic and moderate and publish on different channels.

* Channel Management
* Filters and Tagging
* Moderations of Channels and contents
* Document Type Supported (pdf and all image type)
""",
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['website', 'website_mail'],
    'data': [
        'view/slides_website.xml',
        'view/slides_backend.xml',
        'security/ir.model.access.csv',
        'data/website_slides_data.xml',
    ],   
    'installable': True,
    'auto_install': False,   
}
