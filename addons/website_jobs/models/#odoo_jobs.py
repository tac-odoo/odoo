# -*- coding: utf-8 -*-

from openerp.osv import osv
from openerp.osv import fields

class ProjectTag(osv.Model):
    _name = 'project.tag'

    _columns = {
        'name': fields.char('Name')
    }

class Project(osv.osv):
    _inherit = 'project.project'
    
    _columns = {
        'tag_ids': fields.many2many('project.tag', 'project_id', 'tag_id', 'ref_project_tag', 'Tags'),
        'website_published': fields.boolean('Available in the website', copy=False),
        'public_info': fields.text('Public Info'),
        'create_date': fields.datetime('Posted On'),
        'website_description': fields.html('Description'),
        'number_view': fields.integer('# of Views')
    }
    
    _defaults = {
        'website_published': False
    }

    def img(self, cr, uid, ids, field='image_small', context=None):
        return "/website/image?model=%s&field=%s&id=%s" % (self._name, field, ids[0])

class Employee(osv.osv):
    _inherit = 'hr.employee'
    
    _columns = {
        'website_published': fields.boolean('Available in the website', copy=False),
        'public_info': fields.text('Public Info'),
        'create_date': fields.datetime('Joined Since'),
    }
    
    _defaults = {
        'website_published': False
    }

    def img(self, cr, uid, ids, field='image_small', context=None):
        return "/website/image?model=%s&field=%s&id=%s" % (self._name, field, ids[0])