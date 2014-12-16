# -*- coding: utf-8 -*-
{
    'name': 'Issue Rating',
    'version': '1.0',
    'category': 'Hidden',
    'description': """
This module allows a customer to give rating on Project Issue.
""",
    'author': 'Odoo SA',
    'website': 'http://odoo.com',
    'depends': [
        'rating',
        'project_issue'
    ],
    'data': [
        'views/project_issue_view.xml',
    ],
    'demo': [
        'data/project_issue_demo.xml',
    ],
    'installable': True,
    'auto_install': True,
}
