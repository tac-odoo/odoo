{
    'name': 'Projects Issue',
    'category': 'Website',
    'summary': 'Create Issue From Contact Form',
    'version': '1.0',
    'description': """
OpenERP Projects Issue
======================

        """,
    'author': 'OpenERP SA',
    'depends': ['website_contactus', 'website_mail', 'project_issue'],
    'data': [
        'views/website_project_issue.xml',
    ],
    'installable': True,
}
