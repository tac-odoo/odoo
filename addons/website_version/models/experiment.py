# -*- coding: utf-8 -*-
from openerp.osv import osv, fields

class Experiment_page(osv.Model):
    _name = "website_version.experiment_page"
    
    _columns = {
        'view_id': fields.many2one('ir.ui.view',string="View_id", required=True),
        'key': fields.char(string='Key'),
        'snapshot_id': fields.many2one('website_version.snapshot',string="Snapshot_id",required=True ),
        'experiment_id': fields.many2one('website_version.experiment',string="Experiment_id",required=True),
        'ponderation': fields.integer(string="Ponderation"),
    }

    # _sql_constraints = [
    #     ('view_experiment_uniq', 'unique(view_id, experiment_id)', 'You cannot have multiple records with the same view ID in the same experiment!'),
    # ]

    def onchange_get_key(self,cr,uid,ids,view_id,context=None):
        key = self.pool['ir.ui.view'].browse(cr, uid, [view_id],context=context)[0].key
        print key
        val = {'key': key}
        return {'value': val}


class Experiment(osv.Model):
    _name = "website_version.experiment"
    
    _columns = {
        'name': fields.char(string="Title", size=256, required=True),
        'experiment_page_ids': fields.one2many('website_version.experiment_page', 'experiment_id',string="page_ids"),
        'website_id': fields.many2one('website',string="Website", required=True),
    }