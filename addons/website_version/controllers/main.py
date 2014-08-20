import openerp
from openerp import http
from openerp.http import request
import datetime

class TableExporter(http.Controller):
        
    @http.route(['/change_snapshot'], type = 'json', auth = "user", website = True)
    def change_snapshot(self, snapshot_id):
        request.session['snapshot_id'] = int(snapshot_id)
        return snapshot_id

    @http.route(['/create_snapshot'], type = 'json', auth = "user", website = True)
    def create_snapshot(self,name):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        if name == "":
            name = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        snapshot_id = context.get('snapshot_id')
        website_id = request.website.id
        iuv = request.registry['ir.ui.view']
        snap = request.registry['website_version.snapshot']
        new_snapshot_id = snap.create(cr, uid,{'name':name, 'website_id':website_id}, context=context)
        iuv.copy_snapshot(cr, uid, snapshot_id,new_snapshot_id,context=context)
        request.session['snapshot_id'] = new_snapshot_id
        return name

    @http.route(['/delete_snapshot'], type = 'json', auth = "user", website = True)
    def delete_snapshot(self):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        snap = request.registry['website_version.snapshot']
        snapshot_id = context.get('snapshot_id')
        website_id = request.website.id
        id_master = snap.search(cr, uid, [('name', '=', 'master_'+str(website_id))],context=context)[0]
        if not snapshot_id == id_master:
            name = snap.browse(cr,uid,[snapshot_id],context=context).name
            snap.unlink(cr, uid, [snapshot_id], context=context)
            request.session['snapshot_id'] = id_master
        else:
            name = "nothing"
        return name
    
    @http.route(['/all_snapshots'], type = 'json', auth = "public", website = True)
    def get_all_snapshots(self):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        snap = request.registry['website_version.snapshot']
        website_id = request.website.id
        ids = snap.search(cr, uid, [('website_id','=',website_id)],context=context)
        result = snap.read(cr, uid, ids,['id','name','website_ids'],context=context)
        return result

    @http.route(['/set_context'], type = 'json', auth = "public", website = True)
    def set_context(self):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        snapshot_id = context.get('snapshot_id')
        return snapshot_id
