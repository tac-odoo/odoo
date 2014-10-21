# -*- coding: utf-8 -*-

from openerp import models, fields, api

class comparison_factor(models.Model):
    _name = 'comparison_factor'
    _order = 'ponderation desc'

    name = fields.Char(string="Factor Name", required=True)
    parent_id = fields.Many2one('comparison_factor', ondelete='set null', string="Parent Factor", index=True)
    #user_id =
    child_ids = fields.One2many('comparison_factor', 'parent_id', string="Child Factors")
    note = fields.Text(string="Note")
    #sequence = fields.Integer(string="Sequence")
    type = fields.Selection([('view','Category'),('criterion','Criteria')], default='criterion',string="Type", required=True)
    #result_ids = fields.One2many('comparison.factor.result', 'factor_id', string="Results")
    ponderation = fields.Float(string="Ponderation", default=0)
    #pond_computed = 
    state = fields.Selection([('draft','Draft'),('open','Open')], default='open',string="Status", required=True)

    _sql_constraints = [
        ('name', 'unique(parent_id,name)', 'The name of the Comparison Factor must be unique!' )
    ]

    def create(self, cr, uid, vals, context={}):
        result = super(comparison_factor, self).create(cr, uid, vals, context)
        
        obj_item = self.pool.get('comparison_item')
        obj_factor_result = self.pool.get('comparison_factor_result')
        
        for item_id in obj_item.search(cr, uid, []):
            obj_factor_result.create(cr, uid, {'factor_id':[result][0],'item_id':item_id})
        
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

    def create(self, cr, uid, vals, context={}):
       result = super(comparison_item, self).create(cr, uid, vals, context)

       obj_factor = self.pool.get('comparison_factor')
       obj_factor_result = self.pool.get('comparison_factor_result')
        
       for factor_id in obj_factor.search(cr, uid, []):
           obj_factor_result.create(cr, uid, {'factor_id':factor_id,'item_id':[result][0]})
        
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
    state = fields.Selection([('draft','Draft'),('valid','Valied'),('cancel','Cancel')], string="Status", required=True, readonly=True)

class comparison_factor_result(models.Model):
    _name = 'comparison_factor_result'

    factor_id = fields.Many2one('comparison_factor', string="Factor", required=True, ondelete="cascade", readonly=True)
    item_id = fields.Many2one('comparison_item', string="Item", ondelete="cascade", required=True, readonly=True)
    votes = fields.Float(string="Votes", readonly=True, default=0)
    result = fields.Float(string="Goodness(%)" ,readonly=True, digits=(16,3), default=0) 
    # This field must be recomputed each time we add a vote