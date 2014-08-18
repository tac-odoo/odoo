# -*- coding: utf-8 -*-


import simplejson
import werkzeug.urls
import werkzeug.wrappers
from datetime import datetime

from openerp import http
from openerp import tools
from openerp.http import request
from openerp import SUPERUSER_ID
from openerp.addons.web import http

from openerp.addons.web.http import request
from openerp.addons.website.models.website import slug

from openerp.addons.web.controllers.main import login_redirect
from openerp.addons.website.controllers.main import Website as controllers

class Jobs(http.Controller):

    _project_per_page = 5

    @http.route(['/page/jobs', '/page/jobs/page/<int:page>'], type='http', auth="public", website=True)
    def jobs(self, page=1, **post):
        search = post.get('search')
        domain = []
        job_obj = request.registry['project.project']

        cr, uid, context = request.cr, SUPERUSER_ID, request.context

        if search:
            domain.append('|')
            domain.append(('name','ilike',search))
            domain.append(('analytic_account_id.description','ilike',search))


        if request.uid != SUPERUSER_ID and request.uid != 3:
            user = request.registry['res.users'].browse(cr, uid, request.uid, context=context)
            #TODO: fix a domain to get all users project and open published project to make a bid
            local_domain  = [
                '|',
                ('partner_id','=',user.partner_id.id),
                '|',
                ('website_published','=',False),
                ('website_published','=',True),
                ('user_id','=',False)
            ]
            domain += local_domain

        if request.uid == 3:
            domain.append(('website_published','=',True))
            domain.append(('user_id','=',False))

        project_count = job_obj.search(request.cr, SUPERUSER_ID, domain, count=True, context=request.context)

        url = '/page/jobs'
        pager = request.website.pager(url=url, total=project_count, page=page,
                                      step=self._project_per_page, scope=self._project_per_page,
                                      url_args={})

        project_ids = job_obj.search(request.cr, SUPERUSER_ID, domain, limit=self._project_per_page, offset=pager['offset'], context=request.context)
        
        values = {
            'jobs': job_obj.browse(request.cr, SUPERUSER_ID, project_ids, request.context),
            'job_count': project_count,
            'pager':pager
        }

        return request.website.render("website_jobs.jobslist", values)

    @http.route(['/page/website.jobs/new', '/page/jobs/new'], type='http', auth="user", website=True)
    def new_job(self, **post):
        return request.website.render("website_jobs.project_new", {})

    @http.route(['/page/jobs/post'], type='http', auth="user", website=True)
    def new_job_post(self, **kwargs):
        job_obj = request.registry['project.project']
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        user = request.registry['res.users'].browse(cr, uid, request.uid, context=context)

        values = {
            'privacy_visibility':'public',
            'partner_id': user.partner_id.id,
            'user_id': False
        }

        for field in ['description', 'name', 'amount_max', 'hours_qtt_est']:
            if kwargs.get(field):
                values[field] = kwargs.pop(field)

        if values.get('amount_max', False):
            values['fix_price_invoices'] = True

        if values.get('hours_qtt_est', False):
            values['invoice_on_timesheets'] = True

        project_id = job_obj.create(cr, uid, values)
        url = "/page/jobs/%s" % (project_id)
        return request.redirect(url)

    @http.route(['/page/jobs/<model("project.project"):job>'], type='http', auth="public", website=True)
    def job_view(self, job):
        #TODO: check for the project status and display project, else display warning
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        values = {
            'job': job
        }
        job_obj = request.registry['project.project']
        job_obj.write(cr, uid, job.id, {'number_view':job.number_view+1})
        cr.commit()
        return request.website.render("website_jobs.jobpost", values)

    @http.route(['/page/employee/<int:user_id>/avatar'], type='http', auth="public", website=True)
    def user_avatar(self, user_id=0, **post):
        cr, uid, context = request.cr, request.uid, request.context
        response = werkzeug.wrappers.Response()
        User = request.registry['hr.employee']
        Website = request.registry['website']
        user = User.browse(cr, SUPERUSER_ID, user_id, context=context)

        return Website._image(cr, SUPERUSER_ID, 'hr.employee', user.id, 'image', response, max_height=100)

    @http.route(['/page/website.employees', '/page/employees'], type='http', auth="public", website=True)
    def employees(self, **post):
        search = post.get('search')
        domain = []
        employee_obj = request.registry['hr.employee']
        employee_ids = employee_obj.search(request.cr, SUPERUSER_ID, domain, context=request.context)
        values = {
            'employees': employee_obj.browse(request.cr, SUPERUSER_ID, employee_ids, request.context),
            'employees_count': len(employee_ids)
        }
        return request.website.render("website_jobs.employees", values)

    def _post_message(self, user, attachment_id=0, **post):
        cr, uid, context = request.cr, request.uid, request.context
        project = request.registry['project.project']
        partner_obj = request.registry['res.partner']

        if uid != request.website.user_id.id:
            partner_ids = [user.partner_id.id]
        else:
            partner_ids = project._find_partner_from_emails(cr, SUPERUSER_ID, 0, [post.get('email')], context=context)
            if not partner_ids or not partner_ids[0]:
                partner_ids = [partner_obj.create(cr, SUPERUSER_ID, {'name': post.get('name'), 'email': post.get('email')}, context=context)]

    @http.route('/jobs/comment/<model("project.project"):job>', type='http', auth="public", methods=['POST'], website=True)
    def slides_comment(self, job, **post):
        cr, uid, context = request.cr, request.uid, request.context
        project = request.registry['project.project']
        if post.get('comment'):
            user = request.registry['res.users'].browse(cr, uid, uid, context=context)
            project = request.registry['project.project']
            project.check_access_rights(cr, uid, 'read')
            self._post_message(user, job.id, **post)
        return werkzeug.utils.redirect(request.httprequest.referrer + "#discuss")
