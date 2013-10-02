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
from openerp import SUPERUSER_ID

class report_event_participation(osv.Model):
    _name = 'report.event.participation'
    _inherit = ['helper.groupby_many2many']
    _auto = False

    def _get_presence_status(self, cr, uid, context=None):
        Participation = self.pool.get('event.participation')
        presence = Participation.fields_get(cr, uid, ['presence'], context=context)['presence']
        return presence['selection']

    def _get_registration_states(self, cr, uid, context=None):
        Registration = self.pool.get('event.registration')
        return Registration.fields_get(cr, uid, ['state'])['state']['selection']

    _columns = {
        'id': fields.integer('Id', readonly=True),
        'name': fields.char('Name', readonly=True),
        'registration_id': fields.many2one('event.registration', 'Registration', readonly=True),
        'registration_stage_id': fields.many2one('event.registration.stage', 'Registration Status', readonly=True),
        'registration_state': fields.selection(_get_registration_states, 'Registration State', readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner', readonly=True),
        'seance_id': fields.many2one('event.seance', 'Seance', readonly=True),
        'seance_date': fields.char('Seance Start Date', size=64, readonly=True),
        'year': fields.char('Year', size=4, readonly=True),
        'month': fields.selection([
            ('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'),
            ('09','September'), ('10','October'), ('11','November'), ('12','December')], 'Month',readonly=True),
        'seance_event_ids': fields.related('seance_id', 'content_id', 'event_ids',
                                            relation='event.event', string='Events', type='many2many'),
        'presence_status': fields.selection(_get_presence_status, 'Status', readonly=True),
        'presence_duration': fields.float('Presence'),
        'expected_duration': fields.float('Expected'),
        'ratio': fields.float('Ratio'),
    }

    def init(self, cr):
        """
        Initialize the sql view for the event participation
        """
        tools.drop_view_if_exists(cr, 'report_event_participation')

        # TOFIX this request won't select events that have no registration
        cr.execute(""" CREATE VIEW report_event_participation AS (
            SELECT
                p.id AS id,
                p.name AS name,
                p.partner_id AS partner_id,
                p.presence AS presence_status,
                p.registration_id AS registration_id,
                reg.stage_id AS registration_stage_id,
                reg.state AS registration_state,
                s.id AS seance_id,
                to_char(s.date_begin, 'YYYY-MM-DD') AS seance_date,
                to_char(s.date_begin, 'YYYY') AS year,
                to_char(s.date_begin, 'MM') AS month,
                (extract(epoch from (p.departure_time - p.arrival_time)) / 3600::float) AS presence_duration,
                s.duration AS expected_duration,
                (extract(epoch from (p.departure_time - p.arrival_time)) / 3600::float)  / s.duration AS ratio

            FROM event_participation AS p
            LEFT JOIN event_registration AS reg ON (p.registration_id = reg.id)
            LEFT JOIN event_seance AS s ON (p.seance_id = s.id)
            WHERE p.role = 'participant'
        )
        """)

