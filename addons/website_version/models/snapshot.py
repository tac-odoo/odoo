# -*- coding: utf-8 -*-
from openerp.osv import osv, fields


class Snapshot(osv.Model):
    _name = "website_version.snapshot"
    
    _columns = {
        'name' : fields.char(string="Title", size=256, required=True),
        'view_ids': fields.one2many('ir.ui.view', 'snapshot_id',string="view_ids"),
        'website_ids': fields.one2many('website', 'snapshot_id',string="Websites"),
        'website_id': fields.integer(string="Website"),
        'create_date': fields.datetime('Create Date'),
    }