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
from timeline import Timeline, Availibility
from resource import float_to_hm
from openerp.tools import logged


class EventSeanceType(osv.Model):
    _name = 'event.seance.type'
    _columns = {
        'name': fields.char('Seance Type', size=64, required=True),
    }


class EventContent(osv.Model):
    """ Event Content """
    _name = 'event.content'
    _description = __doc__

    def _get_remaining_duration_to_schedule(self, cr, uid, ids, field_name, args, context=None):
        result = {}
        if not ids:
            return result

        Event = self.pool.get('event.event')
        content_related_domain = [('event_link_ids.content_id', 'in', ids), ('state', '!=', 'cancel')]
        content_related_event_ids = Event.search(cr, uid, content_related_domain, context=context)
        content_related_events = defaultdict(list)
        for event in Event.browse(cr, uid, content_related_event_ids, context=context):
            for content_link in event.event_link_ids:
                content_id = content_link.content_id.id
                if content_id in ids:
                    content_related_events[content_id].append(event)

        for content in self.browse(cr, uid, ids, context=context):
            scheduled_duration = sum((e.duration for e in content_related_events.get(content.id, [])) or [0])
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
        print("change:duration # %s | %s x %s = %s" % (field_source, slot_count, slot_duration, tot_duration))
        print("==> context: %s" % (context,))
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
        # fixed == 'slot_duration'

        # slot_count => duration
        # slot_duration => duration
        # duration => slot_count
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

    _columns = {
        'sequence': fields.integer('Sequence', required=True),
        'name': fields.char('Content', size=128, required=True),
        'type_id': fields.many2one('event.seance.type', 'Type',
                                   help='Default type of seance'),
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
        'group_ids': fields.one2many('event.participant.group', 'event_content_id'),
    }

    _defaults = {
        'duration': 1,
        'sequence': 0,
        'slot_duration': 1,
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

    def _prepare_seance_for_content(self, cr, uid, content, date_begin, date_end, group=None, context=None):
        if isinstance(date_begin, basestring):
            date_begin = datetime.strptime(date_begin, DT_FMT)
        if isinstance(date_end, basestring):
            date_end = datetime.strptime(date_begin, DT_FMT)
        duration_delta = date_end - date_begin
        duration = duration_delta.days * 24 + (duration_delta.seconds / 3600.)
        values = {
            'name': content.name,
            'content_id': content.id,
            'group_id': group.id if group else False,
            'date_begin': date_begin,
            'duration': duration,
        }
        return values

    def create_seances_from_content(self, cr, uid, ids, date_begin, date_end, context=None):
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
    ]

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

    _columns = {
        'name': fields.char('Seance Name', required=True),
        'type_id': fields.many2one('event.seance.type', 'Type'),
        'date_begin': fields.datetime('Begin date', required=True, states={'draft': [('required', False)]}),
        'duration': fields.float('Duration', required=True),
        # 'planned_week_date': fields.function(_get_planned_week_date, string='Planned Week date',
        #                                      type='date', readonly=True, store=True, groupby_range='week'),
        'planned_week': fields.date('Planned Week Date', readonly=True, groupby_range='week'),
        'tz': fields.selection(_tz_get, size=64, string='Timezone'),
        # TODO: add planned_period, planned_period_date
        'participant_min': fields.integer('Participant Min'),
        'participant_max': fields.integer('Participant Max'),
        'main_speaker_id': fields.many2one('res.partner', 'Main Speaker'),
        'address_id': fields.many2one('res.partner', 'Address'),
        'content_id': fields.many2one('event.content', 'Content'),
        'content_divided': fields.related('content_id', 'is_divided', type='boolean',
                                          string='Divided'),
        'group_id': fields.many2one('event.participant.group', 'Group'),
        'event_ids': fields.related('content_id', 'event_ids', type='many2many',
                                    relation='event.event', string='Events',
                                    readonly=True),
        'participant_ids': fields.one2many('event.participant', 'seance_id', 'Participants'),
        'state': fields.selection(SEANCE_STATES, 'State', readonly=True, required=True),
    }

    _defaults = {
        'state': 'draft',
    }

    def _check_content_group_ref(self, cr, uid, ids, context=None):
        """enforce presence of 'group' if linked content is 'divided'"""
        for content_link in self.browse(cr, uid, ids, context=context):
            if content_link.content_divided and not content_link.group_id:
                return False
        return True

    _constraints = [
        (_check_content_group_ref, 'You have to specify a group for divided content', ['group_id']),
    ]

    def onchange_content_id(self, cr, uid, ids, content_id, context=None):
        ocv = super(EventSeance, self).onchange_content_id(cr, uid, ids, content_id, context=context)
        ocv.setdefault('value', {})
        ocv.setdefault('domain', {})
        if content_id:
            content_obj = self.pool.get('event.content')
            content = content_obj.browse(cr, uid, content_id, context=context)
            ocv['value']['content_divided'] = content.is_divided
        ocv['value']['group_id'] = False
        return ocv

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
        return self.write(cr, uid, ids, {'state': 'doen'}, context=context)


class EventParticipant(osv.Model):
    """ Event Participant """
    _name = 'event.participant'
    _description = __doc__
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    PRESENCE_STATUS = [
        ('none', 'No Presence Information'),
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
    ]

    STATES = [
        ('draft', 'Draft'),
        ('exception', 'Exception'),  # TODO: impl. when errors happens on participation
        ('done', 'Done'),
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

    _columns = {
        'name': fields.char('Participant Name', size=128, required=True),
        'partner_id': fields.many2one('res.partner', 'Participant', required=True),
        'seance_id': fields.many2one('event.seance', 'Seance', required=True),
        'registration_id': fields.many2one('event.registration', 'Registration', required=True),
        'state': fields.selection(STATES, 'State', readonly=True, required=True),
        # Presence Information
        'presence': fields.selection(PRESENCE_STATUS, 'Presence', required=True),
        'presence_summary': fields.function(_get_presence_summary, type='char',
                                            string='Presence Summary'),
        'arrival_time': fields.datetime('Arrival Time'),
        'departure_time': fields.datetime('Departure Time'),
    }

    _defaults = {
        'state': 'draft',
        'presence': 'none',
    }

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

    # Workaround shitty bug in when client (taking context of 1st button with same name)
    button_take_presence_2 = button_take_presence

    def onchange_registration(self, cr, uid, ids, registration_id, context=None):
        values = {}
        if registration_id:
            Registration = self.pool.get('event.registration')
            reg = Registration.browse(cr, uid, registration_id, context=context)
            values.update(partner_id=reg.partner_id.id)
        return {'value': values}


class EventParticipantGroup(osv.Model):
    _name = 'event.participant.group'
    _order = 'is_default DESC, name'

    def _get_participant_count(self, cr, uid, ids, field_name, args, context=None):
        result = {}
        for group in self.browse(cr, uid, ids, context=context):
            event = group.event_content_id.event_id
            total = event.register_current + event.register_prospect
            count = sum([reg.nb_register for reg in group.registration_ids])
            result[group.id] = _('%d / %d') % (count, total)
        return result

    def name_get(self, cr, uid, ids, context=None):
        result = []
        for group in self.browse(cr, uid, ids, context=context):
            repr_name = '%s / %s' % (group.event_content_id.name, group.name)
            result.append((group.id, repr_name,))
        return result

    _columns = {
        'name': fields.char('Group name', required=True),
        'event_content_id': fields.many2one('event.content', 'Content', required=True, ondelete='cascade'),
        'is_default': fields.boolean('Is default?'),
        'participant_count': fields.function(_get_participant_count, type='char', string='# of participants'),
        'registration_ids': fields.many2many('event.registration', 'event_registration_participation_group_rel',
                                             string='Registrations', id1='group_id', id2='registration_id'),
    }

    def create(self, cr, uid, values, context=None):
        content_id = values.get('event_content_id')
        if content_id:
            content = self.pool.get('event.content').browse(cr, uid, content_id, context=context)
            event_ids = content.event_ids
            if event_ids and any(e.state != 'draft' for e in event_ids):
                raise osv.except_osv(_('Error'), _('You can only add new content group on draft events'))
        return super(EventParticipantGroup, self).create(cr, uid, values, context=context)

    def write(self, cr, uid, ids, values, context=None):
        if 'registration_ids' in values:
            for group in self.browse(cr, uid, ids, context=context):
                if group.event_content_id.event_id.state == 'done':
                    raise osv.except_osv(_('Error'), _('You cannot change content group subscription on done events'))
        return super(EventParticipantGroup, self).write(cr, uid, ids, values, context=context)

    def unlink(self, cr, uid, ids, context=None):
        for group in self.browse(cr, uid, ids, context=context):
            if group.event_content_id.event_id.state != 'draft':
                raise osv.except_osv(_('Error'), _('You can only remove a new content group on draft events'))
        return super(EventParticipantGroup, self).unlink(cr, uid, ids, context=context)

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
        return super(EventParticipantGroup, self).default_get(cr, uid, fields_list, context=context)


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
        'default_content_planification': 'none',
    }


class EventEvent(osv.Model):
    _name = 'event.event'
    _inherit = ['event.event', 'resource.timeline']

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
    }

    _defaults = {
        'content_planification': 'linear',
    }

    def copy(self, cr, uid, id, default=None, context=None):
        """ Reset the state and the registrations while copying an event
        """
        if default is None:
            default = {}
        default.update(content_ids=False)
        return super(EventEvent, self).copy(cr, uid, id, default=default, context=context)

    def onchange_event_type(self, cr, uid, ids, type_event, context=None):
        values = super(EventEvent, self).onchange_event_type(cr, uid, ids, type_event, context=context)
        if type_event:
            Type = self.pool.get('event.type')
            type_info = Type.browse(cr, uid, type_event, context)
            values['value'].update(
                has_program=type_info.default_has_program,
                content_planification=type_info.default_content_planification)
        return values

    def recompute_seances(self, cr, uid, ids, context=None):
        for event in self.browse(cr, uid, ids, context=context):
            if event.has_program and event.content_planification == 'linear':
                self.create_linear_children_events(cr, uid, [event.id], context=context)
        return True

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
            event_end = event_begin + timedelta(days=20) # TODO: add estimated end date
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
                available_periods = (p for p in timeline.iter(by='change', as_tz='UTC')
                                     if p.status == Availibility.AVAILABLE).__iter__()
                ###
                create_content = partial(Content.create_seances_from_content, cr, uid, context=context)

                period = None
                for content in event.content_ids:
                    logger.info('creating for content %s (%.2f hours' % (content.name, content.duration,))
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
                        create_content(content.id, s, e)
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

        return True


class EventRegistration(osv.Model):
    _inherit = 'event.registration'
    _columns = {
        'group_ids': fields.many2many('event.participant.group', 'event_registration_participation_group_rel',
                                      string='Groups', id1='registration_id', id2='group_id'),
        'participation_ids': fields.one2many('event.participation', 'registration_id', 'Participations', readonly=True),
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

            nondraft_reg_domain = [('id', 'in', ids), ('state', '!=', 'draft')]
            if self.search(cr, uid, nondraft_reg_domain, context=context):
                raise osv.except_osv(_('Error'), _('You can only change groups when registration is unconfirmed'))
        return super(EventRegistration, self).write(cr, uid, ids, values, context=context)

    def onchange_event_id(self, cr, uid, ids, event_id, context=None):
        ocv = super(EventRegistration, self).onchange_event_id(cr, uid, ids, event_id, context=context)
        if event_id:
            group_ids = []
            Event = self.pool.get('event.event')
            event = Event.browse(cr, uid, event_id, context=context)
            for content in event.content_ids:
                if content.group_ids:
                    # take default group (ordered first) or 1st group available if not default
                    group_ids.append(content.group_ids[0].id)
            ocv.setdefault('value', {})
            ocv['value']['group_ids'] = [(6, 0, group_ids)]
        return ocv

    def onchange_group_ids(self, cr, uid, ids, event_id, group_ids, context=None):
        # filter groups to only keep the last group 'id' for each content
        # (this way we can simulte mutualy-exclusing groups)
        if group_ids and len(group_ids[0]) == 3 and group_ids[0][0] == 6:
            group_obj = self.pool.get('event.participant.group')
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
                if content.group_ids and group_count != 1:
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
                if content.group_ids and group_count != 1:
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
            ParticipantGroup = self.pool.get('event.participant.group')
            group_domain = [('event_content_id', '=', context['group_for_content_id'])]
            group_ids = ParticipantGroup.search(cr, uid, group_domain, context=context)
            result = ParticipantGroup.name_get(cr, uid, group_ids, context=context)
        print("CONTEXT: %s" % (context,))
        return result, []

    _group_by_full = {
        'group_ids': _get_groupby_full_group_ids,
    }

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
        if groupby_type != 'many2many':
            return super(EventRegistration, self).read_group(cr, uid, domain, fields, groupby,
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

        print("Result: %s" % (result,))
        return result
