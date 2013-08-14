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


class report_event_seance(osv.Model):
    _name = 'report.event.seance'
    _description = 'Event Seance'
    _auto = False

    _columns = {
        'id': fields.integer('Id', readonly=True),
        'seance_id': fields.many2one('event.seance', 'Seance', readonly=True, group_operator='SUM'),
        'type_id': fields.many2one('event.seance.type', 'Type', readonly=True),
        'speaker_id': fields.many2one('res.partner', 'Speaker', readonly=True),
        'address_id': fields.many2one('res.partner', 'Location', readonly=True),
        'duration': fields.float('Duration', readonly=True),
        'course_id': fields.many2one('event.course', 'Course', readonly=True),
        'content_id': fields.many2one('event.content', 'Content', readonly=True),
        'event_id': fields.many2one('event.event', 'Event', readonly=True),
    }

    def init(self, cr):
        """
        Initialize the sql view for the event seance
        """
        tools.drop_view_if_exists(cr, 'report_event_seance')

        # TOFIX this request won't select events that have no registration
        cr.execute(""" CREATE VIEW report_event_seance AS (
            SELECT
                seance.id||'-'||event.id AS id,
                seance.id AS seance_id,
                seance.type_id AS type_id,
                seance.main_speaker_id AS speaker_id,
                seance.address_id AS address_id,
                seance.course_id AS course_id,
                seance.duration AS duration,
                event.id AS event_id,
                content.id AS content_id

            FROM event_seance seance
            LEFT JOIN event_seance_type seancetype ON (seance.type_id = seancetype.id)
            LEFT JOIN event_content content ON seance.content_id = content.id
            LEFT JOIN event_content_link eclink ON eclink.content_id = content.id
            LEFT JOIN event_event event ON eclink.event_id = event.id
            WHERE seancetype.included_into_analysis = true
        )
        """)
