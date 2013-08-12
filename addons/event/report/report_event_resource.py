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

from datetime import datetime
from dateutil.relativedelta import relativedelta, MO
from collections import defaultdict
from openerp.osv import osv, fields
from openerp import tools
from openerp.addons.core_calendar.timeline import Availibility

class report_event_resource(osv.Model):
    _name = 'report.event.resource'
    _description = 'Event Resource'
    _auto = False

    RESOURCE_TYPES = [
        ('speaker', 'Speaker'),
        ('room', 'Room'),
        ('equipment', 'Equipment'),
    ]

    def _get_resource_hours(self, cr, uid, ids, fieldnames, args, context=None):
        if any(context.get(f) for f in ['this_week', 'this_month', 'this_year']):
            Partner = self.pool.get('res.partner')

            today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
            if context.get('this_week'):
                start = today - relativedelta(weekday=MO(-1))
                end = start + relativedelta(weeks=1)
            elif context.get('this_month'):
                start = today.replace(day=1)
                end = start + relativedelta(months=1)
            elif context.get('this_year'):
                start = today.replace(day=1, month=1)
                end = start + relativedelta(years=1)

            result = {}
            for partner in Partner.browse(cr, uid, ids, context=context):
                result[partner.id] = {}
                for f in fieldnames:
                    result[partner.id].setdefault(f, 0.0)

            timelines = Partner._get_resource_timeline(cr, uid, ids,
                                                       date_from=start, date_to=end,
                                                       context=context)
            for partner_id, p_timeline in timelines.iteritems():
                # Working Hours
                sum_wkhours = sum(p.duration
                                  for p in p_timeline.iter(by='change', as_tz='UTC',
                                                           start=start, end=end, layers=['working_hours'])
                                  if p.status == Availibility.FREE)

                # Leaves
                sum_leaves = sum(p.duration
                                 for p in p_timeline.iter(by='change', as_tz='UTC',
                                                          start=start, end=end, layers=['leaves'])
                                 if p.status >= Availibility.BUSY_TENTATIVE)

                # Effective Time (Busy events times)
                sum_events = sum(p.duration
                                 for p in p_timeline.iter(by='change', as_tz='UTC',
                                                          start=start, end=end, layers=['events'])
                                 if p.status >= Availibility.BUSY_TENTATIVE)

                # Effective Rate
                eff_rate = sum_events / ((sum_wkhours - sum_leaves) or 1.0)

                result[partner_id].update(working_hours=sum_wkhours,
                                          effective_time=sum_events,
                                          effective_rate=eff_rate,
                                          leave_time=sum_leaves,
                                          reserved_time=0.0)  # TODO: compute reserved time based on calendar preferences

            return result

        return defaultdict(lambda: defaultdict(float))

    _columns = {
        'id': fields.integer('Id', readonly=True),
        'resource_name': fields.char('Resource Name', char=128, readonly=True),
        'resource_id': fields.many2one('res.partner', 'Resource', readonly=True),
        'resource_type': fields.selection(RESOURCE_TYPES, 'Type', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'calendar_id': fields.many2one('resource.calendar', 'Calendar', readonly=True),
        'working_hours': fields.function(_get_resource_hours, type='float', string='Working Hours', multi='hours'),
        'leave_time': fields.function(_get_resource_hours, type='float', string='Leaves', multi='hours'),
        'reserved_time': fields.function(_get_resource_hours, type='float', string='Reserved', multi='hours'),
        'effective_time': fields.function(_get_resource_hours, type='float', string='Effective Time', multi='hours'),
        'effective_rate': fields.function(_get_resource_hours, type='float', string='Effective Rate', multi='hours'),
    }

    def init(self, cr):
        """
        Initialize the sql view for the event resource
        """
        tools.drop_view_if_exists(cr, 'report_event_resource')

        # TOFIX this request won't select events that have no registration
        cr.execute(""" CREATE VIEW report_event_resource AS (
            SELECT
                rp.id AS id,
                rp.name AS resource_name,
                rp.id AS resource_id,
                CASE WHEN rp.speaker THEN 'speaker'
                     WHEN rp.room THEN 'room'
                     WHEN rp.equipment THEN 'equipment'
                END AS resource_type,
                rp.parent_id AS company_id,
                rp.calendar_id AS calendar_id
            FROM res_partner rp

            WHERE
                (rp.speaker = true OR rp.room = true OR rp.equipment = true)

        )
        """)