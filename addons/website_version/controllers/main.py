import openerp
from openerp import http
import simplejson
from openerp.http import request, serialize_exception as _serialize_exception
from cStringIO import StringIO
from collections import deque
import datetime

class TableExporter(http.Controller):
        
    @http.route(['/change_snapshot'], type='json', auth="user", website=True)
    def change_snapshot(self,snapshot_name):
        #from pudb import set_trace; set_trace()
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        #website_object = request.registry['website']
        #my_website = website_object.get_current_website(self, cr, uid, context=context)
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        snap = request.registry['website_version.snapshot']
        id=snap.search(cr, uid, [('name', '=', snapshot_name)],context=context)[0]
        request.session['snapshot_id']=id
        #request.session['website_%s_snapshot_id'%(my_website.id)]=id[0]
        return id

    @http.route(['/create_snapshot'], type='json', auth="user", website=True)
    def create_snapshot(self,name):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        if name=="":
            name=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        snapshot_id=request.session.get('snapshot_id')
        website_id=request.session.get('website_id')
        iuv = request.registry['ir.ui.view']
        snap = request.registry['website_version.snapshot']
        new_snapshot_id=snap.create(cr, uid,{'name':name, 'website_id':website_id}, context=context)
        iuv.copy_snapshot(cr, uid, snapshot_id,new_snapshot_id,context=context)
        request.session['snapshot_id']=new_snapshot_id
        return name

    @http.route(['/delete_snapshot'], type='json', auth="user", website=True)
    def delete_snapshot(self):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        snap = request.registry['website_version.snapshot']
        snapshot_id=request.session.get('snapshot_id')
        website_id=request.session.get('website_id')
        id_master=snap.search(cr, uid, [('name', '=', 'master_'+str(website_id))],context=context)[0]
        if not snapshot_id==id_master:
            name=snap.browse(cr,uid,[snapshot_id],context=context).name
            snap.unlink(cr, uid, [snapshot_id], context=context)
            request.session['snapshot_id']=id_master
        else:
            name="nothing"
        return name
    
    @http.route(['/all_snapshots'], type='json', auth="public", website=True)
    def get_all_snapshots(self):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        snap = request.registry['website_version.snapshot']
        website_id=request.session.get('website_id')
        ids=snap.search(cr, uid, [('website_id','=',website_id)])
        result=snap.read(cr, uid, ids,['id','name','website_ids'],context=context)
        res=[]
        for ob in result:
            if ob['website_ids']:
                res.append({'name':ob['name'],'link':'linked'})
            else:
                res.append({'name':ob['name'],'link':''})
        return res


    @http.route(['/set_context'], type='json', auth="public", website=True)
    def set_context(self):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        snapshot_id=request.session.get('snapshot_id')
        print 'OK={}'.format(snapshot_id)
        
        return snapshot_id
