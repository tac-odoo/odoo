
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
    'name': 'Events Organisation',
    'version': '0.1',
    'category': 'Tools',
    'summary': 'Trainings, Conferences, Meetings, Exhibitions, Registrations',
    'description': """
Organization and management of Events.
======================================

The event module allows you to efficiently organise events and all related tasks: planification, registration tracking,
attendances, etc.

Key Features
------------
* Manage your Events and Registrations
* Use emails to automatically confirm and send acknowledgements for any event registration
""",
    'author': 'OpenERP SA',
    'depends': ['base_setup', 'board', 'email_template',
                'resource', 'core_calendar', 'product',
                'base_status'],
    'data': [
        'security/event_security.xml',
        'security/ir.model.access.csv',
        'wizard/event_confirm_view.xml',
        'wizard/event_participant_take_presence_view.xml',
        'resource_view.xml',
        'preplanning_view.xml',
        'event_view.xml',
        'event_seance_view.xml',
        'event_course_view.xml',
        'event_data.xml',
        'report/report_event_registration_view.xml',
        'report/report_event_resource_view.xml',
        'report/report_event_seance_view.xml',
        'board_association_view.xml',
        'res_partner_view.xml',
        'email_template.xml',
        'wizard/event_estimate_end_date_view.xml',
    ],
    'demo': ['event_demo.xml'],
    'test': ['test/process/event_draft2done.yml'],
    'css': [
        'static/lib/jquery-handsontable/jquery.handsontable.full.css',
        'static/src/css/event.css',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'js': [
        'static/lib/jquery-handsontable/jquery.handsontable.full.js',
        'static/src/js/*.js'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': [
        'images/1_event_type_list.jpeg',
        'images/2_events.jpeg',
        'images/3_registrations.jpeg',
        'images/events_kanban.jpeg'
    ],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
