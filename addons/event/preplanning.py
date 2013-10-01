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
from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DT_FMT
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as D_FMT
from openerp.addons.core_calendar.timeline import Availibility


class AutofetchRecordDict(defaultdict):
    def __init__(self, fetching_func, *a, **kw):
        self.fetching_func = fetching_func
        return super(AutofetchRecordDict, self).__init__(None, *a, **kw)

    def __missing__(self, key):
        try:
            dval = self.fetching_func(key)
            return dval
        except Exception:
            raise KeyError


class EventPreplanning(osv.TransientModel):
    _name = 'event.event.preplanning'

    def name_get(self, cr, uid, ids, context=None):
        return [(x['id'], _('Preplanning: %s') % x['name'])
                for x in self.read(cr, uid, ids, ['name'], context=context)]

    def _get_children_ids(self,  cr, uid, ids, fieldname, args, context=None):
        result = {}
        for preplan in self.browse(cr, uid, ids, context=context):
            result[preplan.id] = [child.id for child in preplan.event_id.seance_ids]
        return result

    def _set_children_ids(self, cr, uid, id, fieldname, values, args, context=None):
        result = []
        if not values:
            return result
        Seance = self.pool.get('event.seance')
        Content = self.pool.get('event.content')
        Group = self.pool.get('event.participation.group')

        contents = AutofetchRecordDict(lambda _id: Content.browse(cr, uid, _id, context=context))
        groups = AutofetchRecordDict(lambda _id: Group.browse(cr, uid, _id, context=context))

        for val in values:
            if val[0] == 0:
                content = contents[val[2]['content_id']]
                group = groups[val[2]['group_id']] if val[2]['group_id'] else None
                date_begin = datetime.strptime(val[2]['date_begin'], DT_FMT)
                date_end = date_begin + relativedelta(hours=val[2]['duration'])
                values = Content._prepare_seance_for_content(cr, uid, content, date_begin, date_end, group=group, context=context)

                # preplanned seance should have planned_week + duration set (no date_begin as this should be determined by the user who will planify this)
                values.pop('date_begin', None)
                values['planned_week_date'] = fields.datetime.context_timestamp(cr, uid, date_begin, context=context).strftime(D_FMT)

                id_new = Seance.create(cr, uid, values, context=context)
                result += Seance._store_get_values(cr, uid, [id_new], val[2].keys(), context)
            elif val[0] == 2:
                Seance.unlink(cr, uid, [val[1]], context=context)
            elif val[0] == 4:
                pass  # event should already be attached to this offer (preplanning)
        return result

    _columns = {
        'event_id': fields.many2one('event.event', 'Event Id'),
        'name': fields.related('event_id', 'name', type='char', string='Name', readonly=True),
        'date_begin': fields.related('event_id', 'date_begin', type='datetime', string='Begin date', readonly=True),
        'date_end': fields.datetime('End date', required=True),
        # 'children_ids': fields.related('event_id', 'children_ids', type='one2many', relation='event.event', readonly=True),
        'children_ids': fields.function(_get_children_ids, type='one2many', relation='event.seance',
                                        fnct_inv=_set_children_ids, string='Children Events'),
    }

    def create(self, cr, uid, values, context=None):
        if values and values.get('event_id') and not values.get('date_end'):
            event_obj = self.pool.get('event.event')
            current_end_date = event_obj.browse(cr, uid, values['event_id'], context=context).date_end
            # TODO: compute 'estimated end date' and take max of (current_date_date, estimated_date_end) + next monday
            values['date_end'] = current_end_date
        return super(EventPreplanning, self).create(cr, uid, values, context=context)

    def get_info(self, cr, uid, event_id, date_begin, date_end, context=None):
        if context is None:
            context = {}
        if not event_id:
            return {}
        result = {'contents': [], 'weeks': []}

        # Browse as SUPERUSER_ID to prevent ir.rule from filtering stuff, which
        # will display inconsitant datas
        event = self.pool.get('event.event').browse(cr, SUPERUSER_ID, event_id, context=context)
        week_start_day = MO

        date_begin = datetime.strptime(max(event.date_begin, date_begin), DT_FMT) + relativedelta(weekday=week_start_day(-1))
        date_begin = date_begin.replace(hour=0, minute=0, second=0)

        # Event 'date_end' is now computed by both theoretical planning (est. w/ linear schedule)
        # and last real seance date.
        estimated_date_end = event.date_end
        requested_date_end = date_end
        date_end = datetime.strptime(max(estimated_date_end, requested_date_end), DT_FMT) + relativedelta(weekday=week_start_day(+1))
        date_end = date_end.replace(hour=23, minute=59, second=59)

        lang_name = context.get('lang') or self.pool.get('res.users').context_get(cr, uid, uid)['lang']
        lang_ids = self.pool.get('res.lang').search(cr, uid, [('code', '=', lang_name)], limit=1, context=context)
        lang = self.pool.get('res.lang').browse(cr, uid, lang_ids[0], context=context)

        result['defaults'] = dict(
            tz=event.tz,
            # calendar_id=event.calendar_id.id,
            # registration_ok=False # TODO: allow open/close registration
        )

        for content in event.content_ids:
            result['contents'].append({
                'id': content.id,
                'name': content.name,
                'type_id': content.type_id.id or False,
                'course_id': content.course_id.id or False,
                'module_name': content.module_id.name if content.module_id else False,
                'module_id': content.module_id.id,
                'subject_name': content.subject_id.name or False,
                'groups': [g.id for g in content.group_ids],
                'slot_count': content.slot_count,
                'slot_used': 0,
                'slot_duration': content.slot_duration,
            })
            if content.lang_id:
                content_lang = content.lang_id.iso_code.upper() \
                                or content.lang_id.code[:2].upper() \
                                or content.lang_id.name[:2]
            else:
                content_lang = False
            result['contents'][-1]['lang'] = content_lang

        ContentModule = self.pool.get('event.content.module')
        module_ids = [x['module_id'] for x in result['contents']]
        module_ids = ContentModule.search(cr, uid, [('id', 'in', module_ids)], context=context)

        result['contents'].sort(key=lambda x: (module_ids.index(x['module_id']) if x['module_id'] in module_ids else -1,
                                               x['subject_name'], x['name']))

        tmlayers = ['working_hours', 'leaves']
        timeline = event._get_resource_timeline(layers=tmlayers, date_from=date_begin,
                                                date_to=date_end + relativedelta(weeks=3), context=context)[event.id]

        # Compute available slot per weeks
        slot_per_weeks = defaultdict(list)
        for period in timeline.iterperiods(as_tz='UTC'):
            if period.status == Availibility.FREE:
                # period is always less than 24h, and it's related
                # week is computed based on ISO standard week.
                week_key = period.start.isocalendar()[:2]
                slot_per_weeks[week_key].append(period)

        wd = date_begin.replace()
        while wd <= date_end:
            wd_end = wd + relativedelta(weeks=1)
            week_key = wd.isocalendar()[:2]
            result['weeks'].append({
                'id': wd.strftime('%Y%V'),  # ISO YEAR + ISO WEEK NUMBER
                'name': wd.strftime(lang.date_format),
                'start': wd.strftime(DT_FMT),
                'stop': wd_end.strftime(DT_FMT),
                'slot_count': len(slot_per_weeks[week_key]),
                'slot_used': 0,
            })
            wd = wd_end
        return result
