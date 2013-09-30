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

import time
import math
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from functools import partial
from dateutil.relativedelta import relativedelta, MO
from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.tools import float_is_zero
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DT_FMT
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as D_FMT
from openerp.addons.base.res.res_partner import _tz_get
from core_calendar.timeline import Timeline, Availibility
from openerp.addons.core_calendar.resource import float_to_hm
from openerp.tools import logged, flatten
import openerp.addons.decimal_precision as dp


class list_counted(list):
    def __init__(self, expected=0):
        self.expected = expected


class EventSeanceType(osv.Model):
    _name = 'event.seance.type'
    _columns = {
        'name': fields.char('Seance Type', size=64, required=True),
        'included_into_analysis': fields.boolean('Included into Analysis',
                                                 help="Does this type of seance be included "
                                                      "into 'Event Seance Report'?"),
        'manual_participation': fields.boolean('Manual Participations',
                                               help='Check if you want to manually create '
                                                    'participations for this type of seances'),
        'speaker_product_id': fields.many2one('product.product', "Speaker's Product"),
        'room_product_id': fields.many2one('product.product', "Room's Product"),
        'equipment_product_id': fields.many2one('product.product', "Equipement Product"),
        'speaker_min_required': fields.integer('Minimum Speakers required'),
        'room_required': fields.boolean('Room Required'),
    }

    _defaults = {
        'included_into_analysis': True,
        'manual_participation': False,
        'speaker_min_required': 1,
        'room_required': True,
    }


class EventContentModule(osv.Model):
    _name = 'event.content.module'

    def _get_infos(self, cr, uid, ids, fieldnames, args, context=None):
        if not ids:
            return {}
        if context is None:
            context = {}
        result = {}
        for _id in ids:
            result[_id] = {'date_begin': False, 'date_end': False}
        if context.get('event_id'):
            event_ids = (context['event_id'],)
            cr.execute("""
                SELECT module.id AS module_id,
                       content_info.duration AS content_duration,
                       min(seance.date_begin) AS min_date,
                       max(seance.date_begin + (INTERVAL '1 hour' * seance.duration)) AS max_date
                FROM event_event AS event
                LEFT JOIN event_content_link AS link ON (link.event_id = event.id)
                LEFT JOIN event_content AS content ON (link.content_id = content.id)
                LEFT JOIN event_content_module module ON (content.module_id = module.id)
                LEFT JOIN event_seance AS seance ON (seance.content_id = content.id)
                LEFT JOIN (
                    SELECT event.id AS event_id,
                           content.module_id AS module_id,
                           sum(content.duration) AS duration
                    FROM event_event AS event
                    LEFT JOIN event_content_link AS link ON (link.event_id = event.id)
                    LEFT JOIN event_content AS content ON (link.content_id = content.id)
                    WHERE event.id IN %s
                    GROUP BY event.id, content.module_id
                ) AS content_info ON (content_info.event_id = event.id AND content_info.module_id = module.id)
                WHERE seance.date_begin IS NOT NULL
                  AND content.module_id IS NOT NULL
                  AND event.id IN %s
                GROUP BY module.id, content_info.duration
            """, (event_ids, event_ids,))
            for info in cr.dictfetchall():
                module_id = info['module_id']
                result[module_id].update(date_begin=info['min_date'],
                                         date_end=info['max_date'],
                                         duration=info['content_duration'])
        return result

    _columns = {
        'name': fields.char('Module name', required=True),
        'sequence': fields.integer('Sequence'),
        'date_begin': fields.function(_get_infos, type='datetime', string='Begin date', multi='dates'),
        'date_end': fields.function(_get_infos, type='datetime', string='End date', multi='dates'),
        'duration': fields.function(_get_infos, type='float', string='Duration', multi='dates'),
    }

    def search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        if context.get('event_id'):
            # Display only from used in the related "event"
            Event = self.pool.get('event.event')
            module_ids = set()
            for content in Event.browse(cr, user, context['event_id'], context=context).content_ids:
                if content.module_id:
                    module_ids.add(content.module_id.id)
            module_filter = [('id', 'in', list(module_ids))]
            if args:
                module_filter.insert(0, '&')
            args = module_filter + args
        return super(EventContentModule, self).search(cr, user, args, offset=offset,
                                                      limit=limit, order=order,
                                                      context=context, count=count)


class EventContent(osv.Model):
    """ Event Content """
    _name = 'event.content'
    _description = __doc__
    _order = 'sequence, id'

    def _get_remaining_duration_to_schedule(self, cr, uid, ids, field_name, args, context=None):
        result = {}
        if not ids:
            return result

        for content in self.browse(cr, uid, ids, context=context):
            scheduled_duration = 0.
            for seance in content.seance_ids:
                if seance.state == 'cancel':
                    continue
                # TODO: what is seance is not planned
                scheduled_duration += seance.duration
            result[content.id] = content.duration - scheduled_duration

        return result

    def _get_slot_info(self, cr, uid, ids, fieldname, args, context=None):
        result = {}
        for content in self.browse(cr, uid, ids, context=context):
            count = math.ceil(content.duration / float(content.slot_duration or 1.))
            info_args = (count,) + float_to_hm(content.slot_duration)
            result[content.id] = {
                'slot_count': count,
                'slot_info': '%d x %d:%02d' % info_args,
            }
        return result

    def onchange_duration(self, cr, uid, ids, field_source, slot_count, slot_duration, tot_duration, context=None):
        values = {}
        company_id = context.get('company_id') or self.pool.get('res.users')._get_company(cr, uid, context=context)
        if company_id:
            slot_time_unit = self.pool.get('res.company').read(cr, uid, company_id, ['slot_time_unit'])['slot_time_unit']
            if not float_is_zero(math.modf(slot_duration / (float(slot_time_unit) or 1.))[0], precision_digits=2):
                raise osv.except_osv(
                    _('Error'),
                    _('Slot unit duration (%s) must a multiple of %s') % (
                        '%02d:%02d' % tuple(a * b for a, b in zip(reversed(math.modf(slot_duration)), [1, 60])),
                        '%02d:%02d' % tuple(a * b for a, b in zip(reversed(math.modf(slot_time_unit)), [1, 60]))
                    ))
        if field_source in ('slot_duration', 'slot_count'):
            new_count = math.ceil(slot_count)
        else:
            new_count = math.ceil(tot_duration / float(slot_duration or 1.))
        new_duration = new_count * slot_duration
        if new_duration != tot_duration:
            values['duration'] = new_duration
        if new_count != slot_count:
            values['slot_count'] = new_count

        return {'value': values}

    def onchange_type(self, cr, uid, ids, type_id, context=None):
        return {'value': {}}

    _columns = {
        'sequence': fields.integer('Sequence', required=True),
        'name': fields.char('Content', size=128, required=True),
        'type_id': fields.many2one('event.seance.type', 'Type',
                                   help='Default type of seance'),
        'lang_id': fields.many2one('res.lang', 'Language'),
        'event_ids': fields.many2many('event.event', 'event_content_link',
                                      id1='content_id', id2='event_id',
                                      string='Events', readonly=True),
        'seance_ids': fields.one2many('event.seance', 'content_id', 'Seances', readonly=True),
        'duration': fields.float('Duration', required=True),
        'remaining_duration': fields.function(_get_remaining_duration_to_schedule, type='float', string='Remaining Duration',
                                              help='Remaining duration to be scheduled'),
        'slot_duration': fields.float('Slot duration'),
        'slot_count': fields.function(_get_slot_info, type='integer', string='Slot count', store=True, multi='slot-info'),
        'slot_info': fields.function(_get_slot_info, type='char', string='Info', store=True, multi='slot-info'),
        'is_divided': fields.boolean('Divided?'),
        'group_ids': fields.one2many('event.participation.group', 'event_content_id'),
        'module_id': fields.many2one('event.content.module', 'Module'),
        'room_id': fields.many2one('res.partner', 'Room', help='Default room assigned to created seances related to this content'),
        'speaker_id': fields.many2one('res.partner', 'Speaker', help='Default speaker assigned to created seances related to this content'),
        'other_resource_ids': fields.many2many('res.partner', 'event_content_other_resources_rel',
                                               id1='content_id', id2='partner_id', string='Other resources'),
        'constraint_ids': fields.many2many('event.constraint', id1='content_id', id2='constraint_id', string='Constraints'),
    }

    def copy_data(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default.update(seance_ids=None, event_ids=None)
        return super(EventContent, self).copy_data(cr, uid, id, default=default, context=context)

    def _default_slot_duration(self, cr, uid, context=None):
        if context is None:
            context = {}
        if context.get('calendar_id'):
            calendar = self.pool.get('resource.calendar').browse(cr, uid, context['calendar_id'], context=context)
            return calendar.slot_duration
        return 1

    _defaults = {
        'duration': 1,
        'sequence': 0,
        'slot_duration': _default_slot_duration,
        'slot_count': 1,
    }

    def _msg_divided_groups(self, cr, uid, ids, context=None):
        errors = []
        for content in self.browse(cr, uid, ids, context=context):
            if content.is_divided and len(content.group_ids) < 2:
                errors.append(_("Content '%s' is divided, it should have at least 2 groups") % (content.name,))
        return u'\n'.join(errors)

    def _check_divided_groups(self, cr, uid, ids, context=None):
        for content in self.browse(cr, uid, ids, context=context):
            if content.is_divided and len(content.group_ids) < 2:
                return False
        return True

    _constraints = [
        (lambda self, *a, **kw: self._check_divided_groups(*a, **kw), _msg_divided_groups, ['group_ids']),
    ]

    def create(self, cr, uid, values, context=None):
        new_id = super(EventContent, self).create(cr, uid, values, context=context)
        Registration = self.pool.get('event.registration')
        if values.get('is_divided'):
            content = self.browse(cr, uid, new_id, context=context)
            registration_ids = Registration.search(cr, uid, [('event_id.content_ids', 'in', content.id), ('state', '!=', 'done')], context=context)
            Registration._update_registration_groups(cr, uid, registration_ids, context=context)
        return new_id

    def write(self, cr, uid, ids, values, context=None):
        rval = super(EventContent, self).write(cr, uid, ids, values, context=context)
        if any(f in values for f in ['is_divided', 'group_ids']):
            Registration = self.pool.get('event.registration')
            registration_ids = Registration.search(cr, uid, [('event_id.content_ids', 'in', ids), ('state', '!=', 'done')], context=context)
            Registration._update_registration_groups(cr, uid, registration_ids, context=context)
        if 'event_ids' in values:
            self.unlink_isolated_content(cr, uid, ids, context=context)

        non_planned_seance_update = {}
        if 'speaker_id' in values:
            non_planned_seance_update['main_speaker_id'] = values['speaker_id']
        if 'room_id' in values:
            non_planned_seance_update['address_id'] = values['room_id']
        if 'other_resource_ids' in values:
            non_planned_seance_update['other_resource_ids'] = values['other_resource_ids']
        if non_planned_seance_update:
            Seance = self.pool.get('event.seance')
            future_seance_filter = [
                ('content_id', 'in', ids),
                '|',
                    ('date_begin', '=', False),
                    '&', ('date_begin', '>=', time.strftime('%Y-%m-%d %H:%M:%S')),
                         ('state', '=', 'draft')
            ]
            seance_ids = Seance.search(cr, uid, future_seance_filter, context=context)
            Seance.write(cr, uid, seance_ids, non_planned_seance_update, context=context)
        return rval

    def unlink_isolated_content(self, cr, uid, ids, context=None):
        to_unlink = []
        for content in self.read(cr, uid, ids, ['event_ids'], context=context):
            if not content['event_ids']:
                to_unlink.append(content['id'])
        return self.unlink(cr, uid, to_unlink, context=context)

    def _prepare_seance_for_content(self, cr, uid, content, date_begin, date_end, group=None, context=None):
        if context is None:
            context = {}
        if isinstance(date_begin, basestring):
            date_begin = datetime.strptime(date_begin, DT_FMT)
        if isinstance(date_end, basestring):
            date_end = datetime.strptime(date_begin, DT_FMT)
        duration_delta = date_end - date_begin
        duration = duration_delta.days * 24 + (duration_delta.seconds / 3600.)

        speaker_id = (group and group.speaker_id.id) or content.speaker_id.id or False
        address_id = (group and group.room_id.id) or content.room_id.id or False
        values = {
            'name': content.name,
            'content_id': content.id,
            'type_id': content.type_id.id,
            'lang_id': content.lang_id.id,
            'group_id': group.id if group else False,
            'date_begin': date_begin.strftime(DT_FMT),
            'duration': duration,
            'main_speaker_id': speaker_id,
            'address_id': address_id,
            'other_resource_ids': [(6, 0, [p.id for p in content.other_resource_ids])],
        }
        return values

    def create_seances_from_content(self, cr, uid, ids, date_begin, date_end, o2m_commands=False, context=None):
        """Create seances associated with the requested content
        :return: list of created events id
        """
        if isinstance(ids, (int, long)):
            ids = [ids]
        Seance = self.pool.get('event.seance')
        new_seance_ids = []
        prepare_seance = partial(self._prepare_seance_for_content, cr, uid, context=context)
        for content in self.browse(cr, uid, ids, context=context):
            for group in (content.group_ids or [None]):
                values = prepare_seance(content, date_begin, date_end, group=group)
                if o2m_commands:
                    new_seance_ids.append((0, 0, values))
                else:
                    nsid = Seance.create(cr, uid, values, context=context)
                    new_seance_ids.append(nsid)
        return new_seance_ids

    def button_open_group_registration_dispatch(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not ids:
            return {}
        content = self.browse(cr, uid, ids[0], context=context)
        event_ids = [e.id for e in content.event_ids]
        return {
            'type': 'ir.actions.act_window',
            'name': _('Groups of %s') % content.name,
            'res_model': 'event.registration',
            'view_type': 'form',
            'view_mode': 'kanban,tree,form',
            'domain': [('event_id', 'in', event_ids)],
            'context': {'group_by': 'group_ids', 'group_for_content_id': content.id},
        }
        return True


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
        ('cancel', 'Cancel'),
    ]

    # Required except in draft state
    RQ_EXCEPT_IN_DRAFT = dict(readonly=False,
                              states=dict((st, [('required', True)])
                                          for st, sn in SEANCE_STATES
                                          if st != 'draft'))

    WRITABLE_ONLY_IN_DRAFT = dict(readonly=True, states={'draft': [('readonly', False)]})

    # def _get_planned_week_date(self, cr, uid, ids, fieldname, args, context=None):
    #     result = {}
    #     week_start_day = MO
    #     for seance in self.browse(cr, uid, ids, context=context):
    #         start = datetime.strptime(seance.date_begin, DT_FMT)
    #         start = Timeline.datetime_tz_convert(start, 'UTC',
    #                                              seance.tz or 'UTC')
    #         start = start + relativedelta(weekday=week_start_day(-1))
    #         result[seance.id] = start.date().strftime(D_FMT)
    #     return result

    def name_get(self, cr, uid, ids, context=None):
        result = []
        if isinstance(ids, (int, long)):
            ids = [ids]
        if context is None:
            context = {}

        user_lang = context.get('lang') or self.pool.get('res.users').context_get(cr, uid)['lang']
        user_lang_formats = self.pool.get('res.lang')._lang_date_formats(cr, uid, user_lang)

        for seance in self.browse(cr, uid, ids, context=context):
            if seance.date_begin:
                date = datetime.strptime(seance.date_begin, DT_FMT)
                date = fields.datetime.context_timestamp(cr, uid, date, context=context)
                display_name = '%s (%s - %s)' % (
                    seance.name, date.strftime(user_lang_formats['datetime']),
                    '%d:%02d' % float_to_hm(seance.duration))
            elif seance.planned_week_date:
                date = datetime.strptime(seance.planned_week_date, D_FMT)
                display_name = '%s (%s* - %s)' % (
                    seance.name, date.strftime(user_lang_formats['date']),
                    '%d:%02d' % (float_to_hm(seance.duration)))
            else:
                display_name = '%s' % (seance.name,)
            result.append((seance.id, display_name))
        return result

    def _get_participant_count(self, cr, uid, ids, field_name, args, context=None):
        # force a refresh just before computation
        self._refresh_participations(cr, uid, ids, context=context)
        # return number of participants
        return dict((seance.id, len(seance.participant_ids))
                    for seance in self.browse(cr, uid, ids, context=context))

    def _get_date_end(self, cr, uid, ids, fieldname, args, context=None):
        result = {}
        for seance in self.browse(cr, uid, ids, context=context):
            end = False
            # seance date_begin will be null if generated from preplanning
            # (i.e. we known the planned week, but seance have no fixed date, yet)
            if seance.date_begin:
                start = datetime.strptime(seance.date_begin, DT_FMT)
                end = start + timedelta(hours=seance.duration)
                end = end.strftime(DT_FMT)
            result[seance.id] = end
        return result

    def _store_get_seances_from_seances(self, cr, uid, ids, context=None):
        """return list on seances for participant count refresh"""
        return ids

    def _store_get_seances_from_registrations(self, cr, uid, ids, context=None):
        """retrun list of seances for participant count refresh"""
        event_ids = []
        Registration = self.pool.get('event.registration')
        ids = Registration.search(cr, uid, [('id', 'in', ids), ('state', '!=', 'draft')], context=context)
        for registration in Registration.browse(cr, uid, ids, context=context):
            event_ids.extend(s.id for s in registration.event_id.seance_ids)
        return list(set(event_ids))

    def _store_get_seances_from_participations(self, cr, uid, ids, context=None):
        """return list of seances for participant count refresh"""
        cr.execute("""
            SELECT seance_id
            FROM event_participation
            WHERE id IN %s
        """, (tuple(ids),))
        seance_ids = list(set(_x for (_x,) in cr.fetchall()))
        return list(set(seance_ids))

    def _store_get_seances_from_groups(self, cr, uid, ids, context=None):
        """return list of seances for participant count refresh"""
        registration_ids = []
        Seance = self.pool.get('event.seance')
        ParticipationGroup = self.pool.get('event.participation.group')
        for group in ParticipationGroup.browse(cr, uid, ids, context=context):
            registration_ids.extend(r.id for r in group.registration_ids)
        return Seance._store_get_seances_from_registrations(cr, uid, registration_ids, context=context)

    def _store_get_seances_from_content(self, cr, uid, ids, context=None):
        """return list of seances related to specified contents"""
        Seance = self.pool.get('event.seance')
        return Seance.search(cr, uid, [('content_id', 'in', ids)], context=context)

    def _get_resources_ok(self, cr, uid, ids, fieldname, args, context=None):
        result = {}
        for seance in self.browse(cr, uid, ids, context=context):
            result[seance.id] = r = {}
            room_required = seance.type_id.room_required if seance.type_id else True
            min_speaker = seance.type_id.speaker_min_required if seance.type_id else 1

            # Room
            room_confirmed_part = [p.id for p in seance.resource_participation_ids
                                   if p.role == 'room' and p.state == 'confirm']
            r['room_ok'] = len(room_confirmed_part) >= 1 if room_required else True

            # Speakers
            speaker_confirmed_part = [p.id for p in seance.resource_participation_ids
                                      if p.role == 'speaker' and p.state == 'confirm']
            r['speakers_ok'] = len(speaker_confirmed_part) >= min_speaker

            # Equipment
            # TODO: implement this (add fields on seance, etc...)
            r['equipments_ok'] = True
        return result

    def _get_event_conflicts(self, cr, uid, ids, fieldname, args, context=None):
        if not ids:
            return {}
        CoreCalendarEvent = self.pool.get('core.calendar.event')
        conflicts_method = CoreCalendarEvent._get_user_overlapping_events
        result = {}
        for _id in ids:
            result[_id] = []
        for conflict in conflicts_method(cr, uid, [(self._name, ids)], context=context):
            result[conflict['res_id']] = conflict['overlapping_event_ids'].keys()
        return result

    def _search_event_conflicts(self, cr, uid, model, fieldname, domain, context=None):
        search_in_conflicts = None
        for a in domain:
            if isinstance(a, (list, tuple)) and len(a) == 3 and a[0] == fieldname:
                if a[1] == '!=' and a[2] is False:
                    search_in_conflicts = True
                    break
        if search_in_conflicts is None:
            return []
        CoreCalendarEvent = self.pool.get('core.calendar.event')
        conflicts_method = CoreCalendarEvent._get_user_overlapping_events
        ids = [x['res_id'] for x in conflicts_method(cr, uid, [(self._name, False)], context=context)]
        return [('id', 'in', ids)]

    def _needaction_domain_get(self, cr, uid, context=None):
        return False
        # return [('event_conflict_ids','!=',False)]

    CONTENT_RELATED_STORE = {
        'event.content': (_store_get_seances_from_content, ['name', 'lang_id', 'module_id', 'type_id'], 10),
        'event.seance': (_store_get_seances_from_seances, ['content_id'], 10),
    }

    _columns = {
        'content_id': fields.many2one('event.content', 'Content', required=True, ondelete='cascade',
                                      **WRITABLE_ONLY_IN_DRAFT),
        # Content's related fields
        'name': fields.related('content_id', 'name', type='char', string='Seance Name',
                               readonly=True, required=True, store=CONTENT_RELATED_STORE),
        'lang_id': fields.related('content_id', 'lang_id', type='many2one',
                                  relation='res.lang', string='Language',
                                  readonly=True, store=CONTENT_RELATED_STORE),
        'event_ids': fields.related('content_id', 'event_ids', type='many2many',
                                    relation='event.event', string='Events',
                                    readonly=True),
        'module_id': fields.related('content_id', 'module_id', type='many2one',
                                    relation='event.content.module', string='Module',
                                    readonly=True, store=CONTENT_RELATED_STORE),
        'content_divided': fields.related('content_id', 'is_divided', type='boolean',
                                          string='Divided', readonly=True,
                                          store=CONTENT_RELATED_STORE),
        'type_id': fields.related('content_id', 'type_id', type='many2one',
                                  relation='event.seance.type', string='Type',
                                  readonly=True, store=CONTENT_RELATED_STORE),

        'date_begin': fields.datetime('Begin date', readonly=True,
                                      states=dict((st, [('readonly', not bool(st == 'draft')),
                                                        ('required', not bool(st == 'draft'))])
                                                   for st, sn in SEANCE_STATES)
                                      ),
        'date_end': fields.function(_get_date_end, type='datetime', string='End date', readonly=True, store=True),
        'duration': fields.float('Duration', required=True,
                                  states=dict((st, [('readonly', not bool(st == 'draft'))])
                                              for st, sn in SEANCE_STATES)),
        # 'planned_week_date': fields.function(_get_planned_week_date, string='Planned Week date',
        #                                      type='date', readonly=True, store=True, groupby_range='week'),
        'planned_week_date': fields.date('Planned Week Date', readonly=True, groupby_range='week'),
        'tz': fields.selection(_tz_get, size=64, string='Timezone'),
        'participant_min': fields.integer('Participant Min'),
        'participant_max': fields.integer('Participant Max'),
        'main_speaker_id': fields.many2one('res.partner', 'Main Speaker', select=True),
        'address_id': fields.many2one('res.partner', 'Address', select=True),
        'other_resource_ids': fields.many2many('res.partner', 'event_seance_other_resources_rel',
                                               id1='seance_id', id2='partner_id', string='Other resources',
                                               **WRITABLE_ONLY_IN_DRAFT),
        'group_id': fields.many2one('event.participation.group', 'Group',
                                    **WRITABLE_ONLY_IN_DRAFT),
        'resource_participation_ids': fields.one2many('event.participation', 'seance_id', 'Resource Participation',
                                                      domain=[('role', '!=', 'participant')]),
        'participant_ids': fields.one2many('event.participation', 'seance_id', 'Participants',
                                           domain=[('role', '=', 'participant')]),
        'participant_count': fields.function(_get_participant_count, type='integer', string='# of participants',
                                             store={
                                                 'event.seance': (_store_get_seances_from_seances, ['content_id', 'group_id', 'state'], 10),
                                                 'event.participation': (_store_get_seances_from_participations, ['seance_id'], 10),
                                                 'event.registration': (_store_get_seances_from_registrations, ['group_ids', 'state'], 10),
                                                 'event.participation.group': (_store_get_seances_from_groups, ['registration_ids'], 10),
                                                 'event.content': (_store_get_seances_from_content, ['is_divided'], 10),
                                             }),
        'speakers_ok': fields.function(_get_resources_ok, string='Speakers Confirmed', type='boolean', multi='resources-ok'),
        'room_ok': fields.function(_get_resources_ok, string='Room Confirmed', type='boolean', multi='resources-ok'),
        'equipments_ok': fields.function(_get_resources_ok, string='Equipment Confirmed', type='boolean', multi='resources-ok'),
        'constraint_ids': fields.many2many('event.constraint', id1='seance_id', id2='constraint_id', string='Constraints'),
        'state': fields.selection(SEANCE_STATES, 'State', readonly=True, required=True),
        'event_conflict_ids': fields.function(_get_event_conflicts, type='one2many',
                                               relation='core.calendar.event', readonly=True,
                                               fnct_search=_search_event_conflicts),
    }

    _defaults = {
        'state': 'draft',
    }

    def _check_content_group_ref(self, cr, uid, ids, context=None):
        """enforce presence of 'group' if linked content is 'divided'"""
        for seance in self.browse(cr, uid, ids, context=context):
            if seance.content_id.is_divided and not seance.group_id:
                return False
        return True

    _constraints = [
        (_check_content_group_ref, 'You have to specify a group for divided content', ['group_id']),
    ]

    _sql_constraints = [
        ('date_begin_notnull', "CHECK(CASE WHEN state != 'draft' THEN date_begin IS NOT NULL ELSE True END)",
            'You have to specify a begin date when leaving the draft state'),
    ]

    def _cron_auto_terminate_seance(self, cr, uid, context=None):
        reference_date = time.strftime(DT_FMT)
        seance_to_terminate = self.search(cr, uid, [
            ('date_end', '<', reference_date),
            ('state', 'in', ['confirm', 'inprogress', 'closed'])
        ])
        self.button_set_done(cr, uid, seance_to_terminate, context=context)

    def create(self, cr, uid, values, context=None):
        new_record_id = super(EventSeance, self).create(cr, uid, values, context=context)
        self._refresh_resource_participations(cr, uid, [new_record_id], context=context)
        return new_record_id

    def write(self, cr, uid, ids, values, context=None):
        retval = super(EventSeance, self).write(cr, uid, ids, values, context=context)
        if 'duration' in values or 'date_begin' in values:
            for seance in self.browse(cr, uid, ids, context=context):
                if seance.state != 'draft':
                    raise osv.except_osv(
                        _('Error!'),
                        _('You could only modify seance duration or begin date on draft seance'))
        resource_related_fields_set = set(self._get_resource_related_fields(cr, uid, context=context))
        if resource_related_fields_set & set(values.keys()):
            self._refresh_resource_participations(cr, uid, ids, context=context)
        return retval

    def unlink(self, cr, uid, ids, context=None):
        for seance in self.read(cr, uid, ids, ['state'], context=context):
            if seance['state'] not in ('draft', 'cancel'):
                raise osv.except_osv(
                    _('Error!'),
                    _("You can only delete seances which are 'draft' or 'cancel'"))
        return super(EventSeance, self).unlink(cr, uid, ids, context=context)

    def onchange_content_id(self, cr, uid, ids, content_id, context=None):
        ocv = {}
        ocv.setdefault('value', {})
        if content_id:
            content_obj = self.pool.get('event.content')
            content = content_obj.browse(cr, uid, content_id, context=context)
            ocv['value'].update(
                name=content.name,
                type_id=content.type_id.id,
                lang_id=content.lang_id.id,
                content_divided=content.is_divided,
                course_id=content.course_id.id,
                module_id=content.module_id.id,
                group_id=content.group_ids[0].id if content.is_divided else False)
        else:
            ocv['value']['group_id'] = False
        return ocv

    def onchange_seance_type(self, cr, uid, ids, type_id, context=None):
        values = {}
        return {'value': values}

    def button_set_draft(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'draft'}, context=context)

    def button_set_planned(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'planned'}, context=context)

    def button_set_confirm(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'confirm'}, context=context)

    def button_set_inprogress(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'inprogress'}, context=context)

    def button_set_closed(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'closed'}, context=context)

    def button_set_done(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'done'}, context=context)

    def _get_resource_related_fields(self, cr, uid, context=None):
        return ['main_speaker_id', 'address_id', 'other_resource_ids']

    def _refresh_resource_participations(self, cr, uid, ids, context=None):
        Paricipation = self.pool.get('event.participation')

        for seance in self.browse(cr, uid, ids, context=context):
            resources = set()
            if seance.address_id:
                resources.add(('room', seance.address_id))
            if seance.main_speaker_id:
                resources.add(('speaker', seance.main_speaker_id))
            for p in seance.other_resource_ids:
                roles = [r for r in ['speaker', 'room', 'equipment'] if p[r]]
                if not roles:
                    continue
                resources.add((roles[0], p))

            # computed diff from existing resource assignment
            changes = []
            for participation in seance.resource_participation_ids:
                key = (participation.role, participation.partner_id)
                if key in resources:
                    # TODO: check that price & other values are in sync
                    resources.remove(key)
                else:
                    # assignment not-need, remove it.
                    changes.append((2, participation.id))

            # create missing assignments
            for role, partner in resources:
                changes.append((0, 0, {
                    'role': role,
                    'partner_id': partner.id,
                    'name': partner.name,
                }))

            if changes:
                seance.write({'resource_participation_ids': changes})
            pass

    def _refresh_participations(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if context.get('__internal_refresh_participations'):
            return True
        context['__internal_refresh_participations'] = True
        Registration = self.pool.get('event.registration')
        Participation = self.pool.get('event.participation')
        # Registration = self.pool.get('event.registration')
        p_to_unlink = []  # participation ids to unlink
        p_to_create = defaultdict(list)  # {registration_id: [p1, p2, ...]}
        ids = list(set(ids))

        for seance in self.browse(cr, uid, ids, context=context):
            # print(">>> refreshing participation for seance '%s' [%d]" % (seance.name, seance.id,))
            # registrations = Registration.browse(cr, uid, regids_cache[seance.id], context=context)
            if seance.type_id and seance.type_id.manual_participation:
                continue
            registrations = []
            for event in seance.content_id.event_ids:
                if seance.state == 'done':
                    # done seance have to keep all participation for history tracking
                    registrations.extend(r for r in event.registration_ids)
                    continue
                for reg in event.registration_ids:
                    if reg.state in ('open', 'done'):
                        if seance.group_id:
                            if seance.group_id in reg.group_ids:
                                registrations.append(reg)
                        else:
                            registrations.append(reg)

            partset = {}  # { (registration, contact): list_counted([p1, p2, ...]), ...}
            # build participation set on expected values
            for reg in registrations:
                # TODO: re-add support for named contact ids ('contact_ids' field)
                anon_count = reg.nb_register
                partset[(reg, False)] = list_counted(expected=anon_count)
            # populate set with existing participation values
            for part in seance.participant_ids:
                x = (part.registration_id, False)
                partset.setdefault(x, list_counted(expected=0)).append(part)
            # iterate over the set and compare result (expected vs real)
            for k, v in sorted(partset.iteritems()):
                reg, contact = k
                found, expected = len(v), v.expected
                # print(">>> %s" % (k,))
                # print("--- found %d/%d: %s" % (found, expected, v,))
                if found > expected:
                    if seance.state != 'done':
                        p_to_unlink.extend(p.id for p in v[-found-expected:])
                elif found < expected:
                    if seance.state == 'done':
                        continue
                    for i in xrange(expected-found):
                        if contact:
                            part_name = contact.name
                        elif expected == 1:
                            part_name = '%s' % (reg.name or reg.partner_id.name or '',)
                        else:
                            part_name = '%s #%d' % (reg.name or reg.partner_id.name or '', i+1)
                        part_values = self._prepare_participation_for_seance(cr, uid, part_name, seance,
                                                                             reg, context=context)
                        registration_id = part_values['registration_id']
                        p_to_create[registration_id].append((0, 0, part_values))
        if p_to_unlink:
            Participation.unlink(cr, uid, p_to_unlink, context=context)
        for registration_id, commands in p_to_create.iteritems():
            Registration.write(cr, uid, [registration_id], {
                'participation_ids': commands,
            }, context=context)
        return True

    def _prepare_participation_for_seance(self, cr, uid, name, seance, registration, context=None):
        """Prepare participation dict suitable for create
        :param cr: database cursor
        :param uid: current user id
        :param name: string used for participant name
        :param seance: browse_record instance of event.seance object
        :param registration: browse_record instance of event.registration object
        :param context: dict representing current context
        """
        return {
            'name': name,
            'partner_id': registration.partner_id.id,
            'seance_id': seance.id,
            'registration_id': registration.id,
        }


class EventParticipation(osv.Model):
    """ Event Participation """
    _name = 'event.participation'
    _description = __doc__
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    PRESENCE_STATUS = [
        ('none', 'No Presence Information'),
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('absent_justified', 'Absent (Justified)'),
        ('late', 'Late'),
        ('late_justified', 'Late (Justified)'),
    ]

    STATES = [
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ]

    ROLES = [
        ('participant', 'Participant'),
        ('speaker', 'Speaker'),
        ('room', 'Room'),
        ('equipment', 'Equipment'),
    ]

    def _get_presence_summary(self, cr, uid, ids, fieldname, args, context=None):
        fields = self.fields_get(cr, uid, ['presence'], context=context)
        presence_states = dict(fields['presence']['selection'])
        result = {}
        for participation in self.browse(cr, uid, ids, context=context):
            summary = presence_states[participation.presence]
            if participation.presence == 'late':
                arrival = datetime.strptime(participation.arrival_time, DT_FMT)
                event_begin = datetime.strptime(participation.seance_id.date_begin, DT_FMT)
                delta = relativedelta(arrival, event_begin)
                summary += u' (%d:%02d)' % (delta.hours, delta.minutes)
            result[participation.id] = summary
        return result

    def _compute_purchase_price(self, cr, uid, ids, fieldname, args, context=None):
        if not ids:
            return {}
        if context is None:
            context = {}
        Course = self.pool.get('event.course')
        result = dict.fromkeys(ids, 0.0)
        ids = self.search(cr, uid, [('id', 'in', ids), ('role', '!=', 'participant')], context=context)
        resource_price_cache = {}
        for p in self.browse(cr, uid, ids, context=context):
            if p.purchase_product_id:
                resource_price = p.purchase_product_id.standard_price
                if p.seance_id.course_id:
                    key = (p.partner_id.id, p.seance_id.course_id)
                    course_price = resource_price_cache.get(key)
                    if course_price is None:
                        # speaker's course price have priority over product's puchase price (standard_price)
                        ctx = dict(context, partner_id=p.partner_id.id)
                        course = Course.browse(cr, uid, p.seance_id.course_id.id, context=ctx)
                        course_price = course.price
                        resource_price_cache[key] = course_price
                    resource_price = course_price
                result[p.id] = resource_price
        return result

    def _compute_purchase_product(self, cr, uid, ids, fieldname, args, context=None):
        if not ids:
            return {}
        if context is None:
            context = {}
        # TODO: get and use cached partner -> product mapping
        Employee = self.pool.get('hr.employee')
        get_product_from_employee_product = Employee and 'product_id' in Employee._all_columns

        result = {}
        ids = self.search(cr, uid, [('id', 'in', ids), ('role', '!=', 'participant')], context=context)
        for p in self.browse(cr, uid, ids, context=context):
            product_id = False
            if p.partner_id.external:
                if p.seance_id.type_id:
                    seance_type_product = p.seance_id.type_id[p.role + '_product_id']
                    if seance_type_product:
                        product_id = seance_type_product.id
            # try getting product from related employee (only for 'internal' resource)
            elif get_product_from_employee_product and p.role == 'speaker':
                for user in p.partner_id.user_ids:
                    for employee in user.employee_ids:
                        if employee.product_id:
                            product_id = employee.product_id.id
                            break
            result[p.id] = product_id
        return result

    def _compute_purchase_amount(self, cr, uid, ids, fieldname, args, context=None):
        ModelData = self.pool.get('ir.model.data')
        _m, hour_uom = ModelData.get_object_reference(cr, uid, 'product', 'product_uom_hour')

        result = {}
        for p in self.browse(cr, uid, ids, context=context):
            result[p.id] = {
                'purchase_qty': p.seance_id.duration,
                'purchase_subtotal': p.purchase_price * p.seance_id.duration,
            }
        return result

    _columns = {
        'name': fields.char('Participant Name', size=128, required=True),
        'role': fields.selection(ROLES, 'Role', required=True, select=True),
        'partner_id': fields.many2one('res.partner', 'Participant', select=True),
        'seance_id': fields.many2one('event.seance', 'Seance', required=True, ondelete='cascade', select=True),
        'seance_date': fields.related('seance_id', 'date_begin', type='datetime', string='Seance Date', readonly=True),
        'seance_event_ids': fields.related('seance_id', 'event_ids', type='many2many', relation='event.event', readonly=True, string='Events'),
        'date': fields.related('seance_id', 'date_begin', type='datetime', string='Date', readonly=True),
        'duration': fields.related('seance_id', 'duration', type='float', string='Duration', readonly=True),
        'registration_id': fields.many2one('event.registration', 'Registration', required=False,
                                           states=dict((s[0], [('required', True),('readonly', s[0] != 'draft')]) for s in STATES)),
        'state': fields.selection(STATES, 'State', readonly=True, required=True),
        # Presence Information
        'presence': fields.selection(PRESENCE_STATUS, 'Presence', required=True),
        'presence_summary': fields.function(_get_presence_summary, type='char',
                                            string='Presence Summary'),
        'arrival_time': fields.datetime('Arrival Time'),
        'departure_time': fields.datetime('Departure Time'),
        'purchase_product_id': fields.function(_compute_purchase_product, string='Purchase Product',
                                               type='many2one', relation='product.product'),
        'purchase_price': fields.function(_compute_purchase_price, string='Purchase Price', type='float',
                                          digits_compute=dp.get_precision('Product Price')),
        'purchase_qty': fields.function(_compute_purchase_amount, type='float',
                                        string='Quantity', multi='purchase-amount',
                                        digits_compute=dp.get_precision('Purchase Price')),
        'purchase_subtotal': fields.function(_compute_purchase_amount, type='float',
                                             string='Total', multi='purchase-amout',
                                             digits_compute=dp.get_precision('Account')),
    }

    _defaults = {
        'state': 'draft',
        'presence': 'none',
        'role': 'participant',
    }

    _sql_constraints = [
        ('participant_registration_required',
            "CHECK(CASE WHEN role = 'participant' THEN registration_id IS NOT NULL ELSE True END)",
            "Registration is required for participant's participations"),
    ]

    def create(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        # Do not log participation creation or subscribe user who create the participation
        ctx = dict(context, mail_create_nolog=True, mail_create_nosubscribe=True)
        new_participation_id = super(EventParticipation, self).create(cr, uid, values, context=ctx)
        new_participation = self.browse(cr, uid, new_participation_id, context=context)
        if new_participation.role == 'participant' \
            or (new_participation.partner_id
                and new_participation.partner_id.event_assignment_mode == 'automatic'):
            self.button_set_confirm(cr, uid, [new_participation_id], context=context)
        return new_participation_id

    def unlink(self, cr, uid, ids, context=None):
        # Automatically cancel
        auto_cancel_participation_ids = self.search(cr, uid, [
            '&', ('id', 'in', ids),
            '&', ('state', '!=', 'cancel'),
            '|', ('role', '=', 'participant'),
                 '&', ('role', '!=', 'participant'),
                      ('partner_id.event_assignment_mode', '=', 'automatic'),
        ], context=context)
        if auto_cancel_participation_ids:
            self.button_set_cancel(cr, uid, auto_cancel_participation_ids, context=context)

        participation_not_draft_not_cancel = self.search(cr, uid, [
            ('id', 'in', ids),
            ('state', 'not in', ['draft', 'cancel'])
        ], context=context)
        if participation_not_draft_not_cancel:
            raise osv.except_osv(
                _('Error!'),
                _('Only draft and cancelled participation can be unlinked. '
                  'Check that there is no manual resource assignment, that '
                  'should be cancelled manually.'))
        return super(EventParticipation, self).unlink(cr, uid, ids, context=context)

    def _take_presence(self, cr, uid, ids, presence, context=None):
        if not ids:
            return False
        if context is None:
            context = {}

        print("%s / presence: %s, context: %s" % (ids, presence, context,))
        if presence == 'late' and not context.get('presence_arrival_time'):
            raise osv.except_osv(_('Error!'),
                                 _('No Presence Arrival & Departure Provided'))

        Seance = self.pool.get('event.seance')
        # Group participations by seance so we write() once per seance
        parts_by_seance = defaultdict(list)
        for part in self.read(cr, uid, ids, ['seance_id'], context=context):
            seance_id = part['seance_id'][0]
            parts_by_seance[seance_id].append(part['id'])

        for seance in Seance.browse(cr, uid, parts_by_seance.keys(), context=context):
            participation_ids = parts_by_seance[seance.id]
            values = {'presence': presence}
            if presence in ['none', 'absent']:
                values.update(arrival_time=False, departure_time=False)
            elif presence == 'present':
                values.update(arrival_time=seance.date_begin,
                              departure_time=seance.date_end)
            elif presence == 'late':
                arrival = context.get('presence_arrival_time')
                if not (seance.date_begin <= arrival <= seance.date_end):
                    arrival = seance.date_begin
                departure = context.get('presence_departure_time')
                if not (seance.date_begin <= departure <= seance.date_end):
                    departure = seance.date_end
                values.update(arrival_time=arrival, departure_time=departure)
            self.write(cr, uid, participation_ids, values, context=context)
        return True

    def button_take_presence(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not context.get('presence'):
            raise osv.except_osv(_('Error!'),
                                 _('No Presence Value Found'))
        return self._take_presence(cr, uid, ids, context['presence'], context=context)

    def button_set_draft(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'draft'}, context=context)

    def button_set_confirm(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'confirm'}, context=context)

    def button_set_done(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'done'}, context=context)

    def button_set_cancel(self, cr, uid, ids, context=None):
        for p in self.browse(cr, uid, ids, context=context):
            if p.seance_id.state == 'done':
                print("%d: %s, %s %s" % (p.id, p.name, p.seance_id.name, p.seance_id.state,))
                raise osv.except_osv(_('Error!'),
                                     _('OpenERP can not delete participations which are related to a done seance'))
        return self.write(cr, uid, ids, {'state': 'cancel'}, context=context)


    # Workaround shitty bug in when client (taking context of 1st button with same name)
    button_take_presence_2 = button_take_presence

    def onchange_partner(self, cr, uid, ids, partner_id, context=None):
        values = {}
        if partner_id:
            Partner = self.pool.get('res.partner')
            values['name'] = Partner.browse(cr, uid, partner_id, context=context).name
        return {'value': values}

    def onchange_registration(self, cr, uid, ids, registration_id, context=None):
        values = {}
        if registration_id:
            Registration = self.pool.get('event.registration')
            reg = Registration.browse(cr, uid, registration_id, context=context)
            values.update(partner_id=reg.partner_id.id)
        return {'value': values}

    def onchange_seance(self, cr, uid, ids, seance_id, context=None):
        values = {}
        return {'value': values}


class EventParticipationGroup(osv.Model):
    _name = 'event.participation.group'
    _order = 'is_default DESC, name'

    def _get_participant_count(self, cr, uid, ids, field_name, args, context=None):
        result = {}
        for group in self.browse(cr, uid, ids, context=context):
            events = group.event_content_id.event_ids
            total = 0
            if events:
                total = sum(event.register_current + event.register_prospect
                            for event in events)
            count = sum([reg.nb_register for reg in group.registration_ids])
            result[group.id] = _('%d / %d') % (count, total)
        return result

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        result = []
        show_content_name = bool(context.get('show_content_name'))
        for group in self.browse(cr, uid, ids, context=context):
            if show_content_name:
                repr_name = '%s / %s' % (group.event_content_id.name, group.name)
            else:
                repr_name = group.name
            result.append((group.id, repr_name,))
        return result

    _columns = {
        'name': fields.char('Group name', required=True),
        'event_content_id': fields.many2one('event.content', 'Content', required=True, ondelete='cascade'),
        'is_default': fields.boolean('Is default?'),
        'speaker_id': fields.many2one('res.partner', 'Speaker', help='Default speaker assigned to seances of this group'),
        'room_id': fields.many2one('res.partner', 'Address', help='Default location assigned to seances of this group'),
        'participant_count': fields.function(_get_participant_count, type='char', string='# of participants'),
        'registration_ids': fields.many2many('event.registration', 'event_registration_participation_group_rel',
                                             string='Registrations', id1='group_id', id2='registration_id'),
    }

    def copy_data(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default['registration_ids'] = None
        return super(EventParticipationGroup, self).copy_data(cr, uid, id, default=default, context=context)

    def search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        if context.get('group_for_content_id'):
            group_for_content = [('event_content_id', '=', context['group_for_content_id'])]
            if args:
                group_for_content = ['&'] + group_for_content
            args = group_for_content + args
        return super(EventParticipationGroup, self).search(cr, user, args, offset=offset, limit=limit,
                                                           order=order, context=context, count=count)

    def create(self, cr, uid, values, context=None):
        content_id = values.get('event_content_id')
        if content_id:
            content = self.pool.get('event.content').browse(cr, uid, content_id, context=context)
            event_ids = content.event_ids
            if event_ids and any(e.state not in ['draft', 'template'] for e in event_ids):
                raise osv.except_osv(_('Error'), _('You can only add new content group on template and draft events'))
        return super(EventParticipationGroup, self).create(cr, uid, values, context=context)

    def write(self, cr, uid, ids, values, context=None):
        if 'registration_ids' in values:
            for group in self.browse(cr, uid, ids, context=context):
                if group.event_content_id.event_id.state == 'done':
                    raise osv.except_osv(_('Error'), _('You cannot change content group subscription on done events'))
        return super(EventParticipationGroup, self).write(cr, uid, ids, values, context=context)

    def unlink(self, cr, uid, ids, context=None):
        content_ids = []
        for group in self.browse(cr, uid, ids, context=context):
            if all(e.state != 'draft' for e in group.event_content_id.event_ids):
                raise osv.except_osv(_('Error'), _('You can only remove a new content group on draft events'))
            content_ids.append(group.event_content_id.id)
        if content_ids:
            Registration = self.pool.get('event.registration')
            registration_ids = Registration.search(cr, uid, [('event_id.content_ids', 'in', content_ids), ('state', '!=', 'done')], context=context)
            Registration._update_registration_groups(cr, uid, registration_ids, context=context)
        return super(EventParticipationGroup, self).unlink(cr, uid, ids, context=context)

    def default_get(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        # detect there is another group has 'is_default' active,
        # if not, activate it.
        if 'current_group_ids' in context:
            content_obj = self.pool.get('event.content')
            current_group_ids = context.get('current_group_ids') or []
            current_group_ids = content_obj.resolve_2many_commands(cr, uid, 'group_ids', current_group_ids,
                                                                   fields=['is_default'], context=context)
            if not any(g['is_default'] for g in current_group_ids):
                context = dict(context, default_is_default=True)
        return super(EventParticipationGroup, self).default_get(cr, uid, fields_list, context=context)


class EventType(osv.Model):
    _inherit = 'event.type'

    def _get_selection_content_planifications(self, cr, uid, context=None):
        Event = self.pool.get('event.event')
        fields = Event.fields_get(cr, uid, ['content_planification'], context=context)
        return fields['content_planification']['selection']

    _columns = {
        'default_has_program': fields.boolean('Has program', help='Does this type of event always has a program'),
        'default_content_planification': fields.selection(_get_selection_content_planifications, 'Content planification mode',
                                                          help='Define mode used for created seance of this event'),
    }

    _defaults = {
        'default_content_planification': 'linear',
    }


class EventEvent(osv.Model):
    _name = 'event.event'
    _inherit = ['event.event', 'core.calendar.timeline']

    def _get_seance_ids(self, cr, uid, ids, fieldname, args, context=None):
        Seance = self.pool.get('event.seance')
        seance_ids = Seance.search(cr, uid, [('content_id.event_ids', 'in', ids)])

        result = defaultdict(list)
        event_ids_set = set(ids)
        for seance in Seance.browse(cr, uid, seance_ids, context=context):
            for event in seance.event_ids:
                if event.id in event_ids_set:
                    result[event.id].append(seance.id)
        return result

    def _estimate_end_date(self, cr, uid, start, contents, timeline=None, context=None):
        """Estimated event duration based on start date and contents length
        :param cr: database cursor
        :param uid: current user id
        :param start: start date (datetime or string representing a date)
        :param contents: list of dict representing the content
        :param timeline: a Timeline object
        :param context: dict representing the current context
        """
        # adjust default start, end dates
        if isinstance(start, basestring):
            start = datetime.strptime(start, DT_FMT)
        end = start.replace()

        if not contents:
            return end.strftime(DT_FMT)

        # iter on each timeline change, and eat all "available" time
        if not timeline:
            raise NotImplementedError('No timeline specified, this is currently unsupported')
        tlstart = start
        tlend = datetime.max - timedelta(days=1)
        available_periods = (p for p in timeline.iterperiods(as_tz='UTC',
                                                             start=tlstart, end=tlend)
                             if p.status == Availibility.FREE).__iter__()

        period = None
        for content in contents:
            remaining_duration = content['duration']
            content_allow_splitting = True  # TODO: allow user to change
            while remaining_duration > 0:
                try:
                    period = period or available_periods.next()
                except StopIteration as e:
                    raise osv.except_osv(_('Error!'),
                                         _('No enough time to schedule all content "%s"') % (content.name,))
                if period.duration < content.slot_duration and not content_allow_splitting:
                    # remaining period is too small, get the next one
                    period = None
                    continue
                alloc_duration = min(content.slot_duration, remaining_duration, period.duration)
                (s, e) = period.shift_hours(alloc_duration)
                remaining_duration -= alloc_duration
                end = e
        return end.strftime(DT_FMT)

    def _get_date_end(self, cr, uid, ids, fieldname, args, context=None):
        result = {}
        if not ids:
            return result

        # Fetch stored value
        cr.execute("""SELECT id, date_end
                      FROM event_event WHERE id in %s""",
                   (tuple(ids),))
        stored_values = dict(cr.fetchall())

        for event in self.browse(cr, uid, ids, context=context):
            if event.has_program:
                Seance = self.pool.get('event.seance')
                event_begin = datetime.strptime(event.date_begin, DT_FMT)
                event_end = datetime.max - timedelta(days=1)

                ed = event.date_begin

                timeline = None
                if event.content_ids:
                    tmlayers = ['working_hours', 'leaves']
                    timeline = self._get_resource_timeline(cr, uid, event.id, layers=tmlayers,
                                                           date_from=event_begin, date_to=event_end,
                                                           context=context)

                ed = self._estimate_end_date(cr, uid, event.date_begin, event.content_ids,
                                             timeline=timeline, context=context)

                # search max seance date
                current_seance_filter = [
                    ('content_id.event_ids', 'in', [event.id]),
                    ('state', '!=', 'cancelled'),
                ]
                last_seance_ids = Seance.search(cr, uid, current_seance_filter,
                                                order='date_begin DESC', limit=1)
                if last_seance_ids:
                    seance = Seance.browse(cr, uid, last_seance_ids[0], context=context)
                    ed = max(ed, seance.date_end)

            else:
                ed = stored_values[event.id]
            if not ed:
                # fallback to ensure we have a correct date
                ed = event.date_begin
            result[event.id] = ed
        return result

    def _set_date_end(self, cr, uid, ids, fieldname, value, args, context=None):
        if not ids:
            return False
        if isinstance(ids, (int, long)):
            ids = [ids]
        cr.execute("UPDATE event_event SET date_end = %s WHERE id IN %s",
                   (value, tuple(ids),))
        return True

    def _store_get_events_from_events(self, cr, uid, ids, context=None):
        return ids

    def _store_get_events_from_contents(self, cr, uid, ids, context=None):
        Event = self.pool.get('event.event')
        content_domain = [('content_ids', 'in', ids)]
        return Event.search(cr, uid, content_domain, context=context)

    def _store_get_events_from_seances(self, cr, uid, ids, context=None):
        Event = self.pool.get('event.event')
        cr.execute("""
            SELECT content_id
            FROM event_seance
            WHERE id IN %s
        """, (tuple(ids),))
        content_ids = list(set(_x for (_x,) in cr.fetchall()))
        return Event._store_get_events_from_contents(cr, uid, content_ids, context=context)

    _columns = {
        'calendar_id': fields.many2one('resource.calendar', 'Hours'),
        'has_program': fields.boolean('Program', help='This event has a program'),
        'content_ids': fields.many2many('event.content', 'event_content_link',
                                        id1='event_id', id2='content_id',
                                        string='Contents'),
        'content_planification': fields.selection([
            ('linear', 'Linear'),
            ('preplanning', 'Preplanning')],
            'Content Planification', required=True,
            help='Define mode used for created seance of this event'),
        'seance_ids': fields.function(_get_seance_ids, type='many2many',
                                      relation='event.seance', readonly=True,
                                      string='Seances'),
        'date_end': fields.function(_get_date_end, type='datetime', string='End Date',
                                    required=False, readonly=True, states={'draft': [('readonly', False)]},
                                    fnct_inv=_set_date_end, store={
                                        'event.event': (_store_get_events_from_events, ['date_begin', 'content_ids', 'has_program'], 10),
                                        'event.content': (_store_get_events_from_contents, [], 10),
                                        'event.seance': (_store_get_events_from_seances, [], 10),
                                    }),
    }

    _defaults = {
        'content_planification': 'linear',
    }

    def _check_closing_date(self, cr, uid, ids, context=None):
        for event in self.browse(cr, uid, ids, context=context):
            if event.has_program:
                # for program end date is computed automatically by a stored
                # function fields - and ensure that date_end will be >= date_begin
                continue
            if event.date_end < event.date_begin:
                return False
        return True

    def copy_data(self, cr, uid, id, default=None, context=None):
        """ Reset the state and the registrations while copying an event
        """
        if default is None:
            default = {}
        default.update(content_ids=False, seance_ids=False)
        return super(EventEvent, self).copy_data(cr, uid, id, default=default, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        Content = self.pool.get('event.content')
        new_event_id = super(EventEvent, self).copy(cr, uid, id, context=context)
        event = self.browse(cr, uid, id, context=context)
        new_event = self.browse(cr, uid, new_event_id, context=context)
        if new_event.has_program:
            contents = []
            for content_template in event.content_ids:
                data = Content.copy_data(cr, uid, content_template.id, context=context)
                contents.append((0, 0, data))
            new_event.write({'content_ids': contents})
        # Recompute seances (content_planification == 'linear')
        self.recompute_seances(cr, uid, [new_event_id], context=context)
        return new_event_id

    def write(self, cr, uid, ids, values, context=None):
        content_ids_to_check = set()
        if 'content_ids' in values:
            for event in self.read(cr, uid, ids, ['content_ids'], context=context):
                content_ids_to_check |= set(event['content_ids'])
        result = super(EventEvent, self).write(cr, uid, ids, values, context=context)
        if 'content_ids' in values:
            for event in self.read(cr, uid, ids, ['content_ids'], context=context):
                content_ids_to_check |= set(event['content_ids'])
            Content = self.pool.get('event.content')
            Content.unlink_isolated_content(cr, uid, content_ids_to_check, context=context)
        return result

    def unlink(self, cr, uid, ids, context=None):
        content_ids_to_check = set()
        for event in self.read(cr, uid, ids, ['content_ids'], context=context):
            content_ids_to_check |= set(event['content_ids'])
        result = super(EventEvent, self).unlink(cr, uid, ids, context=context)
        if content_ids_to_check:
            Content = self.pool.get('event.content')
            Content.unlink_isolated_content(cr, uid, content_ids_to_check, context=context)
        return result

    def onchange_event_type(self, cr, uid, ids, type_event, context=None):
        values = super(EventEvent, self).onchange_event_type(cr, uid, ids, type_event, context=context)
        if type_event:
            Type = self.pool.get('event.type')
            type_info = Type.browse(cr, uid, type_event, context)
            values['value'].update(
                has_program=type_info.default_has_program,
                content_planification=type_info.default_content_planification)
        return values

    def _duplicate_template(self, cr, uid, template_id, context=None):
        Content = self.pool.get('event.content')
        new_event_id = super(EventEvent, self)._duplicate_template(cr, uid, template_id, context=context)
        template = self.browse(cr, uid, template_id, context=context)
        new_event = self.browse(cr, uid, new_event_id, context=context)
        if new_event.has_program:
            contents = []
            for content_template in template.content_ids:
                data = Content.copy_data(cr, uid, content_template.id, context=context)
                contents.append((0, 0, data))
            new_event.write({'content_ids': contents})
        # Recompute seances (content_planification == 'linear')
        self.recompute_seances(cr, uid, [new_event_id], context=context)
        return new_event_id

    def button_set_template(self, cr, uid, ids, context=None):
        for event in self.browse(cr, uid, ids, context=context):
            has_shared_content = any(len(c.event_ids) > 1
                                     for c in event.content_ids)
            has_seances = len(event.seance_ids) > 0
            if has_shared_content or has_seances:
                raise osv.except_osv(
                    _('Error!'),
                    _('This event cannot be set as a template because it have '
                      'shared contents or existing seances linked to it'))
        return super(EventEvent, self).button_set_template(cr, uid, ids, context=context)

    def recompute_seances(self, cr, uid, ids, context=None):
        for event in self.browse(cr, uid, ids, context=context):
            if event.has_program and event.content_planification == 'linear':
                self.create_linear_children_events(cr, uid, [event.id], context=context)
        return True

    def onchange_has_program(self, cr, uid, ids, has_program, date_begin, content, context=None):
        values = {}
        # if has_program:
        #     EstimateEndDate = self.pool.get('event.event.estimate_end_date.wizard')
        #     ed = EstimateEndDate._compute_end_date(self, cr, uid, )
        return {'value': values}

    def open_preplanning(self, cr, uid, ids, context=None):
        if not ids:
            return {}
        modeldata_obj = self.pool.get('ir.model.data')
        form_model, form_view_id = modeldata_obj.get_object_reference(cr, uid, 'event', 'view_event_preplanning_form')
        preplanning_id = self.pool.get('event.event.preplanning').create(cr, uid, {
            'event_id': ids[0],
        }, context=context)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Preplanning'),
            'res_model': 'event.event.preplanning',
            'view_type': 'form',
            'view_mode': 'form',
            'views': [(form_view_id, 'form')],
            'res_id': preplanning_id,
            'target': 'current',
            'flags': {'form': {'initial_mode': 'edit'}},
            # 'context': {'filter_offer_id': ids[0]},
        }

    def create_linear_children_events(self, cr, uid, ids, context=None):
        Content = self.pool.get('event.content')
        Seance = self.pool.get('event.seance')
        logger = logging.getLogger('create-linear-seances')
        for event in self.browse(cr, uid, ids, context=context):
            # remove existing children events
            if event.seance_ids:
                Seance.unlink(cr, uid, [c.id for c in event.seance_ids], context=context)

            # if event.children_ids:
            #     continue  # do not re-create events twice
            print(">>> event '%d': creating linear children events" % (event.id,))
            # content_total_duration = sum(c.duration for c in event.content_ids)
            event_begin = datetime.strptime(event.date_begin, DT_FMT)
            # 1 day before end of life - otherwise bigbang traceback
            # with OverflowError cause of timezone computation ;-)
            event_end = datetime.max - timedelta(days=1)
            # event_end = datetime.strptime(event.date_end, DT_FMT)  # FIXME: add support for no end date (=None)

            if not event.content_ids:
                continue

            if event.content_planification == 'preplanning':
                continue  # nothing to do

            elif event.content_planification == 'linear':
                tmlayers = ['working_hours', 'leaves']
                timeline = self._get_resource_timeline(cr, uid, event.id, layers=tmlayers,
                                                       date_from=event_begin, date_to=event_end,
                                                       context=context)
                # iter on each timeline change, and eat all "available" time
                available_periods = (p for p in timeline.iterperiods(as_tz='UTC')
                                     if p.status == Availibility.FREE).__iter__()
                ###
                create_content = partial(Content.create_seances_from_content, cr, uid, o2m_commands=True, context=context)

                period = None
                commands = []
                for content in event.content_ids:
                    logger.info('creating for content %s (%.2f hours)' % (content.name, content.duration,))
                    remaining_duration = content.duration
                    while remaining_duration > 0:
                        try:
                            period = period or available_periods.next()
                        except StopIteration:
                            raise osv.except_osv(_('Error!'),
                                                 _('No enough time to schedule all content "%s"') % (content.name,))
                        logger.info('current period %s, remaining duration: %s' % (period, remaining_duration,))
                        if period.duration < content.slot_duration:
                            # remaining period is too small, get the next one
                            period = None
                            continue
                        alloc_duration = min(content.slot_duration, remaining_duration)
                        (s, e) = period.shift_hours(alloc_duration)
                        logger.info('allocated duration %.2f :: %s -> %s' % (alloc_duration, s, e))
                        commands.extend(create_content(content.id, s, e))
                        remaining_duration -= alloc_duration
                        # period_duration = period.duration
                        # if period_duration <= remaining_duration:
                        #     create_content(content.id, period.start, period.stop)
                        #     remaining_duration -= period_duration
                        #     period = None  # all period used
                        # else:
                        #     event_end = period.start + timedelta(hours=remaining_duration)
                        #     create_content(content.id, period.start, period.stop)
                        #     remaining_duration = 0
                        #     period.start = event_end

                Seance = self.pool.get('event.seance')
                result = []
                # Create all seances without stored fields
                ctx = dict(context, no_store_function=True)
                for cmd in commands:
                    new_seance_id = Seance.create(cr, uid, cmd[2], context=ctx)
                    result += Seance._store_get_values(cr, uid, [new_seance_id], cmd[2].keys(), ctx)
                mresult = defaultdict(list)
                # Computed stored fields in groups
                for order, object, ids, fields2 in result:
                    mresult[(order, object, tuple(fields2))] += ids
                for k in sorted(mresult):
                    (order, object, fields2) = k
                    ids = list(set(mresult[k]))
                    self.pool.get(object)._store_set_values(cr, uid, ids, fields2, context)

        return True

    def _get_resource_leaves(self, cr, uid, ids, date_from=None, date_to=None, context=None):
        result = {}
        Leave = self.pool.get('resource.calendar.leaves')
        for record in self.browse(cr, uid, ids, context=context):
            leave_domain = [
                '|', '|',
                    ('applies_to', '=', 'event_all'),
                    '&', ('applies_to', '=', 'company'), '|', ('company_id', '=', record.company_id.id),
                                                              ('company_id', '=', False),
                    '&', ('applies_to', '=', 'event'), ('event_id', '=', record.id),
            ]
            if record.calendar_id:
                leave_domain[:0] = ['|', '&', ('applies_to', '=', 'calendar'),
                                              ('calendar_id', '=', record.calendar_id.id)]
            result[record.id] = Leave.search(cr, uid, leave_domain, context=context)
        return result


class HelperGroupByMany2Many(osv.AbstractModel):
    _name = 'helper.groupby_many2many'

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False):
        """
        Get the list of records in list view grouped by the given ``groupby`` fields
        """
        # TODO: implement offset, limit, orderby

        ids = self.search(cr, uid, domain, context=context)
        if not groupby:
            raise osv.except_osv(_('Error!'), _('groupby is empty'))
        groupby_list = groupby
        groupby_field, groupby_sub = groupby[0], groupby[1:]
        groupby_column = self._all_columns[groupby_field].column
        groupby_type = groupby_column._type
        print("ReadGroup: %s, %s" % (groupby, groupby_type,))
        if groupby_type != 'many2many':
            return super(HelperGroupByMany2Many, self).read_group(cr, uid, domain, fields, groupby,
                                                                  offset=0, limit=limit, context=context,
                                                                  orderby=orderby)

        fget = self.fields_get(cr, uid, fields)
        aggregated_fields = [
            f for f in fields
            if f not in ('id', 'sequence')
            if fget[f]['type'] in ('integer', 'float')
            if (f in self._columns and getattr(self._columns[f], '_classic_write'))]
        order = orderby or groupby_field

        gb_records = defaultdict(set)
        if ids:
            for record in self.browse(cr, uid, ids, context=context):
                values = record[groupby_field]
                if values:
                    for v in values:
                        gb_records[v.id].add(record.id)
                else:
                    gb_records[False].add(record.id)

            gb_model = self.pool.get(groupby_column._obj)
            gb_records_ids = gb_model.search(cr, uid, [('id', 'in', gb_records.keys())], context=context)
            gb_records_repr = dict(gb_model.name_get(cr, uid, gb_records_ids, context=context))
            if False in gb_records:
                gb_records_ids.insert(0, False)
                gb_records_repr[False] = _('Undefined')

        else:
            gb_records_ids = []
            gb_records_repr = {}

        result = []
        for _id in gb_records_ids:
            if _id is False:
                gbrepr = (_id, _('Undefined'))
            else:
                gbrepr = (_id, gb_records_repr[_id])
            result.append({
                '__context': {'group_by': groupby_sub},
                '__domain': domain + [(groupby_field, '=', _id)],
                groupby_field: gbrepr,
                '%s_count' % (groupby_field,): len(gb_records[_id]),
            })

        if groupby_field and groupby_field in self._group_by_full:
            result = self._read_group_fill_results(cr, uid, domain, groupby_field, groupby_list,
                                                   aggregated_fields, result, read_group_order=order,
                                                   context=context)
        from pprint import pprint
        pprint(result)
        return result


class EventRegistration(osv.Model):
    _name = 'event.registration'
    _inherit = ['event.registration', 'helper.groupby_many2many']

    def _test_event_has_manual_participation(self, cr, uid, ids, context=None):
        if not ids:
            return {}
        cr.execute("""
            SELECT
                event.id, count(1)
            FROM event_event AS event
            LEFT JOIN event_content_link cl ON (cl.event_id = event.id)
            LEFT JOIN event_content AS content ON (cl.content_id = content.id)
            LEFT JOIN event_seance_type seance_type ON (content.type_id = seance_type.id)
            WHERE seance_type.manual_participation = true AND event.id IN %s
            GROUP BY event.id;
        """, (tuple(ids),))
        event_having_manual_participation = set([event['id'] for event in cr.dictfetchall()])
        result = {}
        for _id in ids:
            result[_id] = _id in event_having_manual_participation
        return result

    def _get_event_has_manual_participation(self, cr, uid, ids, fieldname, args, context=None):
        if not ids:
            return {}
        registration2event = dict((r.id, r.event_id.id)
                                  for r in self.browse(cr, uid, ids, context=context))
        event_info = self._test_event_has_manual_participation(cr, uid,
                            registration2event.values(), context=context)
        result = {}
        for reg_id, event_id in registration2event.iteritems():
            result[reg_id] = event_info[event_id]
        return result

    _columns = {
        'group_ids': fields.many2many('event.participation.group', 'event_registration_participation_group_rel',
                                      string='Groups', id1='registration_id', id2='group_id'),
        'participation_ids': fields.one2many('event.participation', 'registration_id', 'Participations', readonly=True),
        'event_has_manual_participation': fields.function(_get_event_has_manual_participation, type='boolean'),
        'manual_participation_ids': fields.one2many('event.participation', 'registration_id', 'Manual Participations',
                                                    domain=[('seance_id.type_id.manual_participation','=',True)]),
    }

    def create(self, cr, uid, values, context=None):
        if values and values.get('event_id') and 'group_ids' not in values:
            change_values = self.onchange_event_id(cr, uid, [], values['event_id'], context=context)
            values['group_ids'] = change_values.get('value', {}).get('group_ids', [])
        return super(EventRegistration, self).create(cr, uid, values, context=context)

    def write(self, cr, uid, ids, values, context=None):
        if context is None:
            context = {}
        if 'group_ids' in values:
            if context.get('group_for_content_id') and isinstance(values['group_ids'], (int, long)):
                # if changed assigned group from kanban view, fix command syntax
                new_group_id = values['group_ids']
                Content = self.pool.get('event.content')
                content = Content.browse(cr, uid, context['group_for_content_id'], context=context)
                commands = [(3, group.id)
                            for group in content.group_ids
                            if group.id != new_group_id]
                commands.append((4, new_group_id))
                values['group_ids'] = commands

            done_reg_domain = [('id', 'in', ids), ('state', '=', 'done')]
            if self.search(cr, uid, done_reg_domain, context=context):
                raise osv.except_osv(_('Error'), _('You can only change groups when registration is not done'))
        return super(EventRegistration, self).write(cr, uid, ids, values, context=context)

    def _update_registration_groups(self, cr, uid, ids, context=None):
        for registration in self.browse(cr, uid, ids, context=context):
            event = registration.event_id
            group_by_content = defaultdict(list)
            for g in registration.group_ids:
                group_by_content[g.event_content_id.id].append(g.id)
            group_ops = []
            for content in event.content_ids:
                if content.is_divided and content.id not in group_by_content:
                    # add default group
                    group_ops.append((4, content.group_ids[0].id))
                elif not content.is_divided and content.id in group_by_content:
                    # remove groups
                    group_ops.extend((3, content_id)
                                     for content_id in group_by_content[content.id])
            registration.write({'group_ids': group_ops})
        return True

    def onchange_event_id(self, cr, uid, ids, event_id, context=None):
        ocv = super(EventRegistration, self).onchange_event_id(cr, uid, ids, event_id, context=context)
        ocv.setdefault('value', {})
        if event_id:
            group_ids = []
            Event = self.pool.get('event.event')
            event = Event.browse(cr, uid, event_id, context=context)
            for content in event.content_ids:
                if content.is_divided:
                    # take default group (ordered first) or 1st group available if not default
                    group_ids.append(content.group_ids[0].id)
            ocv['value']['group_ids'] = [(6, 0, group_ids)]

            # Check if event has manual participations
            manualpart = self._test_event_has_manual_participation(cr, uid, [event_id], context=context)
            ocv['value']['event_has_manual_participation'] = manualpart[event_id]
        else:
            ocv['value']['event_has_manual_participation'] = False
        return ocv

    def onchange_group_ids(self, cr, uid, ids, event_id, group_ids, context=None):
        # filter groups to only keep the last group 'id' for each content
        # (this way we can simulte mutualy-exclusing groups)
        if group_ids and len(group_ids[0]) == 3 and group_ids[0][0] == 6:
            group_obj = self.pool.get('event.participation.group')
            group_ids = group_ids[0][2]
            group_to_unset = []
            group_by_content = {}
            for group in group_obj.browse(cr, uid, group_ids, context=context):
                content = group.event_content_id
                if content.id in group_by_content:
                    group_to_unset.extend(group_by_content[content.id])
                group_by_content[content.id] = [group.id]
            if group_to_unset:
                new_group_ids = [x for x in group_ids if x not in group_to_unset]
                return {'value': {'group_ids': [(6, 0, new_group_ids)]}}

        return True

    def _msg_content_group_subscription(self, cr, uid, ids, context=None):
        for reg in self.browse(cr, uid, ids, context=context):
            reg_errors = []
            reg_group_ids = [g.id for g in reg.group_ids]
            for content in reg.event_id.content_ids:
                group_count = len([g for g in content.group_ids
                                   if g.id in reg_group_ids])
                if content.is_divided and group_count != 1:
                    if group_count < 1:
                        reg_errors.append(_("You have to choose one group for '%s'") % (content.name,))
                    elif group_count > 1:
                        reg_errors.append(_("You have to choose only one group for '%s'") % (content.name,))
            if reg_errors:
                return u'\n'.join(reg_errors)
        return _('You have to subscribe to one and only one group for each event content')

    def _check_content_group_subscription(self, cr, uid, ids, context=None):
        for reg in self.browse(cr, uid, ids, context=context):
            reg_group_ids = [g.id for g in reg.group_ids]
            for content in reg.event_id.content_ids:
                group_count = len([g for g in content.group_ids
                                   if g.id in reg_group_ids])
                if content.is_divided and group_count != 1:
                    return False
        return True

    _constraints = [
        (_check_content_group_subscription, _msg_content_group_subscription, ['group_ids']),
    ]

    @logged
    def _get_groupby_full_group_ids(self, cr, uid, present_group_ids, domain,
                                    read_group_order=None, access_rights_uid=None,
                                    context=None):
        if context is None:
            context = {}
        result = []
        if context.get('group_for_content_id'):
            ParticipationGroup = self.pool.get('event.participation.group')
            group_domain = [('event_content_id', '=', context['group_for_content_id'])]
            group_ids = ParticipationGroup.search(cr, uid, group_domain, context=context)
            result = ParticipationGroup.name_get(cr, uid, group_ids, context=context)
        print("CONTEXT: %s" % (context,))
        return result, []

    _group_by_full = {
        'group_ids': _get_groupby_full_group_ids,
    }


class EventSeance2(osv.Model):
    _name = 'event.seance'
    _inherit = ['event.seance', 'helper.groupby_many2many']
    pass

class EventParticipation2(osv.Model):
    _name = 'event.participation'
    _inherit = ['event.participation', 'helper.groupby_many2many']
    pass

