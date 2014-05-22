
{
    'name': 'PDF Viewer',
    'version': '1.1',
    'category': 'Tools',
    'description': """
PDF Viewer
==========

If you not getting proper output Download Plugin from below sites

For Firefox
----------- 
https://addons.mozilla.org/En-us/firefox/addon/pdfjs/

For Chrome
----------
https://chrome.google.com/webstore/detail/chrome-office-viewer/gbkeegbaiigmenfmjfclcdgdpimamgkj?utm_source=chrome-ntp-icon
    """,
    "author": "OpenERP SA",
    "website": "http://www.openerp.com",
    'depends': ["web"],
    'data' : [
        'views/web_pdf_viewer.xml',
    ],
    'installable': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
