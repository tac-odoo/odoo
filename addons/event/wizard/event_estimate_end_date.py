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
from openerp.tools.translate import _
from datetime import datetime, timedelta


class event_event_estimate_end_date_wizard(osv.osv_memory):
    """ Estimate End Date Wizard """
    _name = 'event.event.estimate_end_date.wizard'
    _rec_name = "event_id"

    def _get_estimated_date_end(self, cr, uid, event_id, date_start=None, simulation_id=None, context=None):
        if context is None:
            context = {}
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
                if context.get('event_date_end_include_scheduled_items'):
                    tmlayers.append('events')
                timeline = Event._get_resource_timeline(cr, uid, event.id, layers=tmlayers,
                                                        date_from=event_begin, date_to=event_end,
                                                        context=context)

            ed = Event._estimate_end_date(cr, uid, event_begin, event.content_ids,
                                          simulation_id=simulation_id,
                                          timeline=timeline, context=context)

        if not ed:
            # fallback to ensure we have a correct date
            ed = event.date_begin
        return ed

    def button_compute_date_end(self, cr, uid, ids, context=None):
        if not ids:
            return True
        if context is None:
            context = {}
        wizard = self.browse(cr, uid, ids[0], context=context)
        date_start = wizard.date_start

        Simulation = self.pool.get('event.event.schedule.simulation')
        simulation_id = Simulation.create(cr, uid, {
            'date_begin': date_start,
            'allocator': wizard.event_id.content_planification,
            'source_event_id': wizard.event_id.id,
            'include_existing_seances': wizard.include_existing_seances,
            }, context=context)

        simulation_ctx = dict(context,
                              event_date_end_include_scheduled_items=wizard.include_existing_seances)

        date_end = self._get_estimated_date_end(cr, uid, wizard.event_id.id,
                                                date_start=date_start,
                                                simulation_id=simulation_id,
                                                context=simulation_ctx)
        wizard.write({'date_end': date_end, 'simulation_id': simulation_id})

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }

    def button_show_simulation(self, cr, uid, ids, context=None):
        if not ids:
            return True
        if context is None:
            context = {}
        wizard = self.browse(cr, uid, ids[0], context=context)
        if not wizard.simulation_id:
            return True

        user_lang = context.get('lang') or self.pool.get('res.users').context_get(cr, uid)['lang']
        user_lang_formats = self.pool.get('res.lang')._lang_date_formats(cr, uid, user_lang)

        date_start = datetime.strptime(wizard.date_start, DT_FMT).strftime(user_lang_formats['datetime'])
        date_start = fields.datetime.context_timestamp(cr, uid, date_start, context=context)
        date_end = datetime.strptime(wizard.date_end, DT_FMT).strftime(user_lang_formats['datetime'])
        date_end = fields.datetime.context_timestamp(cr, uid, date_end, context=context)

        return {
            'name': _('Simulation result (begins: %s, ends: %s)') % (date_start, date_end),
            'type': 'ir.actions.act_window',
            'res_model': 'event.event.schedule.simulation.seance',
            'view_type': 'form',
            'view_mode': 'calendar,tree',
            'domain': [('simulation_id','=', wizard.simulation_id.id)],
        }

    _columns = {
        'event_id': fields.many2one('event.event', 'Event', readonly=True),
        'date_start': fields.datetime('Start on', required=True),
        'date_end': fields.datetime('End on', readonly=True),
        'include_existing_seances': fields.boolean('Include existing seances'),
        'simulation_id': fields.many2one('event.event.schedule.simulation', 'Simulation'),
    }

    def _default_event_id(self, cr, uid, context=None):
        if context is None:
            context = {}
        if context.get('active_model', '') == 'event.event' and context.get('active_id'):
            return context['active_id']
        return False

    def _default_date_start(self, cr, uid, context=None):
        if context is None:
            context = {}
        if context.get('active_model', '') == 'event.event' and context.get('active_id'):
            event_id = context['active_id']
            event = self.pool.get('event.event').browse(cr, uid, event_id, context=context)
            return event.date_begin
        return fields.datetime.now(cr, uid)

    _defaults = {
        'event_id': _default_event_id,
        'date_start': _default_date_start,
        'include_existing_seances': True,
    }


class EventEventScheduleSimulation(osv.TransientModel):
    _name = 'event.event.schedule.simulation'

    def _get_schedule_allocator(self, cr, uid, context=None):
        return [
            ('linear', 'Linear'),
            ('preplanning', 'Preplanning'),
        ]

    _columns = {
        'date_begin': fields.datetime('Date begin', required=True),
        'source_event_id': fields.many2one('event.event', 'Source Event', readonly=True),
        'include_existing_seances': fields.boolean('Include existing seances'),
        'seance_ids': fields.one2many('event.event.schedule.simulation.seance', 'simulation_id', 'Seances'),
        'allocator': fields.selection(_get_schedule_allocator, 'Allocator', required=True),
    }


class EventEventScheduleSimulationSeance(osv.TransientModel):
    _name = 'event.event.schedule.simulation.seance'
    _columns = {
        'simulation_id': fields.many2one('event.event.schedule.simulation', 'Schedule Simulation'),
        'name': fields.char('Name', size=64, readonly=True),
        'date_begin': fields.datetime('Date begin', readonly=True),
        'duration': fields.float('Duration', readonly=True),
        'date_end': fields.datetime('Date end', readonly=True),
        'description': fields.text('Description', readonly=True),
        'content_id': fields.many2one('event.content', 'Content', readonly=True),
        'module_id': fields.many2one('event.content.module', 'Module', readonly=True),
        'seance_id': fields.many2one('event.seance', 'Seance', readonly=True),
        'simulation_scheduled': fields.boolean('Scheduled by OpenERP Simulation', readonly=True),
    }
