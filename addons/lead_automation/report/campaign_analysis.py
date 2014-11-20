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
from openerp import tools, models, fields
from openerp.addons.decimal_precision import decimal_precision as dp


class lead_automation_analysis(models.Model):
    _name = "lead.automation.analysis"
    _description = "Campaign Analysis"
    _auto = False
    _rec_name = 'date'

    def _total_cost(self):
        result = {}
        for ca_obj in self.search([]):
            wi_ids = self.env['lead.automation.workitem'].search(
                        [('segment_id.campaign_id', '=', ca_obj.campaign_id.id)])
            total_cost = ca_obj.activity_id.variable_cost + \
                                ((ca_obj.campaign_id.fixed_cost or 1.00) / len(wi_ids)) #why 1.00???
            result[ca_obj.id] = total_cost
        return result

    res_id = fields.Integer('Resource', readonly=True)
    year = fields.Char('Year', size=4, readonly=True)
    month = fields.Selection([('01','January'), ('02','February'),
                              ('03','March'), ('04','April'),('05','May'), ('06','June'),
                              ('07','July'), ('08','August'), ('09','September'),
                              ('10','October'), ('11','November'), ('12','December')],
                             'Month', readonly=True)
    day = fields.Char('Day', size=10, readonly=True)
    date = fields.Date('Date', readonly=True, select=True)
    campaign_id = fields.Many2one('lead.automation.campaign', 'Campaign',
                                  readonly=True)
    activity_id = fields.Many2one('lead.automation.activity', 'Activity',
                                  readonly=True)
    segment_id = fields.Many2one('lead.automation.segment', 'Segment',
                                 readonly=True)
    partner_id = fields.Many2one('res.partner', 'Partner', readonly=True)
    country_id = fields.Many2one(related='partner_id.country_id', string='Country')
    total_cost = fields.Float(compute='_total_cost', string='Cost', digits=dp.get_precision('Account'))
    revenue = fields.Float('Revenue', readonly=True, digits=dp.get_precision('Account'))
    count = fields.Integer('# of Actions', readonly=True)
    state = fields.Selection([('todo', 'To Do'),
                              ('exception', 'Exception'), ('done', 'Done'),
                              ('cancelled', 'Cancelled')], 'Status', readonly=True)

    def init(self,cr):
        tools.drop_view_if_exists(cr, 'campaign_analysis')
        cr.execute("""
            create or replace view lead_automation_analysis as (
            select
                min(wi.id) as id,
                min(wi.res_id) as res_id,
                to_char(wi.date::date, 'YYYY') as year,
                to_char(wi.date::date, 'MM') as month,
                to_char(wi.date::date, 'YYYY-MM-DD') as day,
                wi.date::date as date,
                s.campaign_id as campaign_id,
                wi.activity_id as activity_id,
                wi.segment_id as segment_id,
                wi.partner_id as partner_id ,
                wi.state as state,
                sum(act.revenue) as revenue,
                count(*) as count
            from
                lead_automation_workitem wi
                left join res_partner p on (p.id=wi.partner_id)
                left join lead_automation_segment s on (s.id=wi.segment_id)
                left join lead_automation_activity act on (act.id= wi.activity_id)
            group by
                s.campaign_id,wi.activity_id,wi.segment_id,wi.partner_id,wi.state,
                wi.date::date
            )
        """)
