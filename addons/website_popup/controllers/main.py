# -*- coding: utf-8 -*-

from openerp import http
from openerp.http import request


class BannerPopup(http.Controller):
    @http.route(['/website_popup/get_content'], type='json', auth="public")
    def get_popup_content(self, list_id, **post):
        mass_mailing_list = request.env['mail.mass_mailing.list'].sudo().browse(int(list_id))
        return {'content': mass_mailing_list.popup_content, 'redirect_url': mass_mailing_list.popup_redirect_url}
