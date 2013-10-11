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

from openerp import tools
from openerp.osv import osv, fields


class resource_calendar_leaves_events(osv.Model):
    _name = 'resource.calendar.leaves.events'
    _auto = False
    _columns = {
        'leave_id': fields.many2one('resource.calendar.leaves', 'Leave', readonly=True),
        'event_id': fields.many2one('event.event', 'Event', readonly=True),
    }

    def init(self, cr):
        """
        Initialize the sql view for the leaves events
        """
        tools.drop_view_if_exists(cr, 'resource_calendar_leaves_events')
        cr.execute(""" CREATE VIEW resource_calendar_leaves_events AS (
        SELECT l.id AS leave_id,
               e.id AS event_id

        FROM resource_calendar_leaves l

        LEFT JOIN event_event e ON (
            CASE WHEN l.applies_to = 'company' THEN true
                 WHEN l.applies_to = 'event_all' THEN true
                 WHEN l.applies_to = 'event' THEN e.id = l.event_id
                 ELSE False
            END)

        WHERE l.applies_to IN ('company', 'event_all', 'event')
          AND e.id IS NOT NULL

        )""")


class resource_calendar_leaves(osv.Model):
    _inherit = "resource.calendar.leaves"
    _columns = {
        'event_ids': fields.many2many('event.event', 'resource_calendar_leaves_events',
                                      id1='leave_id', id2='event_id', string='Events'),
    }


class CoreCalendar(osv.Model):
    _inherit = 'core.calendar'
    _columns = {
        'field_event_ids': fields.many2one('ir.model.fields', 'Related Events',
                                           target_relation='event.event'),
    }

    def _get_base_fields(self, cr, uid, context=None):
        return super(CoreCalendar, self)._get_base_fields(cr, uid, context=context) + ['event_ids']

class CoreCalendarEvent(osv.Model):
    _inherit = 'core.calendar.event'

    def _get_events_code(self, cr, uid, ids, fieldname, args, context=None):
        result = {}
        for e in self.browse(cr, uid, ids, context=context):
            result[e.id] = ', '.join(event.reference or event.name
                                     for event in e.event_ids)
        return result

    _columns = {
        'event_ids': fields.many2many('event.event', 'core_calendar_event_events_rel',
                                      id1='calendar_event_id', id2='event_id', string='Related Events'),
        'events_code': fields.function(_get_events_code, type='char', string='Related Events', readonly=True),
    }
