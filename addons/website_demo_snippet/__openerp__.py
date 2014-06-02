{
    'name': 'Snippet Demo',
    # short description, used as subtitles on modules listings
    'summary': 'Snippet Demo',
    # long description of module purpose
    'description': """Snipper Demo""",
    # who you are
    'author': 'OpenERP SA',
    'website': 'http://www.odoo.com',
    'category': 'Website',
    'version': '0.1',
    'depends': ['website_crm'],
    'data': [
        'views/snippets.xml',
        'views/website_demo_snippet.xml',
    ],
}
