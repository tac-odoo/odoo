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

import re
from openerp.osv import osv, fields
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp


class EventCourseSubject(osv.Model):
    _name = 'event.course.subject'
    _columns = {
        'name': fields.char('Subject Name', size=64, required=True),
        'color': fields.integer('Color Index'),
        'description': fields.text('Description'),
        'parent_id': fields.many2one('event.course.subject', 'Parent Subject'),
    }

    def name_get(self, cr, uid, ids, context=None):
        """ return course subject text representation - include their parents"""
        if context is None:
            context = {}
        result = []
        for subject in self.browse(cr, uid, ids, context=context):
            subject_repr_parts = [subject.name]
            s = subject.parent_id
            while s and not context.get('short_desc'):
                subject_repr_parts.insert(0, s.name)
                s = s.parent_id
            result.append((subject.id, ' / '.join(subject_repr_parts)))
        return result

    def _recursion_message(self, cr, uid, ids, context=None):
        return _('Error! You can not create recursive subjects')

    _constraints = [
        (osv.Model._check_recursion, _recursion_message, ['parent_id']),
    ]


class EventCourse(osv.Model):
    _name = 'event.course'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    _course_states = [
        ('draft', 'Unreviewed'),
        ('review', 'Under review'),
        ('validated', 'Validated'),
        ('deprecated', 'Deprecated'),
    ]

    def _compute_price(self, cr, uid, ids, name, args, context=None):
        if context is None:
            context = {}
        partner_id = context.get('partner_id')
        partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context) if partner_id else False
        speakerinfo = self.pool.get('event.course.speakerinfo')

        result = dict.fromkeys(ids, 0.0)
        for course in self.browse(cr, uid, ids, context=context):
            price = course.standard_price
            if partner and partner.speaker:
                custom_price_domain = [('course_id', '=', course.id),
                                       ('speaker_id', '=', partner.id)]
                custom_price_ids = speakerinfo.search(cr, uid, custom_price_domain, context=context)
                if custom_price_ids:
                    price = speakerinfo.browse(cr, uid, custom_price_ids[0], context=context).price
            result[course.id] = price
        return result

    def _get_speaker_id(self, cr, uid, ids, fieldname, args, context=None):
        return dict.fromkeys(ids, False)

    def _search_speaker_id(self, cr, uid, model, fieldname, args, context=None):
        search_op, search_value = None, None
        for a in args:
            if isinstance(a, (list, tuple)) and len(a) == 3 and a[0] == 'speaker_id':
                search_op = a[1]
                search_value = a[2]
                break
        if search_op is not None:
            if search_op == '=':
                return [('speakerinfo_ids.speaker_id', 'in', [search_value])]
        return []

    _columns = {
        'name': fields.char('Course Name', size=64, required=True),
        'code': fields.char('Internal reference', size=16),
        'lang_id': fields.many2one('res.lang', 'Language', required=True),
        'user_id': fields.many2one('res.users', 'Responsible'),
        'duration': fields.float('Duration'),
        'active': fields.boolean('Active'),
        'description': fields.text('Description', help='Some notes on the course'),
        # 'category_ids': fields.many2many('event.category', string='Categories', id1='course_id', id2='category_id'),
        'subject_id': fields.many2one('event.course.subject', 'Subject'),
        'level_id': fields.many2one('event.level', 'Level'),
        'material_ids': fields.one2many('event.course.material', 'course_id', 'Materials'),
        'material_note': fields.text('Note on Material', help='Some notes on the course materials'),
        'color': fields.integer('Color Index'),
        'state': fields.selection(_course_states, 'State', readonly=True),
        'standard_price': fields.float('Cost', digits_compute=dp.get_precision('Product Price')),
        'price': fields.function(_compute_price, type='float', string='Purchase Price',
                                 digits_compute=dp.get_precision('Product Price')),
        'speakerinfo_ids': fields.one2many('event.course.speakerinfo', 'course_id', 'Speaker Infos'),
        'speaker_id': fields.function(_get_speaker_id, type='many2one', relation='res.partner',
                                      fnct_search=_search_speaker_id, string="Speaker"),

        # Planification preferences
        'split_by': fields.float('Split by', help=(
            'Split the course by the specified duration. '
            'Use 0 to automatically split following calendar slot')),
        'room_category_ids': fields.many2many('res.partner.category', id1='course_id', id2='room_category_id', string='Prefered room types'),
        'constraint_ids': fields.many2many('event.constraint', id1='course_id', id2='constraint_id', string='Constraints'),
    }

    def _default_lang_id(self, cr, uid, context=None):
        if context is None:
            context = {}
        Users = self.pool.get('res.users')
        Lang = self.pool.get('res.lang')
        lang = context.get('lang') or Users.browse(cr, uid, uid, context=context).lang or 'en_US'
        lang_ids = Lang.search(cr, uid, [('code', '=', lang)], context=context)
        if lang_ids:
            return lang_ids[0]
        return False

    _defaults = {
        'lang_id': _default_lang_id,
        'active': True,
        'duration': 1.0,
        'state': 'draft',
    }

    def onchange_subject(self, cr, uid, ids, subject_id, context=None):
        values = {}
        if subject_id:
            Subject = self.pool.get('event.course.subject')
            subj = Subject.browse(cr, uid, subject_id, context=context)
            values.update(color=subj.color)
        return {'value': values}

    def button_draft(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'draft'}, context=context)

    def button_validate(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'validated'}, context=context)

    def button_deprecate(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'deprecated'}, context=context)

    def create(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        subject_id = values.get('subject_id') or context.get('default_subject_id')
        if subject_id and not values.get('color'):
            Subject = self.pool.get('event.course.subject')
            subj = Subject.browse(cr, uid, subject_id, context=context)
            values['color'] = subj.color
        return super(EventCourse, self).create(cr, uid, values, context=context)

    def write(self, cr, uid, ids, values, context=None):
        if values.get('subject_id') and not values.get('color'):
            Subject = self.pool.get('event.course.subject')
            subj = Subject.browse(cr, uid, values['subject_id'], context=context)
            values['color'] = subj.color
        return super(EventCourse, self).write(cr, uid, ids, values, context=context)

    def name_create(self, cr, uid, name, context=None):
        name = name or ''
        parts = []
        hours_re = re.compile('\W*(\d+:\d+)\W*')
        duration = None
        for n in name.split():
            match = hours_re.match(n)
            if match:
                h, m = [int(x) for x in match.groups()[0].split(':')]
                duration = h + m / 60.
            else:
                parts.append(n)
        values = {'name': ','.join(parts)}
        if duration is not None:
            values['duration'] = duration
        print("values: %s" % (values,))
        rec_id = self.create(cr, uid, values, context)
        return self.name_get(cr, uid, [rec_id], context)[0]


class EventCourseSpeakerInfo(osv.Model):
    _name = 'event.course.speakerinfo'

    _prices_from_selection = [
        ('course', 'Course Price'),
        ('custom', 'Custom Price'),
    ]

    def _get_price(self, cr, uid, ids, name, args, context=None):
        result = {}
        for speakerinfo in self.browse(cr, uid, ids, context=context):
            if speakerinfo.price_from == 'course':
                result[speakerinfo.id] = speakerinfo.course_id.standard_price
            else:
                result[speakerinfo.id] = speakerinfo.standard_price
        return result

    def _set_price(self, cr, uid, id, name, value, args, context=None):
        speakerinfo = self.browse(cr, uid, id, context=context)
        if speakerinfo.price_from == 'custom':
            self.write(cr, uid, [id], {'standard_price': value}, context=context)

    _columns = {
        'course_id': fields.many2one('event.course', 'Course', required=True, ondelete='cascade'),
        'speaker_id': fields.many2one('res.partner', 'Speaker', required=True, domain=[('speaker', '=', True)], ondelete='cascade'),
        'price_from': fields.selection(_prices_from_selection, 'Price From', required=True),
        'standard_price': fields.float('Custom Cost', digits_compute=dp.get_precision('Product Price')),
        'price': fields.function(_get_price, type='float', digits_compute=dp.get_precision('Product Price'),
                                 fnct_inv=_set_price, string='Price'),
    }
    _defaults = {
        'price_from': 'course',
    }

    _sql_constraints = [
        ('uniq_course_speaker', 'UNIQUE(course_id, speaker_id)', 'Couple course/speaker must be unique'),
    ]


class EventCourseMaterial(osv.Model):
    _name = 'event.course.material'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _inherits = {
        'ir.attachment': 'attachment_id',
    }

    _material_states = [
        ('draft', 'Unreviewed'),
        ('review', 'Under review'),
        ('validated', 'Validated'),
        ('deprecated', 'Deprecated'),
    ]

    _columns = {
        'attachment_id': fields.many2one('ir.attachment', 'Attachment', required=True, ondelete='restrict'),
        'course_id': fields.many2one('event.course', 'Course',
                                     help='If no course is specified, this material will be available on all courses'),
        'res_id': fields.related('course_id', 'id', type='integer', string='Resource ID', readonly=True, store=True),
        'state': fields.selection(_material_states, 'State', required=True, readonly=True),
    }
    _defaults = {
        'res_model': 'event.course',
        'state': 'draft',
    }


class EventEvent(osv.Model):
    _inherit = 'event.event'
    _columns = {
        'subject_id': fields.many2one('event.course.subject', 'Subject'),
        'course_id': fields.many2one('event.course', 'Course'),
    }


class EventContent(osv.Model):
    _inherit = 'event.content'
    _columns = {
        'course_id': fields.many2one('event.course', 'Course'),
        'subject_id': fields.related('course_id', 'subject_id', type='many2one',
                                     string='Subject', relation='event.course.subject'),
    }

    def onchange_content_course(self, cr, uid, ids, course_id, slot_duration, context=None):
        values = {}
        if course_id:
            course = self.pool.get('event.course').browse(cr, uid, course_id, context=context)
            default_slot_duration = self.default_get(cr, uid, ['slot_duration'], context=context)['slot_duration']
            slot_duration = course.duration if course.duration < slot_duration else default_slot_duration
            values.update(name=course.name,
                          duration=course.duration,
                          slot_duration=slot_duration,
                          lang_id=course.lang_id.id)
        return {'value': values}

    def _prepare_seance_for_content(self, cr, uid, content, date_begin, date_end, group=None, context=None):
        values = super(EventContent, self)._prepare_seance_for_content(cr, uid, content, date_begin, date_end, group=group, context=context)
        if content.course_id:
            values['course_id'] = content.course_id.id
        return values


class EventSeance(osv.Model):
    _inherit = 'event.seance'
    _columns = {
        'course_id': fields.many2one('event.course', 'Course'),
        'subject_id': fields.related('course_id', 'subject_id', type='many2one',
                                     relation='event.course.subject',
                                     string='Subject', readonly=True),
    }
