# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request

class website_product_optional(http.Controller):

    @http.route('/shop/options/<int:product_id>', type='http', auth="public", website=True)
    def options(self, product_id, **post):
        request.website.sale_get_order(force_create=1)._cart_update(product_id=int(product_id), add_qty=1, set_qty=1)
        for product_id in  post.keys():
            request.website.sale_get_order(force_create=1)._cart_update(product_id=int(product_id), add_qty=1, set_qty=1)
        return request.redirect("/shop/cart")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
