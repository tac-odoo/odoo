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
    #result_ids = fields.One2many('comparison_factor_result', 'factor_id', string="Results")
    ponderation = fields.Float(string="Ponderation", default=0)
    state = fields.Selection([('draft','Draft'),('open','Open')], default='open',string="Status", required=True)

    _sql_constraints = [
        ('name', 'unique(parent_id,name)', 'The name of the Comparison Factor must be unique!' )
    ]

    @api.model
    def create(self, vals):
        result = super(comparison_factor,self).create(vals)
        
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

    def compute_parents(self, origin, factor, item):
        cr = self._cr
        if factor.parent_id:
            Comparison_result =  self.env['comparison_factor_result']
            final_score = 0.0

            children_tot_ponderation = 0.0
            for child in factor.parent_id.child_ids:
                children_tot_ponderation += child.ponderation

            all_children = (','.join([str(x.id) for x in factor.parent_id.child_ids]))

            cr.execute("select cfr.result,cf.ponderation from comparison_factor_result as cfr,comparison_factor as cf where cfr.item_id=%s and cfr.votes > 0.0 and cfr.factor_id = cf.id and cf.id in (%s)"%(item.id,all_children))
            res = cr.fetchall()

            if res:
                for record in res:
                    final_score += (record[0] * record[1])

                final_score = final_score / children_tot_ponderation

                parent_result = Comparison_result.search([('factor_id', '=', factor.parent_id.id),('item_id', '=', item.id)])
                parent_result.result = final_score
                if origin == 'create_vote':
                    parent_result.votes += 1
                Comparison_result.write(parent_result)

    @api.model
    def create(self, vals):
        result = super(comparison_vote,self).create(vals)
        obj_factor = self.env['comparison_factor']
        obj_factor_result = self.env['comparison_factor_result']
        obj_vote_values = self.env['comparison_vote_values']
        pond_div = 5.0

        for obj_vote in result:
            obj_result = obj_factor_result.search([('factor_id','=',obj_vote.factor_id.id),('item_id','=',obj_vote.item_id.id)])
            votes_old = obj_result[0]['votes']
            score = (obj_vote.score_id.vote / float(pond_div)) * 100

            if votes_old:
                score = (score + obj_result[0]['result']) / 2

            obj_result.votes = votes_old + 1
            obj_result.result = score
            obj_factor_result.write(obj_result)

            factor = obj_vote.factor_id
            item_obj = obj_vote.item_id
            while (factor and  factor.parent_id):
                self.compute_parents('create_vote', factor, item_obj)
                factor = factor.parent_id

        return result

class comparison_factor_result(models.Model):
    _name = 'comparison_factor_result'

    factor_id = fields.Many2one('comparison_factor', string="Factor", required=True, ondelete="cascade", readonly=True)
    item_id = fields.Many2one('comparison_item', string="Item", ondelete="cascade", required=True, readonly=True)
    votes = fields.Float(string="Votes", readonly=True, default=0.0)
    result = fields.Float(string="Goodness(%)" ,readonly=True, digits=(16,3), default=0) 
    # This field must be recomputed each time we add a vote