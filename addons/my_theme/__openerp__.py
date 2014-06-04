{
    'name': 'My Theme',
    'category': 'Website',
    'summary': 'Customisations',
    'version': '1.0',
    'description': """
Create Themes for website presentation
======================================
        """,
    'author': 'fp@odoo.com',
    'depends': ['website'],
    'data': ["views/pages.xml","views/snippets.xml","views/my_theme.xml"],
    'installable': True,
}
