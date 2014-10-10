# -*- coding: utf-8 -*-
{
    'name': "evaluation_matrix",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "odoo",
    'website': "http://www.odoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['website'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/templates.xml',
        'data/comparison_factor.csv',
        'data/comparison_item.csv',
        'data/comparison_factor_result.csv',
        'data/comparison_vote_values.csv',
        'data/comparison_vote.csv'
    ],
    'qweb': [
        'static/src/views/*.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
}