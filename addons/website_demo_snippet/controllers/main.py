# -*- coding: utf-8 -*-
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp import SUPERUSER_ID


class ContactUsShort(http.Controller):
    @http.route(['/crm/contact_short'], type='json', methods=['POST'], auth="public", website=True)
    def contactus(self, question=None, email=None, section_id=None, **kwargs):
        lead_values = {
            'name': 'Lead from %s (Contact Snippet)' % email,
            'description': question,
            'email_from': email,
            'section_id': section_id,
            'user_id': False,
        }
        return request.registry['crm.lead'].create(request.cr, SUPERUSER_ID, lead_values, request.context)
