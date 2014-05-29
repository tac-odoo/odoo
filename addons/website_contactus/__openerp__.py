{
    'name': 'Contactus Form',
    'category': 'Website',
    'summary': 'Public Contactus Form',
    'version': '1.0',
    'description': """
OpenERP Contact Form
====================

        """,
    'author': 'OpenERP SA',
    'depends': ['website'],
    'data': [
        'views/website_contactus.xml',
    ],
    'installable': True,
    'auto_install': False,
}
