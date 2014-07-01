{
    'name': 'Website Google Search',
    'category': 'Hidden',
    'summary': '',
    'version': '1.0',
    'description': """
OpenERP Website Google Map
========================

        """,
    'author': 'OpenERP SA',
    'depends': ['website'],
    'data': [
        'views/website_templates.xml',
        'views/website_views.xml',
        'views/res_config.xml',
    ],
    'installable': True,
    'auto_install': False,
}
