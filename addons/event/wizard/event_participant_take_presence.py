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


class EventParticipantTakePresenceWizard(osv.TransientModel):
    _name = 'event.participant.take.presence.wizard'

    def _states_selection(self, cr, uid, context=None):
        Participant = self.pool.get('event.participant')
        fields = Participant.fields_get(cr, uid, ['presence'], context=context)
        return fields['presence']['selection']

    _columns = {
        'status': fields.selection(_states_selection, 'Status', required=True),
        'arrival_time': fields.datetime('Arrival Time'),
    }
    _defaults = {
        'arrival_time': fields.datetime.now,
    }

    def update_presence(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        participation_ids = context.get('active_ids') or []
        if not participation_ids:
            return False

        Participant = self.pool.get('event.participant')
        w = self.browse(cr, uid, ids[0], context=context)
        arrival_time = w.arrival_time if w.status == 'late' else False
        ctx = dict(context,
                   presence_arrival_time=arrival_time,
                   presence_departure_time=False)
        return Participant._take_presence(cr, uid, participation_ids,
                                          w.status, context=ctx)
