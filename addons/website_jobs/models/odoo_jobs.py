from openerp import models,fields,api, _
from openerp.exceptions import except_orm,Warning,RedirectWarning
import openerp.addons.decimal_precision as dp

class ProjectTag(models.Model):
	_name = 'project.tag'

	name = fields.Char(string="Name")

class Project(models.Model):
	_inherit = 'project.project'

	tag_ids = fields.Many2many('project.tag',string="Tags")
	category_id = fields.Many2one('project.category', index=True)
	website_published = fields.Boolean(copy=False, string='Available in the website')
	public_info = fields.Text(string='Public Info')
	create_date = fields.Datetime(string='Posted On')
	website_description = fields.Html(string='Description')
	number_view = fields.Integer('# of Views')

	def img(self,field='image_small',context=None):
		return "/website/image?model=%s&field=%s&id=%s" % (self._name,field,self.id)

class Employee(models.Model):
	_inherit = 'hr.employee'

	website_published = fields.Boolean(string='Available in the website', copy=False)
	public_info = fields.Text(string='Public Info')
	create_date = fields.Datetime(string='Joined Since')

	def img(self,field='image_small',context=None):
		return "/website/image?model=%s&field=%s&id=%s" % (self._name,field,self.id)

class Category(models.Model):
	_name = 'project.category'
	_inherit = ['project.category', 'mail.thread']