# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2012-TODAY OpenERP S.A. <http://openerp.com>
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

from openerp.tests import common

class TestMail(common.TransactionCase):

    def _init_mock_build_email(self):
        self._build_email_args_list = []
        self._build_email_kwargs_list = []

    def setUp(self):
        super(TestMail, self).setUp()
        Test = self

        def build_email(self, *args, **kwargs):
            Test._build_email_args_list.append(args)
            Test._build_email_kwargs_list.append(kwargs)
            return build_email.origin(self, *args, **kwargs)

        def send_email(self, cr, uid, message, *args, **kwargs):
            return message['Message-Id']

        self._init_mock_build_email()
        self.MailServerObj = self.env['ir.mail_server']
        self.MailServerObj._patch_method('build_email', build_email)
        self.MailServerObj._patch_method('send_email', send_email)
        # Usefull models
        self.IrModelObj = self.env['ir.model']
        self.IrModelDataObj = self.env['ir.model.data']
        self.IrAttachmentObj = self.env['ir.attachment']
        self.MailAliasObj = self.env['mail.alias']
        self.MailThreadObj = self.env['mail.thread']
        self.MailGroupObj = self.env['mail.group']
        self.MailObj = self.env['mail.mail']
        self.MailMessageObj = self.env['mail.message']
        self.MailNotificationObj = self.env['mail.notification']
        self.MailFollowersObj = self.env['mail.followers']
        self.MailMessageSubtypeObj = self.env['mail.message.subtype']
        self.UsersObj = self.env['res.users'].with_context({'no_reset_password': True})
        self.PartnerObj = self.env['res.partner']
        # Find Employee group
        self.group_employee_id = self.IrModelDataObj.xmlid_to_res_id('base.group_user') or False
        self.user_admin = self.env.user
        # Partner Data
        # User Data: employee, noone
        self.user_employee = self.UsersObj.create({
            'name': 'Ernest Employee',
            'login': 'ernest',
            'alias_name': 'ernest',
            'email': 'e.e@example.com',
            'signature': '--\nErnest',
            'notify_email': 'always',
            'groups_id': [(6, 0, [self.group_employee_id])]})
        self.user_noone = self.UsersObj.create({
            'name': 'Noemie NoOne',
            'login': 'noemie',
            'alias_name': 'noemie',
            'email': 'n.n@example.com',
            'signature': '--\nNoemie',
            'notify_email': 'always',
            'groups_id': [(6, 0, [])]})
        self.user_admin.write({'name': 'Administrator'})
        # Test users to use through the various tests
        self.user_raoul = self.UsersObj.create({
            'name': 'Raoul Grosbedon',
            'signature': 'SignRaoul',
            'email': 'raoul@raoul.fr',
            'login': 'raoul',
            'alias_name': 'raoul',
            'groups_id': [(6, 0, [self.group_employee_id])]})
        self.user_bert = self.UsersObj.create({
            'name': 'Bert Tartignole',
            'signature': 'SignBert',
            'email': 'bert@bert.fr',
            'login': 'bert',
            'alias_name': 'bert',
            'groups_id': [(6, 0, [])]})
        self.partner_admin_id = self.user_admin.partner_id.id
        self.partner_raoul_id = self.user_raoul.partner_id.id
        self.partner_bert_id = self.user_bert.partner_id.id
        # Test 'pigs' group to use through the various tests
        self.group_pigs = self.MailGroupObj.with_context({'mail_create_nolog': True}).create(          
            {'name': 'Pigs', 'description': 'Fans of Pigs, unite !', 'alias_name': 'group+pigs'})
        # Test mail.group: public to provide access to everyone
        self.group_jobs = self.MailGroupObj.create({'name': 'Jobs', 'public': 'public'})
        # Test mail.group: private to restrict access
        self.group_priv = self.MailGroupObj.create({'name': 'Private', 'public': 'private'})

    def tearDown(self):
        # Remove mocks
        self.MailServerObj._revert_method('build_email')
        self.MailServerObj._revert_method('send_email')
        super(TestMail, self).tearDown()
