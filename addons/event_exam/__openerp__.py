
# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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


{
    'name': 'Events Examination',
    'version': '0.1',
    'category': 'Tools',
    'summary': 'Trainings, Conferences, Meetings, Exhibitions, Registrations, Examination',
    'description': """
Organization and management of Event Examinations.
==================================================

This event_exam module allow you to add support for Examinations.

Key Features
-------------
* Quizz and Questions pool
* Quizz auto-correction.
* Assesments.
* Diploma/Degree with automatic subscription.


""",
    'author': 'OpenERP SA',
    'depends': ['event'],
    'data': [
        'event_exam_view.xml',
        'security/ir.model.access.csv',
        'security/event_exam_rules.xml',
    ],
    'demo': ['event_exam_demo.xml'],
    'test': [],
    'css': [
    ],
    'qweb': [],
    'js': [
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': [
    ],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
