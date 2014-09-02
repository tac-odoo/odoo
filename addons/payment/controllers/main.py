# -*- coding: utf-8 -*-
try:
    import simplejson as json
except ImportError:
    import json
import logging
import pprint
import werkzeug

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
        # fix me
        return_url = post.pop('return_url', '')
        if not return_url:
            return_url = '/shop/payment/validate'
        return werkzeug.utils.redirect(return_url)
