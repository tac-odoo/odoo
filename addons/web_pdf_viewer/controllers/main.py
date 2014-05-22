# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014-Today OpenERP SA (<http://www.openerp.com>).
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

# -*- coding: utf-8 -*-

from ...web import controllers
from openerp import http

class Reports(controllers.main.Reports):
    @http.route('/web/report', type='http', auth="user")
    def index(self, action, token):
        res = super(Reports, self).index(action, token)
        true = True
        false = False
        null = None
        action_dict = eval(action)
        if  ((action_dict.get('report_type') and action_dict.get('report_type') in ['pdf', 'qweb-pdf']) or (not action_dict.has_key('report_type'))) and action_dict.has_key('mod_installed') :
            del res.headers['Content-Disposition']
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
