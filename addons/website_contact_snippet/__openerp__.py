{
    'name': 'Contact Snippet',
    # short description, used as subtitles on modules listings
    'summary': 'Contact Snippet, Demo Snippet',
    # long description of module purpose
    'description': """Small contact snippet, creating leads from a contact-form snippet""",
    # who you are
    'author': 'OpenERP SA',
    'website': 'http://www.odoo.com',
    'category': 'Website',
    'version': '0.1',
    'depends': ['website', 'crm'],
    'data': [
        'views/snippets.xml',
        'views/website_contact_snippet.xml',
    ],
}
