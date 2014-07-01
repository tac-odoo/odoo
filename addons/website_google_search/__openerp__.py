{
    'name': 'Website Google Search',
    'category': 'Hidden',
    'summary': '',
    'version': '1.0',
    'description': """
OpenERP Website Google Search
=============================

        """,
    'author': 'OpenERP SA',
    'depends': ['website'],
    'data': [
        'views/snippets.xml',
        'views/website_templates.xml',
    ],
    'installable': True,
    'auto_install': False,
}
