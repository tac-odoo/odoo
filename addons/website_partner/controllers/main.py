# -*- coding: utf-8 -*-
import werkzeug
from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.models.website import unslug


class WebsitePartnerPage(http.Controller):

    # Do not use semantic controller due to SUPERUSER_ID
    @http.route(['/partners/<partner_id>'], type='http', auth="public", website=True)
    def partners_detail(self, partner_id, partner_name='', **post):
        _, partner_id = unslug(partner_id)
        current_grade, current_country = None, None
        grade_id = post.get('grade_id')
        country_id = post.get('country_id')
        if grade_id:
            grade_ids = request.registry['res.partner.grade'].exists(request.cr, request.uid, int(grade_id), context=request.context)
            if grade_ids:
                current_grade = request.registry['res.partner.grade'].browse(request.cr, request.uid, grade_ids[0], context=request.context)
        if country_id:
            country_ids = request.registry['res.country'].exists(request.cr, request.uid, int(country_id), context=request.context)
            if country_ids:
                current_country = request.registry['res.country'].browse(request.cr, request.uid, country_ids[0], context=request.context)
        if partner_id:
            partner = request.registry['res.partner'].browse(request.cr, SUPERUSER_ID, partner_id, context=request.context)
            is_website_publisher = request.registry['res.users'].has_group(request.cr, request.uid, 'base.group_website_publisher')
            if partner.exists() and (partner.website_published or is_website_publisher):
                values = {
                    'main_object': partner,
                    'partner': partner,
                    'current_grade': current_grade,
                    'current_country': current_country
                }
                return request.website.render("website_crm_partner_assign.partner", values)
        return request.not_found()