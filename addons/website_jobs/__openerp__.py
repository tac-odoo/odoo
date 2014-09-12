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
    'depends': [
    'website',
    'project', 
    'hr', 
    'project_timesheet', 
    'hr_gamification',
    'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/job_data.xml',
        'views/website_jobs.xml',
        'views/category_view.xml',
    ],
    'demo': [],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
}