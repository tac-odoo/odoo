# -*- coding: utf-8 -*-

from openerp import http
from openerp.http import request

class website_hr(http.Controller):

    @http.route(['/page/website.aboutus', '/page/aboutus'], type='http', auth="public", website=True)
    def blog(self, **post):
        hr_obj = request.registry['hr.employee']
        employee_ids = hr_obj.search(request.cr, request.uid, [],
                                     context=request.context)
        values = {
            'employee_ids': hr_obj.browse(request.cr, request.uid, employee_ids,
                                          request.context),
            'view_all': request.registry['res.users'].has_group(request.cr, request.uid, 'base.group_website_publisher'),
        }
        return request.website.render("website.aboutus", values)
