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
		'/page/jobs',
		'/page/jobs/page/<int:page>',
		'/page/jobs/tag/<model("project.tag"):tag>'],type='http',auth='public', website=True)
	def jobs(self, page=1, tag=None,**post):
		#retrive search parameter
		search = post.get('search')

		superuser = False
		#check for user if user is SUPERUSER
		if request.uid == 1:
			superuser = True
		domain = []
		if search:
			domain.append(('name','ilike',search))
		env = request.env()
		
		job_obj = env['project.project']
		
		url = '/page/jobs'	

		if not superuser:
			domain.append(('website_published','=',True))

		if tag:
			domain.append(('tag_ids','=',tag.id))

		pager = request.website.pager(url=url,total=len(job_obj.search(domain)),page=page,step=self._project_per_page,scope=self._project_per_page,url_args={})
		jobs = job_obj.search(domain).sudo()
		values = {'jobs':jobs,'job_count':len(job_obj.search(domain)),'pager':pager,"superuser":superuser}
		return request.website.render("website_jobs.index",values)

	@http.route([
		'/page/jobs/new',
		],type='http',auth='user',website=True)
	def new_job(self):
		env = request.env()
		job_tags = env['project.tag'].search([])

		return request.website.render("website_jobs.new_job",{"tags":job_tags})

	@http.route([
		'/page/jobs/post',],type="http", auth="user",website=True)
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
		return request.redirect("/page/jobs/%s" % (job_id))

	@http.route([
		'/page/jobs/<model("project.project"):job>'],type="http",auth="public",website=True)
	def job_view(self, job):
		job.sudo().update({'number_view':job.number_view + 1})
		values= {'job':job}
		return request.website.render("website_jobs.jobview",values)