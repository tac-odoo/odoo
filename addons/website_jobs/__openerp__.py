{
    'name': 'Odoo Jobs',
    'summary': 'Online Directory of Jobs and Consultants worldwide',
    'category': 'Website',
    'version': '1.0',
    'description': """
Website for Online Jobs and Consultants available worldwide
===========================================================
""",
    'author': 'OpenERP SA',
    'depends': ['website', 'project', 'hr', 'project_timesheet'],
    'data': [
        'views/website_jobs.xml'
    ],
    'demo': [],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
}