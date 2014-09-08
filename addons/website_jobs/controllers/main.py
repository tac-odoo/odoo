import werkzeug.urls
import werkzeug.wrappers
from datetime import datetime

from openerp import http
from openerp import tools
from openerp.http import request
from openerp import SUPERUSER_ID

class Jobs(http.Controller):
	_project_per_page = 5

	@http.route([
		'/jobs',
		'/jobs/page/<int:page>',
		'/jobs/tag/<model("project.tag"):tag>'],type='http',auth='public', website=True)
	def jobs(self, page=1, tag=None,**post):
		#retrive search parameter
		search = post.get('search')
		job_ser = False

		superuser = False
		#check for user if user is SUPERUSER
		if request.uid == 1:
			superuser = True
		domain = []
		if search:
			domain.append(('name','ilike',search))
			job_ser = True
		env = request.env()
		
		job_obj = env['project.project']
		
		url = '/jobs'	

		if not superuser:
			domain.append(('website_published','=',True))

		if tag:
			domain.append(('tag_ids','=',tag.id))

		pager = request.website.pager(url=url,total=len(job_obj.search(domain)),page=page,step=self._project_per_page,scope=self._project_per_page,url_args={})
		jobs = job_obj.search(domain).sudo()
		values = {'jobs':jobs,'job_count':len(job_obj.search(domain)),'pager':pager,"superuser":superuser,"job_ser":job_ser}
		return request.website.render("website_jobs.index",values)

	@http.route([
		'/jobs/new',
		],type='http',auth='user',website=True)
	def new_job(self):
		env = request.env()
		job_tags = env['project.tag'].search([])

		return request.website.render("website_jobs.new_job",{"tags":job_tags})

	@http.route([
		'/jobs/post',],type="http", auth="user",website=True)
	def new_job_post(self, **kwargs):
		env = request.env()
		user = env['res.users'].browse(request.uid)
		tags = env['project.tag'].search([])
		job_obj = env['project.project']
		vals = {
			'privacy_visibility':'public',
			'partner_id':user.partner_id.id,
			'user_id':False,
			'name':kwargs['name'],
			'tag_ids':[(6,0,[int (kwargs[tag.name]) for tag in tags if tag.name in kwargs])],
			'hours_qtt_est':kwargs['hours_qtt_est'],
			'amount_max':kwargs['amount_max'],
			'website_description':kwargs['website_description']
			}
		job_id = job_obj.create(vals)
		return request.redirect("/jobs/%s" % (job_id))

	@http.route([
		'/jobs/<model("project.project"):job>'],type="http",auth="public",website=True)
	def job_view(self, job):
		job.sudo().update({'number_view':job.number_view + 1})
		values= {'job':job}
		return request.website.render("website_jobs.jobview",values)

	@http.route([
		'/employees',
		'/employee/badge/<model("gamification.badge"):badge>',
		'/employees/<model("hr.employee"):emp>',], type='http',auth='public', website=True)
	def employee(self, badge=None, emp=None, **post):
		search = post.get('search')
		emp_ser = False
		employees = []
		domain = []
		emp_count = 0
		env = request.env()
		emp_obj = env['hr.employee']
		gami_obj = env['gamification.badge.user']
		'''
		if badge:
			employees = []
			badges = gami_obj.search([('badge_id','=',badge.id)])
			for badge in badges:
				employees.append(badge.employee_id)
			raise Exception (employees)
		'''
		if search:
			domain.append(('name','ilike',search))
			emp_ser = True
		if badge:
			
			badges = gami_obj.search([('badge_id','=',badge.id)])
			for badge in badges:
				employees.append(badge.employee_id)
			emp_count = len(employees)
		else:
			employees.append(emp_obj.search(domain).sudo())
			emp_count = len(emp_obj.search(domain).sudo())
		#employees = emp_obj.search(domain).sudo()
		values = {
			'employees':employees,
			'employees_count': emp_count,
			'emp_ser':emp_ser
		}
		return request.website.render('website_jobs.employees',values)