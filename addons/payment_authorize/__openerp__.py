# -*- coding: utf-8 -*-

{
    'name': 'Authorize Payment Acquirer',
    'category': 'Hidden',
    'summary': 'Payment Acquirer: Authorize Implementation',
    'version': '1.0',
    'description': """Authorize Payment Acquirer""",
    'author': 'OpenERP SA',
    'depends': ['payment'],
    'data': [
        'views/authorize.xml',
        'views/payment_acquirer.xml',
        'data/authorize.xml',
    ],
    'installable': True,
}
