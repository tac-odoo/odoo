# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
from openerp.osv import osv
from openerp.osv import fields
from openerp.tools.translate import _
from datetime import datetime

import re
import uuid
import urlparse

class hr_evaluation_mail_compose_message(osv.TransientModel):
    _name = "hr_evaluation.mail.compose.message" 
    _inherit = "mail.compose.message"
    _description = "Mail composition wizard for sending email notification to user"
    _columns = {
            'survey_id' : fields.many2one('survey.survey', 'Survey'),
            'partner_ids' : fields.many2many('res.partner', '', '', '', 'Employees'),
    }

    def default_get(self, cr, uid, fields, context=None):
        Employee = self.pool.get("hr.employee")
        Category = self.pool.get("hr_evaluation.category")
        category_id = Category.browse(cr, uid, context['active_id'], context=None)
        survey_id = category_id.survey_id
        employee_category_id = category_id.employee_category.id
        employee_ids = Employee.search(cr, uid, [('category_ids', '=', employee_category_id)], context=None)
        partner_list = [ Employee.browse(cr, uid, employee, context=None).address_home_id.id for employee in employee_ids ]

       # JSH Note : Here what to for the employees who don't have entry in
       # res_partner. Two possiblity can be there to create new entry or
       # warn user for creating entry.

        res = super(hr_evaluation_mail_compose_message, self).default_get(cr, uid, fields, context=context)
        res.update({'partner_ids': partner_list,
                    'survey_id' : survey_id.id})
        return res
    def send_email_responce(self, cr, uid, ids, context=None):
        """ Process the wizard content and proceed with sending the related
            email(s), rendering any template patterns on the fly if needed """
        if context is None:
            context = {}

        survey_response_obj = self.pool.get('survey.user_input')
        partner_obj = self.pool.get('res.partner')
        mail_mail_obj = self.pool.get('mail.mail')
        try:
            model, anonymous_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'portal', 'group_anonymous')
        except ValueError:
            anonymous_id = None

        def create_response_and_send_mail(wizard, token, partner_id, email):
            """ Create one mail by recipients and replace __URL__ by link with identification token """
            #set url
            url = wizard.survey_id.public_url

            url = urlparse.urlparse(url).path[1:]  # dirty hack to avoid incorrect urls

            if token:
                url = url + '/' + token

            # post the message
            values = {
                'model': None,
                'res_id': None,
                'subject': wizard.subject,
                'body': wizard.body.replace("__URL__", url),
                'body_html': wizard.body.replace("__URL__", url),
                'parent_id': None,
                'partner_ids': partner_id and [(4, partner_id)] or None,
                'notified_partner_ids': partner_id and [(4, partner_id)] or None,
                'attachment_ids': wizard.attachment_ids or None,
                'email_from': wizard.email_from or None,
                'email_to': email,
            }
            mail_id = mail_mail_obj.create(cr, uid, values, context=context)
            mail_mail_obj.send(cr, uid, [mail_id], context=context)

        def create_token(wizard, partner_id, email):
            if context.get("survey_resent_token"):
                response_ids = survey_response_obj.search(cr, uid, [('survey_id', '=', wizard.survey_id.id), ('state', 'in', ['new', 'skip']), '|', ('partner_id', '=', partner_id), ('email', '=', email)], context=context)
                if response_ids:
                    return survey_response_obj.read(cr, uid, response_ids, ['token'], context=context)[0]['token']
            '''if wizard.public != 'email_private':
                return None
            else:
                token = uuid.uuid4().__str__()
                # create response with token
                survey_response_obj.create(cr, uid, {
                    'survey_id': wizard.survey_id.id,
                    'deadline': wizard.date_deadline,
                    'date_create': datetime.now(),
                    'type': 'link',
                    'state': 'new',
                    'token': token,
                    'partner_id': partner_id,
                    'email': email})
                return token'''
            token = uuid.uuid4().__str__()
            # create response with token
            survey_response_obj.create(cr, uid, {
                'survey_id': wizard.survey_id.id,
                'deadline': context['date'],# JSH Note : Do authentication for date = False
                'date_create': datetime.now(),
                'type': 'link',
                'state': 'new',
                'token': token,
                'partner_id': partner_id,
                'email': email})
            return token



        for wizard in self.browse(cr, uid, ids, context=context):
            # check if __URL__ is in the text
            if wizard.body.find("__URL__") < 0:
                raise osv.except_osv(_('Warning!'), _("The content of the text don't contain '__URL__'. \
                    __URL__ is automaticaly converted into the special url of the survey."))

            '''if not wizard.multi_email and not wizard.partner_ids and (context.get('default_partner_ids') or context.get('default_multi_email')):
                wizard.multi_email = context.get('default_multi_email')
                wizard.partner_ids = context.get('default_partner_ids')'''

            # quick check of email list
            '''emails_list = []
            print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
            print("The email_list : {}".format(emails_list))
            if wizard.multi_email:
                emails = list(set(emails_split.split(wizard.multi_email)) - set([partner.email for partner in wizard.partner_ids]))
                for email in emails:
                    email = email.strip()
                    if re.search(r"^[^@]+@[^@]+$", email):
                        emails_list.append(email)'''

            # remove public anonymous access
            partner_list = [ partner for partner in wizard.partner_ids]
            '''for partner in wizard.partner_ids:
                if not anonymous_id or not partner.user_ids or anonymous_id not in [x.id for x in partner.user_ids[0].groups_id]:
                    partner_list.append({'id': partner.id, 'email': partner.email})'''

            '''if not len(emails_list) and not len(partner_list):
                if wizard.model == 'res.partner' and wizard.res_id:
                    return False
                raise osv.except_osv(_('Warning!'), _("Please enter at least one valid recipient."))

            for email in emails_list:
                partner_id = partner_obj.search(cr, uid, [('email', '=', email)], context=context)
                partner_id = partner_id and partner_id[0] or None
                token = create_token(wizard, partner_id, email)
                create_response_and_send_mail(wizard, token, partner_id, email)'''

            for partner in partner_list:
                token = create_token(wizard, partner['id'], partner['email'])
                create_response_and_send_mail(wizard, token, partner['id'], partner['email'])

        return {'type': 'ir.actions.act_window_close'}
