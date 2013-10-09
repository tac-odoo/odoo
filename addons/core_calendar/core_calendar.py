# -*- coding: utf-8 -*-
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

import pytz
import copy
from datetime import datetime, timedelta
from collections import defaultdict
from openerp.osv import osv, fields, expression
import openerp.tools as tools
from openerp.tools.misc import logged, flatten
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DT_FMT
from openerp.tools.safe_eval import safe_eval
from openerp.tools.translate import _
from openerp.tools.misc import flatten
from openerp.addons.base.res.res_partner import _tz_get
from timeline import Timeline, Availibility, WorkingHoursPeriodEmiter, GenericEventPeriodEmiter


class CoreCalendarTimeline(osv.TransientModel):
    _name = 'core.calendar.timeline'

    LAYERS = set([
        'working_hours',
        'leaves',
        'events',  # calendar event (can be an event, a task, ...)
    ])

    _columns = {
        'tz': fields.selection(_tz_get, size=64, string='Timezone'),
        'calendar_id': fields.many2one('resource.calendar', 'Calendar'),
    }

    def _get_resource_working_hours(self, cr, uid, ids, date_from=None, date_to=None, context=None):
        result = {}
        for record in self.browse(cr, uid, ids, context=context):
            # dayofweek (=> iso weekday): 1: Monday, ..., 6: Saturday, 7: Sunday
            if record.calendar_id and record.calendar_id.attendance_ids:
                result[record.id] = [
                    (int(att.dayofweek)+1, att.hour_from, att.hour_to)
                    for att in record.calendar_id.attendance_ids
                ]
            else:
                result[record.id] = [
                    (dayofweek+1, 0, 24)
                    for dayofweek in xrange(7)
                ]
        return result

    def _get_resource_leaves(self, cr, uid, ids, date_from=None, date_to=None, context=None):
        return dict((_id, []) for _id in ids)

    def _get_resource_events(self, cr, uid, ids, date_from=None, date_to=None, context=None):
        return dict((_id, []) for _id in ids)

    def _get_resource_timezone(self, cr, uid, ids, context=None):
        result = {}
        for record in self.browse(cr, uid, ids, context=context):
            result[record.id] = record.tz or 'UTC'
        return result

    def _get_resource_timeline(self, cr, uid, ids, layers=None, date_from=None, date_to=None, context=None):
        if not ids:
            return False
        record_ids = ids
        if isinstance(ids, (int, long)):
            record_ids = [ids]
        if isinstance(date_from, basestring):
            date_from = datetime.strptime(date_from, DT_FMT)
        if isinstance(date_to, basestring):
            date_to = datetime.strptime(date_to, DT_FMT)

        if layers is None:
            timeline_layers = self.LAYERS
        else:
            # restore order of layers
            timeline_layers = [l for l in self.LAYERS if l in layers]

        result = {}
        for record in self.browse(cr, uid, record_ids, context=context):

            tz = self._get_resource_timezone(cr, uid, [record.id], context=context)[record.id]
            # NOTE: All datetime passed to Timeline should be naive date in the resource "local timezone" !!!
            tz_resource = pytz.timezone(tz)
            tz_utc = pytz.timezone('UTC')
            timeline_start_dt = Timeline.datetime_tz_convert(date_from, tz_utc, tz_resource)
            timeline_end_dt = Timeline.datetime_tz_convert(date_to, tz_utc, tz_resource)
            timeline = Timeline(timeline_start_dt, timeline_end_dt, tz=tz, default=Availibility.UNKNOWN)

            for layer in timeline_layers:
                if layer == 'working_hours':

                    wkhours = self._get_resource_working_hours(cr, uid, [record.id], date_from=date_from,
                                                               date_to=date_to, context=context)[record.id]
                    timeline.add_emiter(WorkingHoursPeriodEmiter('working_hours', working_hours=[
                        # 0: wday, 1: hour_from, 2: hour_to
                        (att[0], att[1], att[2]) for att in wkhours
                    ]))

                elif layer == 'leaves':

                    # add all leaves for this event
                    leaves_emiter = GenericEventPeriodEmiter('leaves')
                    timeline.add_emiter(leaves_emiter)
                    Leave = self.pool.get('resource.calendar.leaves')
                    leave_ids = self._get_resource_leaves(cr, uid, [record.id], date_from=date_from,
                                                          date_to=date_to, context=context)[record.id]
                    for leave in Leave.browse(cr, uid, leave_ids, context=context):
                        leave_from = timeline.datetime_from_str(leave.date_from, tz='UTC')
                        leave_to = timeline.datetime_from_str(leave.date_to, tz='UTC')
                        leaves_emiter.add_event(leave_from, leave_to, Availibility.BUSY)  # FIXME: implement OUT_OF_OFFICE level

                elif layer == 'events':

                    event_emiter = GenericEventPeriodEmiter('events')
                    timeline.add_emiter(event_emiter)
                    CalEvent = self.pool.get('core.calendar.event')
                    event_ids = self._get_resource_events(cr, uid, [record.id], date_from=date_from,
                                                          date_to=date_to, context=context)[record.id]
                    for event in CalEvent.read(cr, uid, event_ids, ['date_start', 'date_end', 'state'], context=context):
                        event_start = timeline.datetime_from_str(event['date_start'], tz='UTC')
                        event_end = timeline.datetime_from_str(event['date_end'], tz='UTC')
                        event_state = event['state']
                        if event_state == 'tentative':
                            event_mapped_state = Availibility.BUSY_TENTATIVE
                        elif event_state == 'confirm':
                            event_mapped_state = Availibility.BUSY
                        else:
                            raise Exception(_('Bad Event State %s') % (event_state))
                        event_emiter.add_event(event_start, event_end, event_mapped_state)

            result[record.id] = timeline

        if isinstance(ids, (int, long)):
            return result.values()[0]
        return result

    def get_resource_unavailibility(self, cr, uid, model, ids, date_from, date_to, group_by_field=None, context=None):
        if not ids:
            return False
        res_ids = ids
        if isinstance(ids, (int, long)):
            res_ids = [ids]
        unavails = []

        model_obj = self.pool.get(model)
        if group_by_field:
            # model represent the base object on which we're doing the "group_by",
            # we need to get the related model from the grouped field instead.
            group_field = model_obj.fields_get(cr, uid, [group_by_field], context=context)[group_by_field]
            if group_field['type'] != 'many2one':
                # in grouped mode, only grouping by many2one field is supported
                return False
            # NOTE: in that case, "ids" already refer to group many2one relation
            #res_ids = [int(_id) for _id in res_ids]
            model_ids = [_id for _id in ids if _id is not False]
            model_obj = self.pool.get(group_field['relation'])

            if hasattr(model_obj, '_get_resource_timeline'):
                tllayers = ['working_hours', 'leaves']
                tlresult = model_obj._get_resource_timeline(cr, uid, model_ids, layers=tllayers,
                                                            date_from=date_from, date_to=date_to,
                                                            context=context)
                for record_id, timeline in tlresult.iteritems():
                    for period in timeline.iterperiods(as_tz='UTC'):
                        if period.status == Availibility.FREE:
                            continue

                        unavails.append({
                            'start_date': period.start.strftime(DT_FMT),
                            'end_date': period.stop.strftime(DT_FMT),
                            'css': 'oe_marked_timespan',
                            'sections': {
                                'groupby': record_id,
                            }
                        })

        return unavails


class CoreCalendarResource(osv.TransientModel):
    _name = 'core.calendar.resource'
    _inherit = 'core.calendar.timeline'

    def _get_resource_freebusy(self, cr, uid, ids, fieldname, args, context=None):
        return self.get_resource_freebusy(cr, uid, ids, context=context)

    _columns = {
        'freebusy': fields.function(_get_resource_freebusy, type='char', string='Free/Busy'),
    }

    def _get_resource_leaves(self, cr, uid, ids, date_from=None, date_to=None, context=None):
        result = {}
        Leave = self.pool.get('resource.calendar.leaves')
        for record in self.browse(cr, uid, ids, context=context):
            leave_domain = [
                '|', '|',
                    ('applies_to', '=', 'resource_all'),
                    '&', ('applies_to', '=', 'company'), '|', ('company_id', '=', record.company_id.id),
                                                              ('company_id', '=', False),
                    '&', ('applies_to', '=', 'resource'), ('partner_id', '=', record.id),
            ]
            if record.calendar_id:
                leave_domain[:0] = ['|', '&', ('applies_to', '=', 'calendar'),
                                              ('calendar_id', '=', record.calendar_id.id)]
            result[record.id] = Leave.search(cr, uid, leave_domain, context=context)
        return result

    def _get_resource_events(self, cr, uid, ids, date_from=None, date_to=None, context=None):
        result = {}
        Calendar = self.pool.get('core.calendar')
        CalEvent = self.pool.get('core.calendar.event')
        for record in self.browse(cr, uid, ids, context=context):
            event_domain = [
                ('attendee_id', '=', record.id),
                ('state', '!=', 'cancel'),
                '|', '&', ('date_start', '>=', date_from.strftime(DT_FMT)),
                          ('date_start', '<=', date_to.strftime(DT_FMT)),
                     '&', ('date_end', '>=', date_from.strftime(DT_FMT)),
                          ('date_end', '<=', date_to.strftime(DT_FMT))
            ]
            result[record.id] = CalEvent.search(cr, uid, event_domain, context=context)
        return result

    def get_i18n_availibility_status(self, cr, uid, availibility_status, short=False, context=None):
        short = False
        return {
            Availibility.UNKNOWN: _('?') if short else _('Unknown'),
            Availibility.UNAVAILABLE: _('U') if short else _('Unavailable'),
            Availibility.FREE: _('F') if short else _('Free'),
            Availibility.BUSY_TENTATIVE: _('T') if short else _('Busy (tentative)'),
            Availibility.BUSY: _('B') if short else _('Busy'),
        }[availibility_status]

    def get_resource_freebusy(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        result = dict.fromkeys(ids, _('Unknown'))
        if not (context.get('fb_from')
                and (context.get('fb_to') or context.get('fb_duration'))):
            return result
        fb_from = context['fb_from']
        fb_to = context.get('fb_to')
        fb_duration = context.get('fb_duration')
        fb_short_status = context.get('fb_short_status') and True or False

        for i, record in enumerate(self.browse(cr, uid, ids, context=context)):
            # print("[%04d - %s :: %d] FreeBusy %s => %s" % (i, record._name, record.id, fb_from, fb_to,))
            sdate = fb_from
            if fb_duration:
                tz = record.tz or 'UTC'
                s = Timeline.datetime_tz_convert(fb_from, 'UTC', tz)
                s += timedelta(hours=fb_duration)
                edate = Timeline.datetime_tz_convert(s, tz, 'UTC').strftime(DT_FMT)
            else:
                edate = fb_to
            timeline = self._get_resource_timeline(cr, uid, record.id,
                                                   date_from=sdate,
                                                   date_to=edate, context=context)
            avails = []
            for period in timeline.iterperiods():
                # print("-- %s" % (period,))
                avails.append(period.status)
            result[record.id] = self.get_i18n_availibility_status(cr, uid, max(avails), short=fb_short_status, context=context)
        return result


class ResPartner(osv.Model):
    _name = 'res.partner'
    _inherit = ['core.calendar.resource', 'res.partner']

    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        if context is None:
            context = {}
        result = super(ResPartner, self).name_search(cr, user, name=name, args=args,
                                                     operator=operator, context=context,
                                                     limit=limit)
        locked = context.get('__fb_lock')
        if (not locked and context.get('fb_from')
                and (context.get('fb_to') or context.get('fb_duration'))):
            ctx = dict(context, fb_short_status=True, __fb_lock=True)
            ids = [x[0] for x in result]
            fb = self.get_resource_freebusy(cr, user, ids, context=ctx)
            newresult = []
            for _id, _name in result:
                lines = _name.split('\n')
                lines[0] = '%s [%s]' % (lines[0], fb[_id])
                newresult.append((_id, '\n'.join(lines)))
            result = newresult
        return result


class CoreCalendar(osv.Model):
    _name = 'core.calendar'
    _calendar_types = [
        ('vevent', 'Events'),
        # ('vtodo', 'Todos'),
        # ('vjournal', 'Journal Logs'),
    ]
    _calendar_date_modes = [
        ('end', 'Start -> End'),
        ('duration', 'Start -> Start + Duration'),
        #('deadline', 'Deadline') <== TODO: implement this specifc case (suggested by apr)
    ]

    def _get_action_data(self, cr, uid, ids, field_names, args, context=None):
        result = {}
        for calendar in self.browse(cr, uid, ids, context=context):
            action = calendar.action_id
            form_view = [v[0] for v in action.views if v[1] == 'form']
            result[calendar.id] = {
                'action_form_view_id': form_view and form_view[0] or False,
                'action_res_model': action.res_model,
            }
        return result

    def onchange_model(self, cr, uid, ids, model_id, context=None):
        values = {}
        if not model_id:
            for f in self._all_columns:
                if f.startswith('field_'):
                    values[f[6:]] = False
        return {'value': values}

    _columns = {
        'name': fields.char('Calendar Name', size=32, required=True, translate=True),
        'type': fields.selection(_calendar_types, 'Type', required=True),
        'date_mode': fields.selection(_calendar_date_modes, 'Date Mode', required=True),
        'model': fields.many2one('ir.model', 'Model', required=True),
        'action_id': fields.many2one('ir.actions.act_window', 'Action', required=True,
                                     help='Action used when opening/creating a new event'),
        'field_name': fields.many2one('ir.model.fields', 'Name', required=True, help='Field used to describe event name'),
        'field_date_start': fields.many2one('ir.model.fields', 'Start date', required=True),
        'field_date_end': fields.many2one('ir.model.fields', 'End date'),
        'field_duration': fields.many2one('ir.model.fields', 'Duration'),
        'field_recurrent': fields.many2one('ir.model.fields', 'Recurrent', help='Field used to indicate if an event is recurrent'),
        'field_organizer_id': fields.many2one('ir.model.fields', 'Responsible', help='Responsible/Organizer for that event',
                                              target_relation='res.partner'),
        'field_location': fields.many2one('ir.model.fields', 'Location', help='Location of event',
                                          target_relation='res.partner'),
        'field_attendee_ids': fields.many2many('ir.model.fields', 'core_calendar_attendee_fields_rel', id1='calendar_id', id2='field_id',
                                               string='Attendees', help='Field representing list of attendee',
                                               target_relation='res.partner'),
        'field_state': fields.many2one('ir.model.fields', 'State'),
        'states_tentative': fields.char('States (Tentative)', size=256,
                                        help='Comma separated list of states which represent object as unlocked/draft'),
        'states_confirm': fields.char('States (Confirm)', size=256,
                                      help='Comma separated list of states which represent object as locked/confirmed'),
        'states_cancel': fields.char('States (Cancel', size=256,
                                     help='Comma separated list of states which represent object as cancelled'),
        'readonly_expr': fields.char('Readonly expression', size=1024),
        'filter_expr': fields.char('Filter domain', size=1024),
        'color': fields.char('Color', help='Hexadecimal colors for events of this calendar'),
        'action_form_view_id': fields.function(_get_action_data, type='many2one', relation='ir.ui.view', multi='action_data',
                                               string='Action Form View', help='The form view used to create/edit event from this calendar'),
        'action_res_model': fields.function(_get_action_data, type='char', string='Action Model', multi='action_data'),
    }

    _sql_constraints = [
        ('check_date_fields', "CHECK((date_mode = 'end' AND field_date_end IS NOT NULL) OR (date_mode = 'duration' AND field_duration IS NOT NULL))",
         'Missing date_end or duration field'),
    ]

    def _get_base_fields(self, cr, uid, context=None):
        """Base fields can be readed as-is from source object table"""
        return ['id', 'name', 'date_start', 'recurrent', 'organizer_id', 'location']

    def _get_extended_fields(self, cr, uid, context=None):
        """Extended fields need to be post-processed"""
        return ['main_speaker_id', 'attendee_ids', 'attendee_id', 'state']

    @tools.ormcache()
    def _get_calendar_info(self, cr, uid, calendar_id, lang=None):
        context = {'lang': lang}
        calendar = self.browse(cr, uid, calendar_id, context=context)
        fields = {}
        fields_type = {}

        def mapped_fieldname(field_record, dest_relation):
            if not field_record:
                return False
            mapped_fieldname = field_record.name
            if field_record.relation == 'res.users' and dest_relation == 'res.partner':
                mapped_fieldname += '.partner_id'
            return mapped_fieldname

        for fieldname in calendar._all_columns:
            if not fieldname.startswith('field_'):
                continue
            short_fieldname = fieldname[6:]
            column = calendar._all_columns[fieldname].column
            target_relation = getattr(column, 'target_relation', None)

            if column._type == 'many2one':
                cval = calendar[fieldname]
                fields[short_fieldname] = mapped_fieldname(cval, target_relation)
                fields_type[short_fieldname] = cval.ttype if cval else False
            elif column._type == 'many2many':
                fields[short_fieldname] = [mapped_fieldname(x, target_relation)
                                           for x in calendar[fieldname]]
                fields_type[short_fieldname] = [x.ttype for x in calendar[fieldname]]
            else:
                raise osv.except_osv(_('Error!'),
                                     _('Unsupported virtual field "%s" using "%s" type of field') % (fieldname, column._type))

        states = {}
        states_reversed = {}
        for state in ['tentative', 'confirm', 'cancel']:
            cval = calendar['states_'+state] or ''
            source_states = [v.strip() for v in cval.split(',') if v.strip()]
            states[state] = source_states
            for s in source_states:
                states_reversed[s] = state

        return {
            'name': calendar.name,
            'model': calendar.model.model,
            'date_mode': calendar.date_mode,
            'states': states,  # map core.calendar.event state to model states
            'states_reversed': states_reversed,  # map model states to core.calendar.event state
            'fields': fields,
            'fields_type': fields_type,
            'filter_expr': calendar.filter_expr,
        }

    @tools.ormcache()
    def _get_calendar_for_model(self, cr, uid, model):
        return self.search(cr, uid, [('model', '=', model)])

    @tools.ormcache()
    def get_subscribed_ids(self, cr, uid):
        ModelAccess = self.pool.get('ir.model.access')
        # TODO: really filter on subscribed calendars
        # TODO: when implemented per calendar subscription - do not forget to invalidate this cache!
        available_calendar_ids = self.search(cr, uid, [])
        user_calendar_ids = []
        for calendar in self.browse(cr, uid, available_calendar_ids):
            model = calendar.model
            if ModelAccess.check(cr, uid, model, 'read', False):
                user_calendar_ids.append(calendar.id)
        return user_calendar_ids

    @logged
    def get_subscribed(self, cr, uid, context=None):
        ModelAccess = self.pool.get('ir.model.access')
        # TODO:
        # - checked: user-preference to store is we should display events from this calendar by default or not
        calendar_ids = self.get_subscribed_ids(cr, uid)
        calendar_fields = ['name', 'color', 'action_id', 'action_res_model', 'action_form_view_id', 'date_mode']
        result = self.read(cr, uid, calendar_ids, calendar_fields, context=context)
        for r in result:
            calinfo = self._get_calendar_info(cr, uid, r['id'])
            calendar_model = r['action_res_model']
            r['fields'] = calinfo['fields']
            r['fields_type'] = calinfo['fields_type']
            r['access'] = {}
            for mode in ['read', 'write', 'create', 'unlink']:
                r['access'][mode] = ModelAccess.check(cr, uid, calendar_model, mode, False)
        return result

    def _merge_m2m_search_args(self, cr, uid, args, context=None):
        if not args:
            return []
        root_model = self.pool.get('core.calendar.event')
        expr = expression.distribute_not(expression.normalize_domain(args))
        from pprint import pprint

        # merge m2m using the same field for correctness of query
        # --- [('attendee_ids.attentee_type','=','speaker'),('attendee_ids.attendee_external','=',False)]
        # ==> [('attendee_ids', 'in', SUBSELECT{[('attendee_type','=','speaker'),
        #                                        ('attendee_external','=',False)]})]

        def is_subselect_leaf(leaf):
            if isinstance(leaf, expression.ExtendedLeaf) and isinstance(leaf.leaf, (tuple, list)) and len(leaf.leaf) == 1:
                for v in leaf.leaf:
                    if len(v) == 3 and v[1] == 'subselect':
                        return True
            return False

        stack = [expression.ExtendedLeaf(leaf, root_model) for leaf in expr]

        class RecrExpression():
            def __init__(self, op, child=None):
                self.op = op
                self.child = child or []

            def display(self, indent=0):
                istr = ' '*(indent)
                jstr = ' '*(indent+4)
                k = ''
                for x in self.child:
                    if hasattr(x, 'display'):
                        k += jstr + x.display(indent+4) + '\n'
                    else:
                        k += jstr + str(x) + '\n'
                return '%s%s: [\n%s\n%s]' % (istr, self.op, k, istr)

            def add_child(self, leaf):
                if is_subselect_leaf(leaf):
                    for c in self.child:
                        if is_subselect_leaf(c) and c.leaf[0][0] == leaf.leaf[0][0]:
                            # merge two line
                            c.leaf[0][2].insert(0, self.op)
                            c.leaf[0][2].extend(leaf.leaf[0][2])
                            return True
                self.child.append(leaf)
                return True

            def __repr__(self):
                return self.display()

            def get_flatten(self):
                result = [self.op] * (len(self.child) - 1)
                for c in self.child:
                    if isinstance(c, RecrExpression):
                        result += c.get_flatten()
                    elif is_subselect_leaf(c):
                        field, op, args = c.leaf[0]
                        column = root_model._all_columns[field].column
                        work_model = root_model.pool.get(column.relation)
                        sub_ids = work_model.search(cr, uid, args, context=context)
                        result += [(field, 'in', sub_ids)]
                    else:
                        result += [c.leaf]
                return result

        # 1st
        rstack = []
        for leaf in reversed(stack):
            if leaf.is_operator():
                # take the two item on the stack
                n = RecrExpression(leaf.leaf)
                for x in [ rstack.pop(), rstack.pop() ]:
                    if isinstance(x, RecrExpression) and x.op == n.op:
                        for xc in x.child:
                            n.add_child(xc)
                    else:
                        n.add_child(x)
                rstack.append(n)
            else:
                field_path = leaf.leaf[0].split('.')
                field_column = root_model._all_columns[field_path[0]].column
                if len(field_path) > 1 and field_column._type == 'many2many':
                    field_subpath = '.'.join(field_path[1:])
                    leaf.leaf = [(field_path[0], 'subselect', [(field_subpath, leaf.leaf[1], leaf.leaf[2])])]
                rstack.append(leaf)

        # return args
        final_leaf = rstack[0]
        if not isinstance(final_leaf, RecrExpression):
            final_leaf = RecrExpression('&', child=[final_leaf])
        return final_leaf.get_flatten()

    # @logged
    def get_search_args(self, cr, uid, calendar_id, args, context=None):
        if not args:
            return []
        args = expression.normalize_domain(args)
        # print("MERGE M2M ARGS: %s" % (self._merge_m2m_search_args(cr, uid, args, context=context),))
        args = self._merge_m2m_search_args(cr, uid, args, context=context)
        # print("ARGS: %s" % (args,))
        calendar_info = self._get_calendar_info(cr, uid, calendar_id)
        calendar_event_obj = self.pool.get('core.calendar.event')
        calendar_model = self.pool.get(calendar_info['model'])
        # calendar = self.browse(cr, uid, calendar_id, context=context)
        calendar_id_filter = '%d-' % calendar_id
        # field_is_standard = ['id', 'date_start', 'name', 'organizer_id', 'location']
        field_is_standard = self._get_base_fields(cr, uid, context=context)
        # field_is_valid = field_is_standard + ['attendee_id', 'attendee_ids', 'state']
        field_is_valid = field_is_standard + self._get_extended_fields(cr, uid, context=context)
        expr = []
        for arg in args:
            if len(arg) == 3:
                field, op, val = arg
                field_extra = ''
                if '.' in field:
                    field, field_extra = field.split('.', 1)
                    field_extra = '.'+field_extra

                # expand related columns name
                columninfo = calendar_event_obj._all_columns.get(field)
                if columninfo and isinstance(columninfo.column, fields.related):
                    column = columninfo.column
                    field = column._arg[0]
                    if column.arg[1:]:
                        field_extra = '.' + '.'.join(column.arg[1:]) + field_extra

                field_realname = calendar_info['fields'].get(field)
                if field_realname and field in field_is_standard:
                    expr.append([field_realname + field_extra, op, val])
                elif field_is_valid and field == 'main_speaker_id':
                    if 'main_speaker_id' in calendar_model._all_columns:
                        expr.append(arg)
                    else:
                        expr.append(['id', '=', -1])
                elif field_is_valid and field in ('attendee_ids', 'attendee_id'):
                    JOIN_OP = '&' if arg[1] in expression.NEGATIVE_TERM_OPERATORS else '|'

                    def fix_id(x):
                        if hasattr(x, '__iter__'):
                            return [fix_id(xid) for xid in x]
                        elif isinstance(x, basestring) and x.isdigit():
                            return long(x)
                        return x
                    calendar_attendee_fields = calendar_info['fields']['attendee_ids'][:]
                    organizer_id_field = calendar_info['fields']['organizer_id']
                    if organizer_id_field and organizer_id_field not in calendar_attendee_fields:
                        calendar_attendee_fields.append(organizer_id_field)
                    # print("Attendee calendar fields: %s" % (calendar_attendee_fields,))
                    if calendar_attendee_fields:
                        domains = [[f + field_extra, arg[1], fix_id(arg[2])] for f in calendar_attendee_fields]
                        expr.extend([JOIN_OP] * (len(domains) - 1) + domains)
                    else:
                        expr.append(['id', '=', -1])
                elif field_is_valid and field == 'id':
                    if isinstance(val, (tuple, list)):
                        # filter only id related to this calendar
                        val = [v[len(calendar_id_filter):]
                               for v in val
                               if isinstance(v, basestring) and v.startswith(calendar_id_filter)]
                    elif isinstance(val, basestring):
                        if not val.startswith('%d-' % calendar_id):
                            val = -1  # TODO
                    expr.append(['id', op, val])
                elif field_is_valid and field == 'state' and calendar_info['fields']['state']:
                    states = []
                    if isinstance(arg[2], (list, tuple)):
                        for v in arg[2]:
                            states.extend(calendar_info['states'][v])
                    else:
                        states.extend(calendar_info['states'][arg[2]])
                    if op in ('=', '!='):
                        op = {'=': 'in', '!=': 'not in'}[op]
                    expr.append((calendar_info['fields']['state'], op, states))
                else:
                    expr.append(['id', '=', -1])  # return always false domain
            else:
                expr.append(arg)
        expr = expression.normalize_domain(expr)
        if calendar_info['filter_expr']:
            filter_expr = safe_eval(calendar_info['filter_expr'])
            filter_expr = expression.normalize_domain(filter_expr)
            expr[:0] = ['&'] + filter_expr
        return expr

    def create(self, cr, uid, values, context=None):
        nid = super(CoreCalendar, self).create(cr, uid, values, context=context)
        self.clear_caches()
        return nid

    def write(self, cr, uid, ids, values, context=None):
        rval = super(CoreCalendar, self).write(cr, uid, ids, values, context=context)
        self.clear_caches()
        return rval

    def unlink(self, cr, uid, ids, context=None):
        rval = super(CoreCalendar, self).unlink(cr, uid, ids, context=context)
        self.clear_caches()
        return rval


class CoreCalendarEvent(osv.Model):
    _name = 'core.calendar.event'
    _auto = True

    def _get_user_query(self, cr, uid, fields_to_read=None, attendee_list=False, context=None):
        if not fields_to_read:
            fields_to_read = self._all_columns.keys()
        if 'id' not in fields_to_read:
            fields_to_read.insert(0, 'id')
        if context is None:
            context = {}
        lang = context.get('lang') or 'en_US'

        def build_query(model, root_table, joins, where, fields):
            q = 'SELECT '
            q += ','.join("%s AS %s" % (f[1], f[0])
                          for f in fields)
            q += ' FROM %s AS %s' % (root_table[1], root_table[0])

            # TYPE, AS_TABLE, TABLE, TABLE_FIELD, SRC, SRC_FIELD
            # "LEFT JOIN" "TABLE" AS "AS_TABLE" ON ("AS_TABLE"."TABLE_FIELD" = "SRC"."SRC_FIELD")
            for j in joins:
                (join_type, table_alias,
                    base_table, base_field,
                    dest_table, dest_field) = j
                q += ' %s %s AS %s ON (%s.%s = %s.%s) ' % \
                    (join_type, dest_table, table_alias,
                        base_table, base_field,
                        table_alias, dest_field)

            if where:
                q += ' WHERE ' + ' AND '.join(where)
            return q

        unions = []
        Calendar = self.pool.get('core.calendar')
        for calendar_id in Calendar.get_subscribed_ids(cr, uid):
            cal = Calendar._get_calendar_info(cr, uid, calendar_id, lang)
            calfields = cal['fields']
            model = self.pool.get(cal['model'])

            root_table_alias = 't'
            root_table = (root_table_alias, '%s' % model._table)
            joins = [] # TYPE, AS_TABLE, TABLE, TABLE_FIELD, SRC, SRC_FIELD
                       # "LEFT JOIN" "TABLE" AS "AS_TABLE" ON ("AS_TABLE"."TABLE_FIELD" = "SRC"."SRC_FIELD")
            where = []
            fields = [
                ('id', "'%d-'||%s.id" % (calendar_id, root_table_alias)),
                ('model', "'%s'" % cr.mogrify(cal['model'])),
                ('calendar_id', '%d' % calendar_id),
                ('res_id', "%s.id" % root_table_alias),
                ('date_start', "%s.%s" % (root_table_alias, calfields['date_start'])),
            ]

            # Date Stop
            if calfields['date_end']:
                v = '%s.%s' % (root_table_alias, calfields['date_end'])
                fields.append(('date_end', v))
            else:
                v = "%s.%s + '1 hour'::interval * %s.%s" % \
                    (root_table_alias, calfields['date_start'],
                     root_table_alias, calfields['duration'])
                fields.append(('date_end', v))

            # Duration
            if calfields['duration']:
                v = '%s.%s' % (root_table_alias, calfields['duration'])
                fields.append(('duration', v))
            else:
                v = '%s.%s - %s.%s' % \
                    (root_table_alias, calfields['date_end'],
                     root_table_alias, calfields['date_start'])
                fields.append(('duration', v))

            # Attendees
            if calfields['attendee_ids']:
                attendee_parts = []
                # return an 'ARRAY[]' notation for each fields
                for field in calfields['attendee_ids']:
                    subfields = field.split('.')
                    sf = subfields.pop(0)
                    column = model._all_columns[sf].column
                    if column._type != 'many2one' and subfields:
                        raise osv.except_osv(
                            _('Error!'),
                            _('Sub-field notation FIELD_1.FIELD_2 is only allowed for many2one field'))
                    if column._type == 'many2many':
                        v = "ARRAY(SELECT %s FROM %s WHERE %s = %s.%s)" % \
                            (column._id2, column._rel, column._id1, root_table_alias, 'id')
                        attendee_parts.append(v)
                    elif column._type == 'many2one':
                        base_table = root_table_alias
                        base_field = sf
                        base_model = model
                        base_column = column
                        while subfields:
                            dest_field = subfields.pop(0)
                            dest_model = self.pool.get(base_column._obj)
                            dest_table = dest_model._table
                            dest_table_alias = '%s_%s' % (base_field, dest_table)
                            for j in joins:
                                if j[0] == 'LEFT JOIN' and j[1] == dest_table_alias:
                                    break   # already present
                            else:
                                joins.append(
                                    ('LEFT JOIN', dest_table_alias,
                                        root_table_alias, base_field,
                                        dest_table, 'id'),
                                )
                            # update datas and continue
                            base_table = dest_table_alias
                            base_field = dest_field
                            base_model = dest_model
                            base_column = dest_model._all_columns[dest_field].column
                        v = 'ARRAY[%s.%s]' % (base_table, base_field)
                        attendee_parts.append(v)
                attendee_query = '(%s)' % ' || '.join(attendee_parts)
                if attendee_list:
                    attendee_query = 'unnest%s' % attendee_query
                    # where.append('attendee_ids IS NOT NULL')
                fields.append(('attendee_ids', attendee_query))

            fs = [f for f in fields if f[0] in fields_to_read]
            q = build_query(model, root_table, joins, where, fs)
            unions.append(q)

        return "(%s)" % ' UNION ALL '.join(['(%s)' % q for q in unions])

    def _get_user_overlapping_events(self, cr, uid, filter_sets, context=None, count=False):
        union_all_fields = ['id', 'model', 'calendar_id', 'res_id',
                            'date_start', 'date_end', 'attendee_ids']
        union_all_query = self._get_user_query(cr, uid, union_all_fields,
                                               attendee_list=True, context=context)
        where_filter = []
        where_params = []
        for (model, ids) in filter_sets:
            if not ids:
                where_filter.append('a.model = %s')
                where_params.append(model)
            else:
                where_filter.append('a.model = %s AND a.res_id IN %s')
                where_params += [model, tuple(ids)]
        where_clause = ' AND ' + ' AND '.join(where_filter) if where_filter else ''

        query = """
            WITH events AS (%s)
            SELECT a.id, a.model, a.res_id, a.attendee_ids AS partner_id, b.id
            FROM events AS a
            LEFT JOIN events AS b ON (b.attendee_ids = a.attendee_ids
                                      AND a.calendar_id != b.calendar_id
                                      AND a.res_id != b.res_id
                                      AND (a.date_start, a.date_end) OVERLAPS (b.date_start, b.date_end))
            LEFT JOIN res_partner p ON (a.attendee_ids = p.id)
            WHERE p.avoid_double_allocation = true
              AND a.calendar_id != b.calendar_id AND a.res_id != b.res_id %s
        """ % (union_all_query, where_clause)
        cr.execute(query, where_params)
        result = []
        data = {}
        for r in cr.fetchall():
            if r[0] in data:
                data[r[0]]['overlapping_event_ids'].setdefault(r[4], []).append(r[3])
                continue
            v = {
                'id': r[0],
                'model': r[1],
                'res_id': r[2],
                'overlapping_event_ids': {}
            }
            v['overlapping_event_ids'].setdefault(r[4], []).append(r[3])
            data[v['id']] = v
            result.append(v)
        return result

    def _get_attendees(self, cr, uid, ids, field_name, args, context=None):
        return self._compute_attendees(cr, uid, ids, field_name, args, context=context)

    def _compute_attendees(self, cr, uid, ids, field_name, args, context=None):
        ids_by_calendar = self._group_ids_by_calendar(cr, uid, ids, context=context)
        result = {}
        for id in ids:
            result[id] = {
                'attendee_ids': [],
                'main_speaker_id': False,
            }

        all_attendee_ids = set()
        calendar_ids = self.get_calendars(cr, uid, ids_by_calendar.keys(), context=context)
        for calendar in self.pool.get('core.calendar').browse(cr, uid, calendar_ids, context=context):
            calendar_model = self.pool.get(calendar.model.model)
            calendar_ids = ids_by_calendar[calendar.id]

            fields = dict((x.name, (x.ttype, x.relation)) for x in calendar.field_attendee_ids)
            if not fields:
                continue

            for record in calendar_model.browse(cr, uid, calendar_ids, context=context):
                attendee_ids = set()
                for fname, (ftype, frelation) in fields.iteritems():
                    if ftype == 'many2one':
                        value = record[fname]
                        if value:
                            if frelation == 'res.users':
                                value = value.partner_id
                            attendee_ids.add(value.id)
                    elif ftype == 'many2many':
                        for r in record[fname]:
                            if frelation == 'res.users':
                                r = r.partner_id
                            attendee_ids.add(r.id)
                result['%s-%s' % (calendar.id, record['id'])]['attendee_ids'] = list(attendee_ids)
                all_attendee_ids |= attendee_ids

        # Filter attendee which are speakers
        Partner = self.pool.get('res.partner')
        speaker_domain = [
            ('attendee_type', '=', 'speaker'),
            ('id', 'in', list(all_attendee_ids))
        ]
        speaker_ids = Partner.search(cr, uid, speaker_domain, context=context)
        speaker_names = dict(Partner.name_get(cr, uid, speaker_ids, context=context))
        speaker_ids = set(speaker_ids)
        for _id in ids:
            spks = [x for x in result[_id]['attendee_ids'] if x in speaker_ids]
            if spks:
                result[_id]['main_speaker_id'] = (spks[0], speaker_names[spks[0]])

        return result

    def _get_attendee_id(self, cr, uid, ids, fieldname, args, context=None):
        return dict.fromkeys(ids, False)

    def _search_attendee_id(self, cr, uid, model, fieldname, domain, context=None):
        # print("Model; %s, fieldname: %s, domain: %s" % (model, fieldname, domain,))
        return []

    def _get_attendee_type(self, cr, uid, context=None):
        return self.pool.get('res.partner').fields_get(cr, uid, ['attendee_type'], context=context)['attendee_type']['selection']

    _state_selection = [
        ('tentative', 'Tentative'),
        ('confirm', 'Confirmed'),
        ('cancel', 'Cancelled'),
    ]

    _columns = {
        'id': fields.char('Id', size=None),
        'calendar_id': fields.many2one('core.calendar', 'Calendar', required=True),
#        'partner_id': fields.many2one('res.partner', 'Resource'),
        'name': fields.char('Event Name', required=True),
        'date_start': fields.datetime('Start date', required=True),
        'date_end': fields.datetime('End date', required=True),
        'duration': fields.float('Duration', required=True, readonly=True),
        'recurrent': fields.boolean('Recurrent', readonly=True),
        'organizer_id': fields.many2one('res.partner', 'Responsible', readonly=True,
                                          help='Responsible and/or Organizer person for this event'),
        'location': fields.char('Location', size=254, readonly=True,
                                 help="Location of this event"),
        'attendee_ids': fields.function(_get_attendees, type='many2many', relation='res.partner',
                                        string='Attendees', multi='attendees'),
        'main_speaker_id': fields.function(_get_attendees, type='many2one', relation='res.partner',
                                           string='Speaker', multi='attendees'),
        'state': fields.selection(_state_selection, 'State', readonly=True),
        'attendee_id': fields.function(_get_attendee_id, type='many2one', relation='res.partner',
                                       fnct_search=_search_attendee_id, string='Attendee'),
        'attendee_external': fields.related('attendee_id', 'attendee_external', type='boolean', string='Attendee External'),
        'attendee_type': fields.related('attendee_id', 'attendee_type', type='selection',
                                        selection=_get_attendee_type, readonly=True, string='Attendee Type'),
        'attendee_tags': fields.related('attendee_id', 'category_id', type='many2many',
                                        relation='res.partner.category', string='Attendee Tags'),
    }

    def default_get(self, cr, uid, fields_list, context=None):
        defaults = super(CoreCalendarEvent, self).default_get(cr, uid, fields_list,  context=context)
        # Compute automatic default values
        for f in fields_list:
            if f not in defaults:
                _type = self._all_columns[f].column._type
                if _type in ('char', 'text', 'html', 'selection', 'reference'):
                    defaults[f] = ''
                elif _type in ('integer',):
                    defaults[f] = 0
                elif _type in ('float',):
                    defaults[f] = 0.0
                elif _type in ('many2one', 'boolean', 'binary', 'date', 'datetime', 'many2many', 'one2many'):
                    defaults[f] = False
        return defaults

    def _group_ids_by_calendar(self, cr, uid, ids, context=None):
        if not isinstance(ids, (list, tuple)):
            ids = [ids]
        ids_by_calendar = defaultdict(list)
        for _id in ids:
            calendar_id, real_id = _id.split('-', 1)
            if real_id.isdigit():
                real_id = long(real_id)
            calendar_id = long(calendar_id)
            ids_by_calendar[calendar_id].append(real_id)
        return ids_by_calendar

    def get_subscribed_filters(self, cr, uid, context=None):
        return []

    def get_calendars(self, cr, uid, ids=None, context=None):
        if context is None:
            context = {}
        calendar_obj = self.pool.get('core.calendar')
        return ids if ids else calendar_obj.get_subscribed_ids(cr, uid)

    def create(self, cr, uid, values, context=None):
        raise Exception('You must call create() on related calendar model')

    #@logged
    def search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False):
        ids_by_calendar = []
        calendar_obj = self.pool.get('core.calendar')
        calendar_ids = self.get_calendars(cr, user, context=context)
        for calendar in calendar_obj.browse(cr, user, calendar_ids, context=context):
            # print("calendar: %s" % (calendar.name,))
            # print("raw args: %s" % (args,))
            calendar_args = calendar_obj.get_search_args(cr, user, calendar.id, args)
            # print("calendar args: %s" % (calendar_args,))
            calendar_model = self.pool.get(calendar.model.model)
            ids_by_calendar.append(['%s-%s' % (calendar.id, id)
                                    for id in calendar_model.search(cr, user, calendar_args, context=context)])
        # from pprint import pprint
        # pprint(ids_by_calendar)
        ids = flatten(ids_by_calendar)
        ids = ids[offset:limit or None]
        if count:
            return len(ids)
        return ids
        # return super(res_calendar_event, self).search(cr, user, args, offset=offset, limit=limit,
        #                                               order=order, context=context, count=count)

    #@logged
    def read(self, cr, user, ids, fields_to_read=None, context=None, load='_classic_read'):
        Calendar = self.pool.get('core.calendar')

        if context is None:
            context = {}
        if not fields_to_read or (isinstance(fields, (list, tuple)) and not fields):
            fields_to_read = self._columns.keys()

        fields_pre = []
        fields_post = []
        for f in fields_to_read:
            column = self._all_columns[f].column
            if isinstance(column, fields.function):
                fields_post.append(f)
            else:
                fields_pre.append(f)

        date_fields_requested = any(f in fields_pre for f in ['date_start', 'date_end', 'duration'])

        result = []
        record_defaults = self.default_get(cr, user, fields_to_read, context=context)

        for calendar_id, event_ids in self._group_ids_by_calendar(cr, user, ids, context=context).iteritems():
            calendar_info = Calendar._get_calendar_info(cr, user, calendar_id, context.get('lang'))
            calendar_model = self.pool.get(calendar_info['model'])
            calendar_fields = calendar_info['fields']
            byduration = True if calendar_info['date_mode'] == 'duration' else False

            model_fields_pre = fields_pre[:]
            if date_fields_requested:
                # ensure we read date fields - this is needed if we need to compute
                # automatically date_end / duration depending on calendar 'end date' mode
                model_fields_pre = list(set(model_fields_pre + ['date_start', 'date_end', 'duration']))
            calendar_fields_to_read = [x for x in flatten(calendar_fields.get(fld)
                                                          for fld in model_fields_pre)
                                       if x not in (None, False)]

            for val in calendar_model.read(cr, user, event_ids, calendar_fields_to_read, context=context):
                record = dict(record_defaults)
                record['id'] = '%s-%s' % (calendar_id, val['id'])
                # TODO: handle log_access columns read
                if 'calendar_id' in fields_pre:
                    record['calendar_id'] = (calendar_id, calendar_info['name'])
                if 'state' in fields_pre:
                    record['state'] = calendar_info['states_reversed'][val['state']] if val['state'] else False

                for f in fields_pre:
                    if f in ['id', 'calendar_id', 'state']:
                        continue
                    column = self._all_columns[f].column
                    if column._type in ('many2many', 'one2many'):
                        # multiple fields
                        values = []
                        if not isinstance(calendar_fields[f], (list, tuple)):
                            fields_list = [(calendar_info['fields'][f],
                                            calendar_info['fields_type'][f])]
                        else:
                            fields_list = zip(calendar_info['fields'][f],
                                              calendar_info['fields_type'][f])
                        for field_name, field_type in fields_list:
                            value = val[field_name]
                            if value:
                                if field_type in ('many2many',):
                                    values.extend(value)
                                elif field_type == 'many2one':
                                    values.append(value[0])
                                else:
                                    values.append(value)
                        record[f] = values
                    else:
                        field_name = calendar_info['fields'].get(f)
                        field_type = calendar_info['fields_type'].get(f)
                        if not field_name:
                            continue
                        if '.' in field_name:
                            fns = field_name.split('.')
                            fnb = calendar_model.browse(cr, user, val['id'], context=context)
                            fnb_root = fnb
                            while len(fns) > 1:
                                b = fns.pop(0)
                                fnb_root = fnb_root[b]
                            value = fnb_root.read([fns[0]], context=context)[0][fns[0]]
                        else:
                            value = val[field_name]
                        if value:
                            if field_type == 'many2one':
                                if column._type in 'integer':
                                    value = value[0]  # keep only the ID
                                elif column._type != 'many2one':
                                    value = value[1]  # we want textual value
                            record[f] = value

                if date_fields_requested:
                    value_dt_start = val.get(calendar_fields['date_start'])
                    if value_dt_start:
                        record_dt_start = datetime.strptime(value_dt_start, DT_FMT)
                        if byduration and 'date_end' in fields_pre:
                            duration = timedelta(hours=val[calendar_fields['duration']])
                            record['date_end'] = (record_dt_start + duration).strftime(DT_FMT)
                        elif not byduration and 'duration' in fields_pre:
                            record_dt_end = datetime.strptime(val[calendar_fields['date_end']], DT_FMT)
                            duration = (record_dt_end - record_dt_start)
                            record['duration'] = duration.days * 24. + duration.seconds / 3600.
                    else:
                        # not date start
                        if byduration and 'date_end' in fields_pre:
                            record['date_end'] = False
                        elif not byduration and 'duration' in fields_pre:
                            record['duration'] = 0.0
                result.append(record)

        # Compute POST fields
        todo = defaultdict(list)
        for f in fields_post:
            column = self._all_columns[f].column
            todo[column._multi].append(f)
        for key, val in todo.items():
            if key:
                res2 = self._columns[val[0]].get(cr, self, ids, val, user, context=context, values=result)
                assert res2 is not None, \
                    'The function field "%s" on the "%s" model returned None\n' \
                    '(a dictionary was expected).' % (val[0], self._name)
                for pos in val:
                    for record in result:
                        if isinstance(res2[record['id']], str): res2[record['id']] = eval(res2[record['id']]) #TOCHECK : why got string instend of dict in python2.6
                        multi_fields = res2.get(record['id'], {})
                        if multi_fields:
                            record[pos] = multi_fields.get(pos, [])
            else:
                for f in val:
                    res2 = self._columns[f].get(cr, self, ids, f, user, context=context, values=result)
                    for record in result:
                        if res2:
                            record[f] = res2[record['id']]
                        else:
                            record[f] = []

        return result


    @logged
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False):
        """
        Get the list of records in list view grouped by the given ``groupby`` fields

        :param cr: database cursor
        :param uid: current user id
        :param domain: list specifying search criteria [['field_name', 'operator', 'value'], ...]
        :param list fields: list of fields present in the list view specified on the object
        :param list groupby: fields by which the records will be grouped
        :param int offset: optional number of records to skip
        :param int limit: optional max number of records to return
        :param dict context: context arguments, like lang, time zone
        :param list orderby: optional ``order by`` specification, for
                             overriding the natural sort ordering of the
                             groups, see also :py:meth:`~osv.osv.osv.search`
                             (supported only for many2one fields currently)
        :return: list of dictionaries(one dictionary for each record) containing:

                    * the values of fields grouped by the fields in ``groupby`` argument
                    * __domain: list of tuples specifying the search criteria
                    * __context: dictionary with argument like ``groupby``
        :rtype: [{'field_name_1': value, ...]
        :raise AccessError: * if user has no read rights on the requested object
                            * if user tries to bypass access rules for read on the requested object

        """
        # TODO: implement offset, limit, orderby

        ids = self.search(cr, uid, domain, context=context)
        if not groupby:
            raise osv.except_osv(_('Error!'), _('groupby is empty'))
        groupby_field, groupby_sub = groupby[0], groupby[1:]
        groupby_column = self._all_columns[groupby_field].column
        groupby_type = groupby_column._type

        from collections import OrderedDict
        gb_records = OrderedDict()
        gb_records_rawval = {}
        for record in self.read(cr, uid, ids, [groupby_field], context=context):
            v = record[groupby_field]
            if groupby_type == 'many2one' and v:
                v = v[0]
            v = v or False
            gb_records_rawval[v] = record[groupby_field]

            if v not in gb_records:
                gb_records[v] = set()
            gb_records[v].add(record['id'])

        result = []
        for key, ids in gb_records.iteritems():
            result.append({
                '__context': {'group_by': groupby_sub},
                '__domain': domain + [(groupby_field, '=', key)],
                groupby_field: gb_records_rawval[key],
                '%s_count' % (groupby_field,): len(ids),
            })
        return result

    @logged
    def write(self, cr, uid, ids, values, context=None):
        Calendar = self.pool.get('core.calendar')

        ids_by_calendar = self._group_ids_by_calendar(cr, uid, ids, context=context)
        calendar_ids = self.get_calendars(cr, uid, ids_by_calendar.keys(), context=context)
        for calendar in self.pool.get('core.calendar').browse(cr, uid, calendar_ids, context=context):
            calendar_info = Calendar._get_calendar_info(cr, uid, calendar.id, context.get('lang'))
            item_ids = ids_by_calendar[calendar.id]
            calendar_model = self.pool.get(calendar.action_res_model)
            item_values = {}
            fields = []
            for k, v in values.iteritems():
                calfield = getattr(calendar, 'field_'+k, None)
                if calfield:
                    fields.append(k)
                    item_values[calfield.name] = v

            if all(calendar_info['fields'][f] for f in ['date_start', 'date_end', 'duration']):
                # all dates fields are directly writable - passthough
                vals = dict((calendar_info['fields'][f], values[f])
                            for f in ['date_start', 'date_end', 'duration']
                            if f in calendar_info['fields'] and f in values)
                calendar_model.write(cr, uid, item_ids, vals, context=context)
                continue

            byduration = calendar.date_mode == 'duration'
            datestart_fname = calendar.field_date_start.name

            if byduration:
                duration_fname = calendar.field_duration.name
                if 'duration' in values:
                    calendar_model.write(cr, uid, item_ids, item_values, context=context)
                elif 'date_start' in values:
                    start = datetime.strptime(values['date_start'], DT_FMT)
                    end = datetime.strptime(values['date_end'], DT_FMT)
                    duration = end - start
                    item_values[duration_fname] = duration.days * 24. + duration.seconds / 3600.
                    calendar_model.write(cr, uid, item_ids, item_values, context=context)
                else:
                    end = datetime.strptime(values['date_end'], DT_FMT)
                    for item in calendar_model.read(cr, uid, item_ids, [datestart_fname], context=context):
                        start = datetime.strptime(item[datestart_fname], DT_FMT)
                        duration = end - start
                        val = dict(item_values)
                        val[duration_fname] = duration.days * 24. + duration.seconds / 3600.
                        calendar_model.write(cr, uid, [item['id']], val, context=context)
            else:
                enddate_fname = calendar.field_date_end.name
                if 'date_end' in values:
                    calendar_model.write(cr, uid, item_ids, item_values, context=context)
                elif 'date_start' in values:
                    start = datetime.strptime(values['date_start'], DT_FMT)
                    end = start + timedelta(hours=values['duration'])
                    item_values[enddate_fname] = end.strftime(DT_FMT)
                    calendar_model.write(cr, uid, item_ids, item_values, context=context)
                else:
                    duration = timedelta(hours=values['duration'])
                    for item in calendar_model.read(cr, uid, item_ids, [datestart_fname], context=context):
                        start = datetime.strptime(item[datestart_fname], DT_FMT)
                        end = start + duration
                        val = dict(item_values)
                        val[enddate_fname] = end.strftime(DT_FMT)
                        calendar_model.write(cr, uid, [item['id']], val, context=context)
        # TODO: handler write for date_start/date_end/duration to fallback to model write
        #       -- note: this is used when move a event on the agenda view
        return True  # stub
        # return super(res_calendar_event, self).write(cr, uid, values, context=context)

    @logged
    def unlink(self, cr, uid, ids, context=None):
        ids_by_calendar = self._group_ids_by_calendar(cr, uid, ids, context=context)
        calendar_ids = self.get_calendars(cr, uid, ids_by_calendar.keys(), context=context)
        for calendar in self.pool.get('core.calendar').browse(cr, uid, calendar_ids, context=context):
            item_ids = ids_by_calendar[calendar.id]
            calendar_model = self.pool.get(calendar.action_res_model)
            calendar_model.unlink(cr, uid, item_ids, context=context)
        return True  # stub
        # return super(res_calendar_event, self).unlink(cr, uid, ids, context=context)
