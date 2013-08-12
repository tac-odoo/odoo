# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-Today OpenERP SA (<http://www.openerp.com>)
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

from osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DT_FMT
from datetime import datetime, timedelta


class event_event_estimate_end_date_wizard(osv.osv_memory):
    """ Estimate End Date Wizard """
    _name = 'event.event.estimate_end_date.wizard'
    _rec_name = "event_id"

    def _get_estimated_date_end(self, cr, uid, event_id, date_start=None, context=None):
        ed = None
        Event = self.pool.get('event.event')
        event = Event.browse(cr, uid, event_id, context=context)

        if event.has_program:
            event_begin = datetime.strptime(date_start or event.date_begin, DT_FMT)
            event_end = datetime.max - timedelta(days=1)

            ed = event.date_begin

            timeline = None
            if event.content_ids:
                tmlayers = ['working_hours', 'leaves']
                timeline = Event._get_resource_timeline(cr, uid, event.id, layers=tmlayers,
                                                        date_from=event_begin, date_to=event_end,
                                                        context=context)

            ed = Event._estimate_end_date(cr, uid, event_begin, event.content_ids,
                                          timeline=timeline, context=context)

        if not ed:
            # fallback to ensure we have a correct date
            ed = event.date_begin
        return ed

    def button_compute_date_end(self, cr, uid, ids, context=None):
        if not ids:
            return True
        wizard = self.browse(cr, uid, ids[0], context=context)
        date_start = '%s 00:00:00' % wizard.date_start
        date_end = self._get_estimated_date_end(cr, uid, wizard.event_id.id,
                                                date_start=date_start,
                                                context=context)
        wizard.write({'date_end': date_end})

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }

    _columns = {
        'event_id': fields.many2one('event.event', 'Event', readonly=True),
        'date_start': fields.date('Start on', required=True),
        'date_end': fields.date('End on', readonly=True),
    }

    def _default_event_id(self, cr, uid, context=None):
        if context is None:
            context = {}
        if context.get('active_model', '') == 'event.event' and context.get('active_id'):
            return context['active_id']
        return False

    _defaults = {
        'event_id': _default_event_id,
        'date_start': fields.date.today,
    }
