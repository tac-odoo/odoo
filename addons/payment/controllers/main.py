# -*- coding: utf-8 -*-
import logging
import pprint
import werkzeug
import urlparse

from openerp import http, SUPERUSER_ID
from openerp.http import request

_logger = logging.getLogger(__name__)


class PaymentController(http.Controller):

    @http.route([
        '/payment/<provider>/return',
    ], type='http', auth='public')
    def transfer_form_feedback(self, provider, **post):
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        _logger.info('Beginning form_feedback with post data %s', pprint.pformat(post))  # debug
        request.registry['payment.transaction'].form_feedback(cr, uid, provider, post, context)
        base_url = request.env['ir.config_parameter'].get_param('web.base.url')

        provider_obj = request.registry['payment.acquirer.provider']
        provider_id = provider_obj.search(cr, uid, [('name', '=', provider)], context=context)[0]
        provider = provider_obj.browse(cr, uid, provider_id, context=context)
        return_url = post.pop('return_url', '')
        # fix me
        if not return_url:
            return_url = '/shop/payment/validate'
        #somegateway (like authorize.net) is expecting a response to the POST sent by their server.
        #This response is in the form of a URL that gateway will pass on to the
        #client's browser to redirect them to the desired location need javascript.
        if provider.render_template:
            return eval(provider.render_template)
        return werkzeug.utils.redirect(return_url)
