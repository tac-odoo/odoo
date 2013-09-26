# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2013-TODAY OpenERP S.A. (<http://openerp.com>).
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

from openerp.osv import osv, fields


class ResPartner(osv.osv):
    _inherit = 'res.partner'

    def _get_attendee_types(self, cr, uid, context=None):
        return [
            ('person', 'Person'),
            ('speaker', 'Speaker'),
            ('resource', 'Resource'),
            ('room', 'Room'),
        ]
    # indirection to avoir rewriting field
    _attendee_types = lambda self, *args, **kwargs: self._get_attendee_types(*args, **kwargs)

    _columns = {
        'attendee_type': fields.selection(_attendee_types, 'Attendee Type', required=True,
                                          help='Usage of this contact on events'),
        'attendee_external': fields.boolean('External?', help='Check this is attendee should be considered external form the company'),
        'avoid_double_allocation': fields.boolean('Avoid double allocation'),
    }

    _defaults = {
        'attendee_type': 'person',
        'avoid_double_allocation': True,
    }
