# -*- coding: utf-8 -*-
from openerp import api, fields, models


class ProjectIssue(models.Model):

    _name = "project.issue"
    _inherit = ['project.issue', 'rating.mixin']

    @api.multi
    def write(self, values):
        if 'stage_id' in values and values.get('stage_id', False):
            template = self.env['project.task.type'].browse(values.get('stage_id')).rating_template_id
            if template:
                rated_partner_id = self.user_id.partner_id
                partner_id = self.partner_id
                if partner_id and rated_partner_id:
                    self.rating_send_request(template, partner_id, rated_partner_id)
        return super(ProjectIssue, self).write(values)


class Project(models.Model):

    _inherit = "project.project"

    @api.multi
    @api.depends('percentage_satisfaction_task', 'percentage_satisfaction_issue')
    def _compute_percentage_satisfaction_project(self):
        super(Project, self)._compute_percentage_satisfaction_project()
        Rating = self.env['rating.rating']
        for record in self:
            if record.use_tasks or record.use_issues:
                # built the domain according the project parameters (use tasks and/or issues)
                res_models = []
                domain = []
                if record.use_tasks:
                    res_models.append('project.task')
                    domain += ['&', ('res_model', '=', 'project.task'), ('res_id', 'in', record.tasks.ids)]
                if record.use_issues:
                    res_models.append('project.issue')
                    domain += ['&', ('res_model', '=', 'project.issue'), ('res_id', 'in', record.issue_ids.ids)]
                if len(res_models) == 2:
                    domain = ['|'] + domain
                domain = [('rating', '>=', 0)] + domain
                # get the number of rated tasks and issues with a read_group (more perfomant !)
                data = Rating.read_group(domain, ['res_model'], ['res_model'])
                # compute the number of each model and total number
                res = dict.fromkeys(res_models, 0)
                for d in data:
                    res[d['res_model']] += d['res_model_count']
                nbr_rated_task = res.get('project.task', 0)
                nbr_rated_issue = res.get('project.issue',0)
                nbr_project_rating = nbr_rated_issue + nbr_rated_task
                # compute the weighted arithmetic average
                ratio_task = float(nbr_rated_task) / float(nbr_project_rating) if nbr_project_rating else 0
                ratio_issue = float(nbr_rated_issue) / float(nbr_project_rating) if nbr_project_rating else 0
                record.percentage_satisfaction_project = round((ratio_task*record.percentage_satisfaction_task)+(ratio_issue*record.percentage_satisfaction_issue)) if nbr_project_rating else -1
            else:
                record.percentage_satisfaction_project = -1

    @api.one
    def _compute_percentage_satisfaction_issue(self):
        project_issue = self.env['project.issue'].search([('project_id', '=', self.id)])
        activity = project_issue.rating_get_grades()
        self.percentage_satisfaction_issue = activity['great'] * 100 / sum(activity.values()) if sum(activity.values()) else 0

    @api.one
    @api.depends('use_tasks', 'use_issues')
    def _display_happy_customer(self):
        self.is_visible_happy_customer = self.use_tasks if self.use_tasks else self.use_issues


    percentage_satisfaction_issue = fields.Integer(
        compute='_compute_percentage_satisfaction_issue', string='% Happy')


    @api.multi
    def action_view_issue_rating(self):
        """ return the action to see all the rating about the issues of the project """
        action = self.env['ir.actions.act_window'].for_xml_id('rating', 'action_view_rating')
        issues = self.env['project.issue'].search([('project_id', 'in', self.ids)])
        return dict(action, domain=[('res_id', 'in', issues.ids), ('res_model', '=', 'project.issue')])

    @api.multi
    def action_view_all_rating(self):
        action = super(Project, self).action_view_all_rating()
        task_domain = action['domain']
        domain = []
        if self.use_tasks: # add task domain, if neeed
            domain = ['&'] + task_domain
        if self.use_issues: # add issue domain if needed
            issues = self.env['project.issue'].search([('project_id', 'in', self.ids)])
            domain = domain + ['&', ('res_id', 'in', issues.ids), ('res_model', '=', 'project.issue')]
        if self.use_tasks and self.use_issues:
            domain = ['|'] + domain
        return dict(action, domain=domain)

