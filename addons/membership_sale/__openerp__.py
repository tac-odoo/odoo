# -*- coding: utf-8 -*-
{
    'name': 'Membership Sale',
    'version': '0.1',
    'category': 'Tools',
    'description': """
Membership Sale module manage subscription that allows customer to pay a membership fee or subscription with limited duration of time.

""",
    'author': 'Odoo SA',
    'depends': ['membership', 'sale'],
    'data': [
        'views/membership_sale_view.xml',
    ],
    'installable': True,
    'auto_install': True
}
