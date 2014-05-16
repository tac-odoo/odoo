#Hr employee tree structure..
{
    'name':'hr_structure',
    'version': '1.1',
    'author': 'OpenERP SA',
    'category': 'Human Resources',
    'website': 'http://www.openerp.com',
    'summary': 'Heirarchycal Chart Employee',
    'description': """
Human Resources Management
==========================
    This is Application of Employee of Organization displayee in Hierarchycal View

    """,
    'depends': ['base','hr','web','base_setup','website','mail'],
    'data': [
    'employee_tree_view.xml',
    #'view/hr_employee_tree.xml',
    ],
    'css':[
        'static/src/css/hr_employee_tree.css',
    ],
    'js':[
        'static/src/js/hr_employee_tree.js',
        'static/src/js/d3.v3.js',
    ],
    'qweb': [
        'static/src/xml/hr_employee_tree.xml'
        ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
