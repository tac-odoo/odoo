{
    'name': 'Sales Coupon',
    'version': '1.0',
    'category': 'Sales Coupon',
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['product','sale','website_sale'],
    'data': [
        'sale_coupon_view.xml',
        'views/report_sale_coupon.xml',
        'views/templates.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}

