# -*- coding: utf-8 ⁻*-
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
from openerp.tools.translate import _


class resource_calendar_leaves(osv.Model):
    _inherit = "resource.calendar.leaves"

    def _get_applies_to(self, cr, uid, ids, field_name, args, context=None):
        result = {}
        for leave in self.browse(cr, uid, ids, context=context):
            if leave.partner_id or leave.resource_id:
                result[leave.id] = 'resource'
            elif leave.event_id:
                result[leave.id] = 'event'
            elif leave.calendar_id:
                result[leave.id] = 'calendar'
            else:
                result[leave.id] = 'company'
        return result

    _columns = {
        'event_id': fields.many2one('event.event', 'Event'),
        'applies_to': fields.function(_get_applies_to, type='selection', string='Applies to',
                                      selection=lambda s, *a, **kw: s._get_applies_to_selection(*a, **kw),
                                      store=True, fnct_inv=lambda *a: True),
    }

    def _get_applies_to_selection(self, cr, uid, context=None):
        result = super(resource_calendar_leaves, self)._get_applies_to_selection(cr, uid, context=context)
        result.append(('event', _('This event')))
        return result

    def _get_applies_to(self, cr, uid, ids, field_name, args, context=None):
        result = {}
        for leave in self.browse(cr, uid, ids, context=context):
            if leave.partner_id or leave.resource_id:
                result[leave.id] = 'resource'
            # elif leave.event_id:
            #     result[leave.id] = 'event'
            elif leave.calendar_id:
                result[leave.id] = 'calendar'
            else:
                result[leave.id] = 'company'
        return result

    def onchange_applies_to(self, cr, uid, ids, applies_to, context=None):
        ocv = super(resource_calendar_leaves, self).onchange_applies_to(cr, uid, ids, applies_to, context=context)
        if applies_to == 'event':
            ocv['value'].update(resource_id=False, partner_id=False)
        return ocv
