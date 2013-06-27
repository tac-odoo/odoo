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
from collections import defaultdict


class EventSeanceLink(osv.Model):
    """ Link between a seance an one or multiple event """
    _name = 'event.seance.link'
    _description = __doc__
    _columns = {
        'seance_id': fields.many2one('event.seance', 'Seance', required=True),
        'event_id': fields.many2one('event.event', 'Event', required=True),
        'content_id': fields.many2one('event.content', 'Content', required=True),
    }


class EventSeanceType(osv.Model):
    _name = 'event.seance.type'
    _columns = {
        'name': fields.char('Seance Type', size=64, required=True),
    }


class EventSeance(osv.Model):
    _name = 'event.seance'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    SEANCE_STATES = [
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirm', 'Confirmed'),
        ('inprogress', 'In Progress'),
        ('closed', 'Closed'),
        ('done', 'Done'),
    ]

    _columns = {
        'name': fields.char('Seance Name', required=True),
        'type': fields.many2one('event.seance.type', 'Type'),
        'date_begin': fields.datetime('Begin date', required=True),
        'date_end': fields.datetime('End date', required=True),
        'duration': fields.float('Duration', required=True),
        # TODO: add planned_period, planned_period_date
        'participant_min': fields.integer('Participant Min'),
        'participant_max': fields.integer('Participant Max'),
        'main_speaker_id': fields.many2one('res.partner', 'Main Speaker'),
        'address_id': fields.many2one('res.partner', 'Address'),
        'event_link_ids': fields.one2many('event.seance.link', 'seance_id', 'Link to event'),
        'event_ids': fields.many2many('event.event', 'event_seance_link',
                                      id1='seance_id', id2='event_id',
                                      string='Events', readonly=True),
        'participant_ids': fields.one2many('event.participant', 'seance_id', 'Participants'),
        'state': fields.selection(SEANCE_STATES, 'State', readonly=True, required=True),
    }

    _defaults = {
        'state': 'draft',
    }


class EventParticipant(osv.Model):
    """ Event Participant """
    _name = 'event.participant'
    _description = __doc__

    PRESENCE_STATUS = [
        ('none', 'No Presence Information'),
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
    ]

    _columns = {
        'name': fields.char('Participant Name', size=128, required=True),
        'partner_id': fields.many2one('res.partner', 'Participant', required=True),
        'seance_id': fields.many2one('event.seance', 'Seance', required=True),
        'registration_id': fields.many2one('event.registration', 'Registration'),

        # Presence Information
        'presence': fields.selection(PRESENCE_STATUS, 'Presence', required=True),
        'arrival_time': fields.datetime('Arrival Time'),
        'departure_time': fields.datetime('Departure Time'),
    }

    _defaults = {
        'presence': 'none',
    }


class EventType(osv.Model):
    _inherit = 'event.type'

    def _get_selection_seance_modes(self, cr, uid, context=None):
        Event = self.pool.get('event.event')
        fields = Event.fields_get(cr, uid, ['seance_mode'], context=context)
        return fields['seance_mode']['selection']

    _columns = {
        'default_seance_mode': fields.selection(_get_selection_seance_modes, 'Seance mode',
                                                help='Define mode used for created seance of this event'),
    }

    _defaults = {
        'default_seance_mode': 'none',
    }


class EventEvent(osv.Model):
    _inherit = 'event.event'

    def _get_seance_ids(self, cr, uid, ids, fieldname, args, context=None):
        Seance = self.pool.get('event.seance')
        seance_ids = Seance.search(cr, uid, [('event_id', 'in', ids)])

        result = defaultdict(list)
        event_ids_set = set(ids)
        for seance in Seance.browse(cr, uid, seance_ids, context=context):
            for event in seance.event_ids:
                if event.id in event_ids_set:
                    defaultdict[event.id].append(seance.id)
        return result

    _columns = {
        'seance_mode': fields.selection([
            ('none', 'No seance'),
            ('one', 'Unique seance'),
            ('one_per_day', 'One seance per day'),
            ('per_event_calendar', 'Following event calendar'),
            ('preplanning', 'Preplanning')],
            'Seance mode', required=True,
            help='Define mode used for created seance of this event'),
        'seance_ids': fields.function(_get_seance_ids, type='many2many',
                                      relation='event.seance', readonly=True,
                                      string='Seances'),
    }

    _defaults = {
        'seance_mode': 'none',
    }

    def onchange_event_type(self, cr, uid, ids, type_event, context=None):
        values = super(EventEvent, self).onchange_event_type(cr, uid, ids, type_event, context=context)
        if type_event:
            Type = self.pool.get('event.type')
            type_info = Type.browse(cr, uid, type_event, context)
            values['value'].update(
                seance_mode=type_info.default_seance_mode)
        return values
