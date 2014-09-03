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

import openerp
from openerp import _, api, fields, models
from openerp.exceptions import Warning
from openerp.tools import html2plaintext


class crm_helpdesk(models.Model):
    """ Helpdesk Cases """

    _name = "crm.helpdesk"
    _description = "Helpdesk"
    _order = "id desc"
    _inherit = ['mail.thread']

    id = fields.Integer('ID', readonly=True)
    name = fields.Char('Name', required=True)
    active = fields.Boolean('Active', required=False, default=1)
    date_action_last = fields.Datetime('Last Action', readonly=1)
    date_action_next = fields.Datetime('Next Action', readonly=1)
    description = fields.Text('Description')
    create_date = fields.Datetime('Creation Date' , readonly=True)
    write_date = fields.Datetime('Update Date' , readonly=True)
    date_deadline = fields.Date('Deadline')
    user_id = fields.Many2one('res.users', 'Responsible', default=lambda s : s._uid)
    section_id = fields.Many2one('crm.case.section', 'Sales Team', select=True, help='Responsible sales team. Define Responsible user and Email account for mail gateway.')
    company_id = fields.Many2one('res.company', 'Company', default=lambda s : s.env['res.company']._company_default_get('crm.helpdesk'))
    date_closed = fields.Datetime('Closed', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Partner')
    email_cc = fields.Text('Watchers Emails', help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma")
    email_from = fields.Char('Email', help="Destination email for email gateway")
    date = fields.Datetime('Date', default=fields.Datetime.now())
    ref = fields.Reference('reference_model', 'Reference')
    ref2 = fields.Reference('reference_model', 'Reference 2')
    channel_id = fields.Many2one('crm.tracking.medium', 'Channel', help="Communication channel.")
    planned_revenue = fields.Float('Planned Revenue')
    planned_cost = fields.Float('Planned Costs')
    priority = fields.Selection([('0','Low'), ('1','Normal'), ('2','High')], 'Priority', default='1')
    probability = fields.Float('Probability (%)')
    categ_id = fields.Many2one('crm.case.categ', 'Category', \
                            domain="['|',('section_id','=',False),('section_id','=',section_id),\
                            ('object_id.model', '=', 'crm.helpdesk')]")
    duration = fields.Float('Duration', states={'done': [('readonly', True)]})
    state = fields.Selection(
                [('draft', 'New'),
                 ('open', 'In Progress'),
                 ('pending', 'Pending'),
                 ('done', 'Closed'),
                 ('cancel', 'Cancelled')], 'Status', readonly=True, track_visibility='onchange', default='draft',
                                  help='The status is set to \'Draft\', when a case is created.\
                                  \nIf the case is in progress the status is set to \'Open\'.\
                                  \nWhen the case is over, the status is set to \'Done\'.\
                                  \nIf the case needs to be reviewed then the status is set to \'Pending\'.')

    @api.model
    def reference_model(self):
        res = self.env['res.request.link'].search([])
        return [(r.object, r.name) for r in res]

    @api.onchange('partner_id')
    def on_change_partner_id(self):
        self.email_from = self.partner_id.email if self.partner_id else ''

    @api.multi
    def write(self, values):
        """ Override to add case management: open/close dates """
        if values.get('state'):
            if values.get('state') in ['draft', 'open'] and not values.get('date_open'):
                # TODO/FIXME: date_open field is note there - will give warning
                values['date_open'] = fields.Datetime.now()
            elif values.get('state') == 'done' and not values.get('date_closed'):
                values['date_closed'] = fields.Datetime.now()
        return super(crm_helpdesk, self).write(values)

    @api.multi
    def case_escalate(self):
        """ Escalates case to parent level """
        data = {'active': True}
        if self.section_id and self.section_id.parent_id:
            parent_id = self.section_id.parent_id
            data['section_id'] = parent_id.id
            if parent_id.change_responsible and parent_id.user_id:
                data['user_id'] = parent_id.user_id.id
        else:
            raise Warning (_('You can not escalate, you are already at the top level regarding your sales-team category.'))
        self.write(data)
        return True

    # -------------------------------------------------------
    # Mail gateway
    # -------------------------------------------------------

    @api.model
    def message_new(self, msg, custom_values=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        if custom_values is None:
            custom_values = {}
        desc = html2plaintext(msg.get('body')) if msg.get('body') else ''
        defaults = {
            'name': msg.get('subject') or _("No Subject"),
            'description': desc,
            'email_from': msg.get('from'),
            'email_cc': msg.get('cc'),
            'user_id': False,
            'partner_id': msg.get('author_id', False),
        }
        defaults.update(custom_values)
        return super(crm_helpdesk, self).message_new(msg, custom_values=defaults)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
