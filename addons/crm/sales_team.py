# -*- coding: utf-8 -*-

import calendar
from datetime import date
from dateutil import relativedelta
import json

from openerp import tools
from openerp import models, api, fields


class crm_team(models.Model):
    _inherit = 'crm.team'
    _inherits = {'mail.alias': 'alias_id'}

    @api.model
    def _get_stage_common(self):
        result = self.env['crm.stage'].search([('case_default', '=', 1)])
        return result.ids

    @api.multi
    def _get_opportunities_data(self):
        """ Get opportunities-related data for salesteam kanban view
            monthly_open_leads: number of open lead during the last months
            monthly_planned_revenue: planned revenu of opportunities during the last months
        """
        # TODO: __get_bar_values not migrate into new api so i must have to pass obj with self.pool
        # FIXME after migrate __get_bar_values method
        obj = self.pool['crm.lead']
        month_begin = date.today().replace(day=1)
        date_begin = month_begin - \
            relativedelta.relativedelta(months=self._period_number - 1)
        date_end = month_begin.replace(
            day=calendar.monthrange(month_begin.year, month_begin.month)[1])
        lead_pre_domain = [(
            'create_date', '>=', date_begin.strftime(tools.DEFAULT_SERVER_DATE_FORMAT)),
            ('create_date', '<=', date_end.strftime(
             tools.DEFAULT_SERVER_DATE_FORMAT)),
            ('type', '=', 'lead')]
        opp_pre_domain = [(
            'date_deadline', '>=', date_begin.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)),
            ('date_deadline', '<=', date_end.strftime(
             tools.DEFAULT_SERVER_DATETIME_FORMAT)),
            ('type', '=', 'opportunity')]

        for team in self:
            lead_domain = lead_pre_domain + [('team_id', '=', team.id)]
            opp_domain = opp_pre_domain + [('team_id', '=', team.id)]
            team.monthly_open_leads = json.dumps(team.__get_bar_values(
                obj, domain=lead_domain, read_fields=['create_date'], value_field='create_date_count', groupby_field='create_date'))
            team.monthly_planned_revenue = json.dumps(team.__get_bar_values(obj, domain=opp_domain, read_fields=[
                                                      'planned_revenue', 'date_deadline'], value_field='planned_revenue', groupby_field='date_deadline'))

    resource_calendar_id = fields.Many2one(
        'resource.calendar', "Working Time", help="Used to compute open days")
    stage_ids = fields.Many2many(
        'crm.stage', 'crm_team_stage_rel', 'team_id', 'stage_id', 'Stages', default=_get_stage_common)
    use_leads = fields.Boolean(
        'Leads', default=True, help="The first contact you get with a potential customer is a lead you qualify before converting it into a real business opportunity. Check this box to manage leads in this sales team.")
    use_opportunities = fields.Boolean(
        'Opportunities', default=True, help="Check this box to manage opportunities in this sales team.")
    monthly_open_leads = fields.Char(
        compute='_get_opportunities_data', readonly=True, string='Open Leads per Month')
    monthly_planned_revenue = fields.Char(
        compute='_get_opportunities_data', readonly=True, string='Planned Revenue per Month')
    alias_id = fields.Many2one(
        'mail.alias', 'Alias', ondelete="restrict", required=True,
        help="The email address associated with this team. New emails received will automatically create new leads assigned to the team.")

    @api.v7
    def _auto_init(self, cr, context=None):
        """Installation hook to create aliases for all lead and avoid constraint errors."""
        return self.pool.get(
            'mail.alias').migrate_to_alias(cr, self._name, self._table, super(crm_team, self)._auto_init,
                                           'crm.lead', self._columns['alias_id'], 'name', alias_prefix='Lead+', alias_defaults={}, context=context)

    @api.model
    def create(self, vals):
        self = self.with_context(
            alias_model_name='crm.lead', alias_parent_model_name=self._name)
        team = super(crm_team, self).create(vals)
        team.alias_id.write(
            {'alias_parent_thread_id': team.id, 'alias_defaults': {'team_id': team.id, 'type': 'lead'}})
        return team

    @api.multi
    def unlink(self):
        # Cascade-delete mail aliases as well, as they should not exist without
        # the sales team.
        alias_ids = [team.alias_id.id for team in self if team.alias_id]
        res = super(crm_team, self).unlink()
        self.env['mail.alias'].browse(alias_ids).unlink()
        return res
