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
from openerp.tools.translate import _


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

    _columns = {
        'name': fields.char('Course Name', size=64, required=True),
        'lang_id': fields.many2one('res.lang', 'Language', required=True),
        'duration': fields.float('Duration'),
        'active': fields.boolean('Active'),
        'description': fields.text('Description', help='Some notes on the course'),
        # 'category_ids': fields.many2many('event.category', string='Categories', id1='course_id', id2='category_id'),
        'subject_id': fields.many2one('event.course.subject', 'Subject'),
        'material_ids': fields.one2many('event.course.material', 'course_id', 'Materials'),
        'material_note': fields.text('Note on Material', help='Some notes on the course materials'),
        'color': fields.integer('Color Index'),
        'state': fields.selection(_course_states, 'State', readonly=True),
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
        return {}

    def button_draft(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'draft'}, context=context)

    def button_validate(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'validated'}, context=context)

    def button_deprecate(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'deprecated'}, context=context)


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
    }

    def onchange_content_course(self, cr, uid, ids, course_id, context=None):
        values = {}
        if course_id:
            course = self.pool.get('event.course').browse(cr, uid, course_id, context=context)
            values.update(name=course.name, duration=course.duration)
        return {'value': values}
