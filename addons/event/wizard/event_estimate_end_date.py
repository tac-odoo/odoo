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

import logging
from itertools import chain
from collections import defaultdict
from osv import osv, fields
from openerp.addons.resource.faces import task as Task
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DT_FMT
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as D_FMT
from datetime import time, datetime, timedelta


def face_quoted(arg, quote="'"):
    return "%s%s%s" % (quote, arg, quote)


def face_new_def(base_name, id, *args, **kwargs):
    return face_new_obj('def', base_name, id, *args, **kwargs)


def face_new_class(base_name, id, *args, **kwargs):
    return face_new_obj('class', base_name, id, *args, **kwargs)


def face_new_obj(obj_type, base_name, id, *args, **kwargs):
    face_type = kwargs.pop('face_type', None) or ''
    indent = " " * (kwargs.pop('indent', None) or 0)
    subindent = indent+" "*4
    return '\n'.join(chain(
        [indent + '%s %s_%s(%s):' % (obj_type, base_name, id, face_type)],
        (subindent + a for a in args),
        (subindent + '%s = %s' % (k, v) for k, v in kwargs.iteritems()),
        ['\n'],
    ))


class event_event_estimate_end_date_wizard(osv.osv_memory):
    """ Estimate End Date Wizard """
    _name = 'event.event.estimate_end_date.wizard'
    _rec_name = "event_id"

    def _get_task_def(self, cr, uid, event, component, depends=None, indent=0, context=None):
        """ Returns the task definitio corresponding to a component components of an event
            for the faces code used to compute the end date of an event """
        calendar_id = event.calendar_id
        slot_duration = calendar_id and calendar_id.slot_duration or 4
        content_performed_dates = (
            "(Content_%s, dt.strptime(%s, %s), dt.strptime(%s, %s), %s)" % (
                s.content_id.id, face_quoted(s.date_begin), face_quoted(DT_FMT),
                face_quoted((datetime.strptime(s.date_begin, DT_FMT)+timedelta(hours=s.duration)).strftime(DT_FMT)),
                face_quoted(DT_FMT), slot_duration)
            for s in component.seance_ids
        )

        start = 'up.start'
        if depends:
            start = 'max(%s)' % ','.join([start] + ['up.Task_%s.end' % d for d in depends])
        task_args = dict(
            indent=indent,
            effort=face_quoted('%sH' % component.duration),
            todo=face_quoted('%sH' % component.remaining_duration),
            resource='Content_%s' % component.id,
            # for courses, only a certain number of slots per week can be used. the weekly load is:
            #       number of slots * length of a slot.
            # load='DailyMax("%sH")' % (component.consecutive_event_count * slot_duration,),
            performed='[%s]' % (', '.join(content_performed_dates,)),
            start=start,
        )
        from pprint import pprint
        pprint(task_args)
        return face_new_def('Task', component.id, **task_args)

    def _compute_end_date(self, cr, uid, event_id, date_start, context=None):
        """ Returns the estimated end date of an event. This is computed using faces. """
        logger = logging.getLogger('estimate.end.date')
        resource_obj = self.pool.get('resource.resource')
        event = self.pool.get('event.event').browse(cr, uid, event_id, context=context)

        calendar_id = event.calendar_id
        slot_duration = calendar_id and calendar_id.slot_duration or 4
        working_days = resource_obj.compute_working_calendar(cr, uid, calendar_id.id, context=context)
        # Code = Header + Resource Definitions + Project Definition
        code = ""

        # header (imports and main project definition) for the faces code
        code += ("from openerp.addons.resource.faces import *\n"
                 "import datetime\n"
                 "from datetime import datetime as dt\n"
                 "\n")
        # resource: each content has an associated resource, for timing constraints
        for content in event.content_ids:
            code += face_new_class('Content', content.id, 'pass', face_type='Resource', indent=0)

        # project definition
        calendar_id = event.calendar_id

        format_date_start = D_FMT if len(date_start) <= 10 else DT_FMT
        project_start = 'dt.strptime(%s, %s)' % (face_quoted(date_start), face_quoted(format_date_start))

        code += face_new_def('Project', event.id, indent=0,
                             start=project_start,
                             working_days=working_days)

        # compute content definition
        contents = defaultdict(lambda: {'depends': set(), 'rdepends': set(), 'order': 0})
        for i, content in enumerate(event.content_ids):
            contents[content.id].update(id=content.id, name=content.name, order=i)
            # for prec in content.preceding_content_ids:
            #     contents[content.id]['depends'].add(prec.id)
            #     contents[prec.id]['rdepends'].add(content.id)

        # task: each content has an associated task that will be scheduled
        for content in event.content_ids:
            deps = contents[content.id]['depends']
            code += self._get_task_def(cr, uid, event, content, depends=deps, indent=4, context=context)

        code += "proj = BalancedProject(Project_%s)\n" % (event.id)
        code += "proj = AdjustedProject(proj)\n"
        # print(code)

        # "Magic" that executes the faces code
        try:
            local_dict = {}
            exec code in local_dict
            project_gantt = local_dict['proj']

            # the estimated end date is the maximum of the end dates of the components
            if not event.content_ids:
                computed_max_end_date = event.date_begin
            else:
                computed_max_end_date = max((
                    getattr(project_gantt, 'Task_%s' % (c.id)).end.strftime(DT_FMT)
                    for c in event.content_ids
                ))
        except Exception:
            logger.debug('something strange faces computation # code: %s' % (code,))
            computed_max_end_date = event.date_begin

        existing_child_event_dates = []
        for s in event.seance_ids:
            end = (datetime.strptime(s.date_begin, DT_FMT) + timedelta(s.duration)).strftime(DT_FMT)
            existing_child_event_dates.append(end)
        return max([date_start, computed_max_end_date] + existing_child_event_dates)

    def button_compute_date_end(self, cr, uid, ids, context=None):
        if not ids:
            return True
        wizard = self.browse(cr, uid, ids[0], context=context)
        date_end = self._compute_end_date(cr, uid, wizard.event_id.id, wizard.date_start, context=context)
        wizard.write({'date_end': date_end})

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': wizard.id,
        }

    _columns = {
        'event_id': fields.many2one('event.event', 'Event', readonly=True),
        'date_start': fields.date('Start on', required=True),
        'date_end': fields.date('End on', readonly=True),
    }

    def _default_event_id(self, cr, uid, context=None):
        if context is None:
            context = {}
        if context.get('active_model', '') == 'event.event' and context.get('active_id'):
            return context['active_id']
        return False

    _defaults = {
        'event_id': _default_event_id,
        'date_start': fields.date.today,
    }
