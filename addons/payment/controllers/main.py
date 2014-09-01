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
    ], type='http', auth='none')
    def transfer_form_feedback(self, provider, **post):
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        print '>>>>>>>>>>>>>>>>>>>..1111111',provider
        _logger.info('Beginning form_feedback with post data %s', pprint.pformat(post))  # debug
        request.registry['payment.transaction'].form_feedback(cr, uid, provider, post, context)
        return werkzeug.utils.redirect(post.pop('return_url', '/'))
        
#    @http.route([
#        '/payment/buckaroo/return',
#        '/payment/buckaroo/cancel',
#        '/payment/buckaroo/error',
#        '/payment/buckaroo/reject',
#    ], type='http', auth='none')
#    def buckaroo_return(self, **post):
#        """ Buckaroo."""
#        print '>>>>>>>>>>>>>>>>>>>>>>>>postsssssss',post
#        _logger.info('Buckaroo: entering form_feedback with post data %s', pprint.pformat(post))   debug
#        request.registry['payment.transaction'].form_feedback(request.cr, SUPERUSER_ID, post, context=request.context)
#        return_url = post.pop('return_url', '')
#        if not return_url:
#            data ='' + post.pop('ADD_RETURNDATA', '{}').replace("'", "\"")
#            custom = json.loads(data)
#            return_url = custom.pop('return_url', '/')
#        return werkzeug.utils.redirect(return_url)
