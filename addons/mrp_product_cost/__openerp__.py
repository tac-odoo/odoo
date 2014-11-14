# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014-today OpenERP SA (<http://www.openerp.com>).
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
    'name': 'MRP Product Cost',
    'version': '1.0',
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'category': 'Manufacturing',
    'sequence': 18,
    'depends': ['mrp'],
    'description': """
Module to manage the cost price of product based on manufacturing cost.
=======================================================================

This module allows you to calculate cost price of product based on manufacturing cost of product which includes sub products and routing defined on BoM of that product as well as BoM defined on sub products.

    """,
    'data': ['product_view.xml'],
    'test': ['test/cost_price_based_on_bom.yml', 'test/cost_price_based_on_bom_multilevel.yml'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
