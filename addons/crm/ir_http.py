# -*- coding: utf-8 -*-
from openerp.http import request
from openerp import models


class ir_http(models.AbstractModel):
    _inherit = 'ir.http'

    def get_utm_domain_cookies(self):
        return request.httprequest.host

    def _dispatch(self):
        #FIXME: this method not migrate when super method migrate than fix it
        response = super(ir_http, self)._dispatch()
        for var, dummy in self.pool['crm.tracking.mixin'].tracking_fields():
            if var in request.params and (var not in request.session or request.session[var] != request.params[var]):
                response.set_cookie(var, request.params[var], domain=self.get_utm_domain_cookies())
        return response
