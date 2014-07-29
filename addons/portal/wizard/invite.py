# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012-Today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from openerp import SUPERUSER_ID
from openerp.osv import osv
from openerp.tools.translate import _


class invite_wizard(osv.osv_memory):
    _inherit = 'mail.wizard.invite'

    def _get_partner_access_link(self, cr, uid, mail, model, res_id, partner, context=None):
        if context is None:
            context = {}
        if partner and not partner.user_ids:
            contex_signup = dict(context, signup_valid=True)
            signup_url = self.pool['res.partner']._get_signup_url_for_action(cr, SUPERUSER_ID, [partner.id],
                                                                             model=model, res_id=res_id,
                                                                             context=contex_signup)[partner.id]
            return _("<a style='color:inherit' href='%s'>Click here to access the document</a>") % signup_url
        return super(invite_wizard, self)._get_partner_access_link(cr, uid, mail, model, res_id, partner, context=context)
