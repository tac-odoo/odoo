# -*- coding: utf-8 -*-
import logging
import werkzeug

from openerp import http , SUPERUSER_ID
from openerp.http import request
import pprint
_logger = logging.getLogger(__name__)



class Authorize_Controller(http.Controller):

    @http.route([
        '/payment/authorize/return/',
    ], type='http', auth='none')
    def authorize_form_feedback(self, **post):
        _logger.info('Authorize: entering form_feedback with post data %s', pprint.pformat(post))  # debug
        request.registry['payment.transaction'].form_feedback(request.cr, SUPERUSER_ID, post, 'authorize', context=request.context)
        return werkzeug.utils.redirect(post.pop('return_url', '/'))
