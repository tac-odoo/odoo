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

import logging
from openerp.osv import osv, fields


class EventScoring(osv.Model):
    _name = 'event.scoring'

    MODES_SELECTION = [
        ('percentage', 'Percentage'),
        ('point', 'Point'),
    ]

    _columns = {
        'name': fields.char('Scoring Name', size=48, required=True),
        'mode': fields.selection(MODES_SELECTION, 'Mode', required=True),
        'level_ids': fields.one2many('event.scoring.level', 'scoring_id', 'Levels'),
    }

    _defaults = {
        'mode': 'percentage',
    }


class EventScoringLevel(osv.Model):
    _name = 'event.scoring.level'
    _order = 'level asc'
    _columns = {
        'scoring_id': fields.many2one('event.scoring', 'Scoring', required=True),
        'name': fields.char('Level name', size=32, required=True),
        'level': fields.float('Level',
            help='Points of pourcentage representing the low score/pourcentage to reach this level'),
        'pass': fields.boolean('Pass',
            help='If checked, this means this level should be considered as succeeded'),
    }


class EventQuestionnaire(osv.Model):
    _name = 'event.questionnaire'

    STATES_SELECTION = [
        ('draft', 'Draft'),
        ('valid', 'Validated'),
        ('deprecated', 'Deprecated'),
    ]

    _columns = {
        'name': fields.char('Questionnaire Name', size=128, required=True),
        'reference': fields.char('Ref.', size=32),
        'lang_id': fields.many2one('res.lang', 'Language'),
        'version': fields.integer('Version', readonly=True),
        'main_course_id': fields.many2one('event.course', 'Main Course'),
        'scoring_id': fields.many2one('event.scoring', 'Scoring', required=True),
        'line_ids': fields.one2many('event.questionnaire.line', 'questionnaire_id', 'Lines'),
        'question_ids': fields.one2many('event.questionnaire.line', 'questionnaire_id', 'Questions',
                                        domain=[('type', '=', 'question')], readonly=True),
        'state': fields.selection(STATES_SELECTION, 'State', required=True),

        # TODO: course_ids
        # TODO: domain_ids
        # TODO: attachment_ids
    }

    def _default_scoring_id(self, cr, uid, context=None):
        Scoring = self.pool.get('event.scoring')
        scoring_ids = Scoring.search(cr, uid, [], context=context)
        return scoring_ids[0] if scoring_ids else False

    _defaults = {
        'version': 0,
        'state': 'draft',
        'scoring_id': _default_scoring_id,
    }


class EventContent(osv.Model):
    _inherit = 'event.content'
    _columns = {
        'is_exam': fields.related('type_id', 'is_exam', type='boolean',
                                  string='Is Exam', readonly=True),
        'questionnaire_ids': fields.many2many('event.questionnaire', id1='content_id', id2='questionnaire_id',
                                             string='Default questionnaires'),
    }

    def onchange_type(self, cr, uid, ids, type_id, context=None):
        changes = super(EventContent, self).onchange_type(cr, uid, ids, type_id, context=context)
        is_exam = False
        if type_id:
            SeanceType = self.pool.get('event.seance.type')
            is_exam = SeanceType.browse(cr, uid, type_id, context=context).is_exam
        changes['value']['is_exam'] = is_exam
        return changes

    def _prepare_seance_for_content(self, cr, uid, content, date_begin, date_end, group=None, context=None):
        values = super(EventContent, self)._prepare_seance_for_content(cr, uid, content, date_begin, date_end,
                                                                       group=group, context=context)
        if content.type_id and content.type_id.is_exam:
            values.update(is_exam=True,
                          questionnaire_ids=[(6, 0, [q.id for q in content.questionnaire_ids])])
        return values


class EventQuestionnaireLine(osv.Model):
    _name = 'event.questionnaire.line'
    _order = 'questionnaire_id, sequence, id'

    TYPES_SELECTION = [
        ('question', 'Question'),
        ('pagebreak', 'Page Break'),
        ('text', 'Text'),
    ]

    _columns = {
        'sequence': fields.integer('Sequence'),
        'questionnaire_id': fields.many2one('event.questionnaire', 'Questionnaire', required=True, ondelete='cascade'),
        'type': fields.selection(TYPES_SELECTION, 'Type', required=True),
        'question_id': fields.many2one('event.question', 'Question'),
        'points': fields.related('question_id', 'points', type='float', string='Points'),
        'points_no_answer': fields.related('question_id', 'points_no_answer', type='float', string='Points (No answer)'),
        'body': fields.text('Text Body'),
    }

    _defaults = {
        'type': 'question',
    }

    _sql_constraints = [
        ('questline_question_required',
            "CHECK(CASE WHEN type = 'question' THEN question_id IS NOT NULL ELSE True END)",
            "Question field is required for type 'Question'"),
    ]


class EventQuestion(osv.Model):
    _name = 'event.question'

    TYPES_SELECTION = [
        ('qcu', 'Unique choice'),
        ('qcm', 'Multiple choice'),
        ('plain', 'Plain response'),
        ('yesno', 'Yes/No'),
    ]

    POINTS_FROM_SELECTION = [
        ('question', 'Question'),
        ('answers', 'Answers'),
    ]

    IMAGE_POSITIONS_SELECTION = [
        ('before', "Before Question's Text"),
        ('after', "After Question's Text"),
    ]

    STATES_SELECTION = [
        ('draft', 'Draft'),
        ('valid', 'Validated'),
        ('deprecated', 'Deprecated'),
    ]

    LEVELS_SELECTION = [
        (0, 'Super easy'),
        (1, 'Easy'),
        (2, 'Normal'),
        (3, 'Hard'),
        (4, 'Super hard'),
    ]

    def _get_points(self, cr, uid, ids, fieldname, args, context=None):
        if not ids:
            return {}
        # cache current stored value
        cr.execute("SELECT id, points "
                   "FROM event_question "
                   "WHERE id IN %s",
                   (tuple(ids),))
        points_cache = dict(cr.fetchall())

        result = {}
        for question in self.browse(cr, uid, ids, context=context):
            if question.points_from == 'answers':
                # TODO: compute points from answers
                result[question.id] = 0
            else:
                result[question.id] = points_cache.get(question.id) or 0.0
        return result

    def _set_points(self, cr, uid, id, fieldname, value, args, context=None):
        l = logging.getLogger('event.question')
        l.debug('set points to %s for id: %s' % (value, id,))
        cr.execute("UPDATE event_question SET points = %s WHERE id = %s", (value, id,))
        return True

    def _store_get_questions_self(self, cr, uid, ids, context=None):
        return ids

    def _store_get_questions_from_answers(self, cr, uid, ids, context=None):
        Questions = self.pool.get('event.question')
        Answers = self.pool.get('event.question.answer')
        question_ids = set(x['question_id'][0]
                           for x in Answers.read(cr, uid, ids, ['question_id'], context=context))
        filter_domain = [
            ('id', 'in', list(question_ids)),
            ('points_from', '=', 'answers'),
        ]
        return Questions.search(cr, uid, filter_domain, context=context)

    _columns = {
        'name': fields.char('Question Name', size=128, required=True),
        'reference': fields.char('Ref.', size=32),
        'lang_id': fields.many2one('res.lang', 'Language',
            help='Language of the question'),
        'version': fields.integer('Version', readonly=True),
        'type': fields.selection(TYPES_SELECTION, 'Type', required=True),
        'level': fields.selection(LEVELS_SELECTION, 'Level'),
        'text': fields.text('Question Text', required=True),

        # options
        'duration': fields.float('Duration',
            help='Maxium time allowed to respond to this question'),
        'is_mandatory': fields.boolean('Mandatory'),
        'is_eliminatory': fields.boolean('Eliminatory'),  # implies is_mandatory = True

        'points_from': fields.selection(POINTS_FROM_SELECTION, 'Count points from', required=True),
        'points_no_answer': fields.float('Points (No answer)',
            help=('Number of points to give if user did not answer this question. '
                  'Use negative number to give penalities for not answering this question')),
        'points': fields.function(_get_points, type='float', string='Points',
                                  fnct_inv=_set_points, store={
                                      'event.question': (_store_get_questions_self, ['points_from', 'answer_ids'], 10),
                                      'event.question.answer': (_store_get_questions_from_answers, [], 10),
                                  }),

        'has_image': fields.boolean('Image'),
        'image': fields.binary('Image Data'),
        'image_position': fields.selection(IMAGE_POSITIONS_SELECTION, 'Image Position', required=True,
            help="Image position relatively to question's text"),

        'answer_ids': fields.one2many('event.question.answer', 'question_id', 'Answers'),
        'text_free_lines_count': fields.integer('Free lines count',
            help='Number of free lines to display for response'),


        'course_ids': fields.many2many('event.course', id1='question_id', id2='course_id', string='Courses',
            help='Courses related to this question'),
        'domain_ids': fields.many2many('event.question.domain', id1='question_id', id2='domain_id', string='Domains',
            help='Domains related to this question'),
        # course_ids
        # competency_ids
        'state': fields.selection(STATES_SELECTION, 'State', required=True, readonly=True),
    }

    _defaults = {
        'type': 'qcu',
        'points_from': 'question',
        'points_no_answer': 0,
        'level': 2,  # normal
        'duration': 10. / 60.,
        'points': 1.0,
        'image_position': 'after',
        'state': 'draft',
    }


class EventQuestionAnswer(osv.Model):
    _name = 'event.question.answer'
    _rec_name = 'text'
    _order = 'question_id, sequence, id'
    _columns = {
        'sequence': fields.integer('Sequence'),
        'question_id': fields.many2one('event.question', 'Question', required=True),
        'text': fields.text('Text'),
        'is_solution': fields.boolean('Solution'),
        'point_checked': fields.float('Points (checked)'),
        'point_unchecked': fields.float('Points (unchecked)'),
    }


class EventQuestionDomain(osv.Model):
    _name = 'event.question.domain'
    _columns = {
        'name': fields.char('Domain Name', size=64, required=True),
        'description': fields.text('Description'),
        'parent_id': fields.many2one('event.question.domain', 'Parent Domain'),
    }

    # TODO: add specific name_get() to display parenting level


class EventDegree(osv.Model):
    _name = 'event.degree'

    STATES_SELECTION = [
        ('draft', 'Draft'),
        ('valid', 'Validated'),
        ('deprecated', 'Deprecated'),
    ]

    def _get_degree_stats(self, cr, uid, ids, fieldname, args, context=None):
        result = {}
        if isinstance(fieldname, (list, tuple)):
            for id in ids:
                result[id] = dict((f, 0) for f in fieldname)
        else:
            result = dict.fromkeys(ids, 0)
        return result

    _columns = {
        'name': fields.char('Degree Name', size=64, required=True),
        'course_ids': fields.many2many('event.course', id1='degree_id', id2='course_id', string='Courses'),
        'lang_id': fields.many2one('res.lang', 'Language', required=True),
        'active': fields.boolean('Active'),
        'desired_count': fields.function(_get_degree_stats, type='integer', string='# of desired', multi='degree-stats'),
        'eligible_count': fields.function(_get_degree_stats, type='integer', string='# of eligible', multi='degree-stats'),
        'acquired_count': fields.function(_get_degree_stats, type='integer', string='# of acquired', multi='degree-stats'),
        'state': fields.selection(STATES_SELECTION, 'State', required=True, readonly=True),
    }

    _defaults = {
        'active': True,
    }


class EventDegreeContact(osv.Model):
    _name = 'event.degree.contact'

    STATES_SELECTION = [
        ('desired', 'Desired'),
        ('eligible', 'Eligible'),
        ('acquired', 'Acquired'),
    ]

    def _get_all_exams(self, cr, uid, ids, fieldname, args, context=None):
        result = {}
        if not ids:
            return result
        if isinstance(fieldname, (list, tuple)):
            for id in ids:
                result[id] = dict((f, []) for f in fieldname)
        else:
            result = dict.fromkeys(ids, [])
        return result

    _columns = {
        'name': fields.char('Contact Name', size=128, required=True),
        'contact_id': fields.many2one('res.partner', 'Contact'),
        'is_favorite': fields.boolean('Favorite',
            help='User has marked this degree as a desired/favorite one'),
        'acquired_date': fields.date('Acquired Date'),
        'degree_id': fields.many2one('event.degree', 'Degree', required=True),
        'exam_participation_ids': fields.function(_get_all_exams, type='one2many', relation='event.participaiton',
                                                  string='Exam Participations', multi='all-exams'),
        'exam_done_ids': fields.function(_get_all_exams, type='one2many', relation='event.course',
                                         string='Exam Done', multi='all-exams'),
        'exam_todo_ids': fields.function(_get_all_exams, type='one2many', relation='event.course',
                                         string='Exam Todo', multi='all-exams'),
        'state': fields.selection(STATES_SELECTION, required=True, readonly=True),
    }

    _defaults = {
        'state': 'draft',
    }


class EventSeanceType(osv.Model):
    _inherit = 'event.seance.type'
    _columns = {
        'is_exam': fields.boolean('Exam'),
    }


class EventSeance(osv.Model):
    _inherit = 'event.seance'
    _columns = {
        'is_exam': fields.boolean('Exam'),
        'questionnaire_ids': fields.many2many('event.questionnaire', id1='seance_id', id2='questionnaire_id',
                                             string='Default questionnaires'),
    }

    def onchange_seance_type(self, cr, uid, ids, type_id, context=None):
        changes = super(EventSeance, self).onchange_seance_type(cr, uid, ids, type_id, context=context)
        if type_id:
            SeanceType = self.pool.get('event.seance.type')
            type_ = SeanceType.browse(cr, uid, type_id, context=context)
            changes.setdefault('value', {}).update(
                is_exam=type_.is_exam,
            )
        return changes

    def _prepare_participation_for_seance(self, cr, uid, name, seance, registration, context=None):
        values = super(EventSeance, self)._prepare_participation_for_seance(cr, uid, name, seance, registration, context=context)
        if seance.is_exam:
            exams = []
            for q in seance.questionnaire_ids:
                exams.append((0, {'questionnaire_id': q.id}))
            values.update(exam_course_id=seance.course_id.id,
                          exam_ids=exams)
        return values


class EventParticipationReponse(osv.Model):
    _name = 'event.participation.response'
    _columns = {
        'participation_id': fields.many2one('event.participation', 'Participation', required=True),
        'questionnaire_id': fields.many2one('event.questionnaire', 'Questionnaire', required=True),
        'question_id': fields.many2one('event.question', 'Question', required=True),
        'points': fields.float('Points'),
        'max_points': fields.related('question_id', 'points', type='float', string='Max Points', readonly=True),
        'is_graded': fields.boolean('Graded?'),
    }


class EventParticipationExam(osv.Model):
    _name = 'event.participation.exam'

    def _get_score_points(self, cr, uid, ids, fieldname, args, context=None):
        # TODO: compute real score based on response line
        return dict.fromkeys(ids, 0.0)

    def _get_score_id(self, cr, uid, ids, fieldname, args, context=None):
        # TODO: compute real score based on 'exam_score_points' + 'exam_questionnaire_id'
        return dict.fromkeys(ids, False)

    def _store_get_participation_exam_self(self, cr, uid, ids, context=None):
        return ids

    def _store_get_participation_exam_from_participation(self, cr, uid, ids, context=None):
        ParticipationExam = self.pool.get('event.participation.exam')
        return ParticipationExam.search(cr, uid, [('participation_id', 'in', ids)], context=context)

    def _store_get_participation_exam_from_responses(self, cr, uid, ids, context=None):
        Exam = self.pool.get('event.participation.exam')
        Response = self.pool.get('event.participation.response')
        participations_set = set(r.participation_id.id
                                 for r in Response.browse(cr, uid, ids, context=context))
        return Exam._store_get_participation_exam_from_participation(cr, uid, list(participations_set), context=context)

    _columns = {
        'participation_id': fields.many2one('event.participation', 'Participation', required=True, ondelete='cascade'),
        'course_id': fields.related('participation_id', 'course_id', type='many2one',
                                    string='Course', relation='event.course'),
        'questionnaire_id': fields.many2one('event.questionnaire', 'Questionnaire', required=True),
        'score_id': fields.function(_get_score_id, type='many2one', relation='event.scoring.level',
                                    string='Score', store={
                                        'event.participation.exam': (_store_get_participation_exam_self, ['score_points', 'questionnaire_id'], 20),
                                        'event.participation.response': (_store_get_participation_exam_from_responses, None, 10),
                                    }),
        'succeeded': fields.related('score_id', 'pass', type='boolean',
                                    string='Succeeded', store=True, readonly=True),
        'score_points': fields.function(_get_score_points, type='float',
                                        string='Score (points)', store={
                                            'event.participation.exam': (_store_get_participation_exam_self, ['score_points', 'questionnaire_id'], 20),
                                            'event.participation.response': (_store_get_participation_exam_from_responses, None, 10),
                                        })
    }


class EventParticipation(osv.Model):
    _inherit = 'event.participation'

    _columns = {
        'is_exam': fields.related('seance_id', 'is_exam', type='boolean', string='Exam',
                                  readonly=True,),
        'exam_course_id': fields.many2one('event.course', 'Exam Course'),
        'exam_ids': fields.one2many('event.participation.exam', 'participation_id', 'Exams'),
        'exam_response_ids': fields.one2many('event.participation.response', 'participation_id', 'Responses'),
    }

    def onchange_seance(self, cr, uid, ids, seance_id, context=None):
        changes = super(EventParticipation, self).onchange_seance(cr, uid, ids, seance_id, context=context)
        if seance_id:
            Seance = self.pool.get('event.seance')
            seance_record = Seance.browse(cr, uid, seance_id, context=context)
            changes.setdefault('value', {}).update(
                is_exam=seance_record.is_exam,
            )
        return changes

    def create(self, cr, uid, values, context=None):
        seance_id = values.get('seance_id')
        if seance_id:
            Seance = self.pool.get('event.seance')
            seance_record = Seance.browse(cr, uid, seance_id, context=context)
            if seance_record.is_exam and seance_record.questionnaire_ids and not values.get('exam_ids'):
                values['exam_ids'] = [(0, 0, {'questionnaire_id': q.id})
                                      for q in seance_record.questionnaire_ids]
        return super(EventParticipation, self).create(cr, uid, values, context=context)
