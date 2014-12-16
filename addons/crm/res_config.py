# -*- coding: utf-8 -*-
from openerp import SUPERUSER_ID
from openerp import models, api, fields, _


class crm_configuration(models.TransientModel):
    _name = 'sale.config.settings'
    _inherit = ['sale.config.settings', 'fetchmail.config.settings']

    group_fund_raising = fields.Boolean("Manage Fund Raising",
                                        implied_group='crm.group_fund_raising',
                                        help="""Allows you to trace and manage your activities for fund raising.""")
    module_crm_claim = fields.Boolean("Manage Customer Claims",
                                      help='Allows you to track your customers/suppliers claims and grievances.\n'
                                      '-This installs the module crm_claim.')
    module_crm_helpdesk = fields.Boolean("Manage Helpdesk and Support",
                                         help='Allows you to communicate with Customer, process Customer query, and provide better help and support.\n'
                                         '-This installs the module crm_helpdesk.')
    alias_prefix = fields.Char('Default Alias Name for Leads')
    alias_domain = fields.Char('Alias Domain',
                               default=lambda self: self.env['mail.alias'].browse([1]).sudo()._get_alias_domain(name=None, args=None)[1])
    group_scheduled_calls = fields.Boolean(
        "Schedule calls to manage call center",
        implied_group='crm.group_scheduled_calls',
        help="""This adds the menu 'Scheduled Calls' under 'Sales / Phone Calls'""")

    def _find_default_lead_alias_id(self):
        alias_id = self.env.ref('crm.mail_alias_lead_info')
        if not alias_id:
            alias_ids = self.env['mail.alias'].search(
                [
                    ('alias_model_id.model', '=', 'crm.lead'),
                    ('alias_force_thread_id', '=', False),
                    ('alias_parent_model_id.model', '=', 'crm.team'),
                    ('alias_parent_thread_id', '=', False),
                    ('alias_defaults', '=', '{}')
                ])
            alias_id = alias_ids and alias_ids[0] or False
        return alias_id

    @api.multi
    def get_default_alias_prefix(self):
        alias_name = False
        alias = self._find_default_lead_alias_id()
        if alias:
            alias_name = alias.alias_name
        return {'alias_prefix': alias_name}

    @api.multi
    def set_default_alias_prefix(self):
        mail_alias = self.env['mail.alias']
        for record in self:
            alias = record._find_default_lead_alias_id()
            if not alias:
                alias = mail_alias.with_context(alias_model_name='crm.lead', alias_parent_model_name='crm.team').create(
                    {'alias_name': record.alias_prefix})
            else:
                alias.write({'alias_name': record.alias_prefix})
        return True
