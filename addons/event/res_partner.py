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

from openerp.osv import fields, osv
from openerp.tools.translate import _


class ResPartner(osv.osv):
    _inherit = 'res.partner'

    _columns = {
        'speaker': fields.boolean('Speaker', help="Check this box if this contact is a speaker."),
        'event_ids': fields.one2many('event.event', 'main_speaker_id', readonly=True),
        'event_registration_ids': fields.one2many('event.registration', 'partner_id', readonly=True),
        'speakerinfo_ids': fields.one2many('event.course.speakerinfo', 'course_id', 'Speaker Infos'),
    }

    def open_registrations(self, cr, uid, ids, context=None):
        """ Utility method used to add an "Open Registrations" button in partner views """
        partner = self.browse(cr, uid, ids[0], context=context)
        if partner.customer:
            return {'type': 'ir.actions.act_window',
                    'name': _('Registrations'),
                    'res_model': 'event.registration',
                    'view_type': 'form',
                    'view_mode': 'tree,form,calendar,graph',
                    'context': "{'search_default_partner_id': active_id}"}
        return {}

    def open_events(self, cr, uid, ids, context=None):
        """ Utility method used to add an "Open Events" button in partner views """
        partner = self.browse(cr, uid, ids[0], context=context)
        partner_domain = [
            '|', '|',
            ('registration_ids.partner_id', '=', partner.id),
            ('main_speaker_id', '=', partner.id),
            ('address_id', '=', partner.id),
        ]
        return {'type': 'ir.actions.act_window',
                'name': _('Events'),
                'res_model': 'event.event',
                'view_type': 'form',
                'view_mode': 'tree,form,calendar,graph',
                'domain': partner_domain}

    def open_courses(self, cr, uid, ids, context=None):
        """ Utility method used to add an "Open Courses" button in partner views """
        partner = self.browse(cr, uid, ids[0], context=context)
        if partner.speaker:
            return {
                'name': _('Courses'),
                'type': 'ir.actions.act_window',
                'res_model': 'event.course',
                'view_type': 'form',
                'view_mode': 'kanban,form,tree',
                'context': "{'search_default_speaker_id': active_id}",
            }
        return {}

    def onchange_speaker(self, cr, uid, ids, speaker, context=None):
        values = {}
        values = {
            'attendee_type': 'speaker' if speaker else 'person',
        }
        return {'value': values}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
