# -*- coding: utf-8 -*-

from openerp import models, fields, api

class comparison_factor(models.Model):
    _name = 'comparison_factor'
    _order = 'ponderation desc'

    name = fields.Char(string="Factor Name", required=True)
    parent_id = fields.Many2one('comparison_factor', ondelete='set null', string="Parent Factor", index=True)
    child_ids = fields.One2many('comparison_factor', 'parent_id', string="Child Factors")
    note = fields.Text(string="Note")
    type = fields.Selection([('view','Category'),('criterion','Criteria')], default='criterion',string="Type", required=True)
    #result_ids = fields.One2many('comparison.factor.result', 'factor_id', string="Results")
    ponderation = fields.Float(string="Ponderation", default=0)
    state = fields.Selection([('draft','Draft'),('open','Open')], default='open',string="Status", required=True)

    _sql_constraints = [
        ('name', 'unique(parent_id,name)', 'The name of the Comparison Factor must be unique!' )
    ]

    @api.model
    def create(self, vals):
        result = super(comparison_factor, self).create(vals)
        
        obj_item = self.env['comparison_item']
        obj_factor_result = self.env['comparison_factor_result']
        
        for item in obj_item.search([]):
            obj_factor_result.create({'factor_id':result[0]['id'],'item_id':item.id})
        
        return result  

class comparison_item(models.Model):
    _name = 'comparison_item'

    name = fields.Char(string="Software", required=True)
    code = fields.Char(string="Code", required=True)
    version = fields.Char(string="Version", required=True)
    note = fields.Text(string="Description")
    state = fields.Selection([('draft','Draft'),('open','Open')])
    link_image = fields.Char(string="Image")
    load_default = fields.Boolean(string="Load by Default",default=False, help="This option if checked, will let the Item display on Evaluation Matrix, by default.")

    _sql_constraints = [
        ('name', 'unique(name)', 'the item with the same name is already in the List!' )
    ]

    @api.model
    def create(self, vals):
       result = super(comparison_item, self).create(vals)

       obj_factor = self.env['comparison_factor']
       obj_factor_result = self.env['comparison_factor_result']
        
       for factor in obj_factor.search([]):
           obj_factor_result.create({'factor_id':factor.id,'item_id':result[0]['id']})
        
       return result

class comparison_vote_values(models.Model):
    _name = 'comparison_vote_values'

    name = fields.Char(string="Vote Type", required=True)
    vote = fields.Float(string="Factor", required=True)

class comparison_vote(models.Model):
    _name = 'comparison_vote'

    factor_id = fields.Many2one('comparison_factor', string="Factor", required=True, ondelete="cascade", domain=[('type','<>','view')])
    item_id = fields.Many2one('comparison_item', string="Item", required=True, ondelete="cascade")
    score_id = fields.Many2one('comparison_vote_values', string="Value", required=True)
    note = fields.Text(string="Note")
    state = fields.Selection([('draft','Draft'),('valid','Valide'),('cancel','Cancel')], string="Status", required=True, readonly=True)

    @api.model
    def create(self, vals):
        result = super(comparison_vote,self).create(vals)
        obj_factor = self.env['comparison_factor']
        obj_factor_result = self.env['comparison_factor_result']
        obj_vote_values = self.env['comparison_vote_values']

        return result

class comparison_factor_result(models.Model):
    _name = 'comparison_factor_result'

    factor_id = fields.Many2one('comparison_factor', string="Factor", required=True, ondelete="cascade", readonly=True)
    item_id = fields.Many2one('comparison_item', string="Item", ondelete="cascade", required=True, readonly=True)
    votes = fields.Float(string="Votes", readonly=True, default=0)
    result = fields.Float(string="Goodness(%)" ,readonly=True, digits=(16,3), default=0) 
    # This field must be recomputed each time we add a vote