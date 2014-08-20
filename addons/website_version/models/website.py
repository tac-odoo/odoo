# -*- coding: utf-8 -*-
from openerp.osv import osv,fields
from openerp.http import request


#domain=[('website_id','=',_my_fonction())]
def _my_fonction():
    return 1


class NewWebsite(osv.Model):
    _inherit = "website"

    _columns = {
        'snapshot_id':fields.many2one("website_version.snapshot",string="Snapshot", domain="[('website_id','=',context.get('active_id'))]")
    }

    def get_current_snapshot(self,cr,uid,context=None):
        snap = request.registry['website_version.snapshot']
        snapshot_id=request.context.get('snapshot_id')

        if not snapshot_id:
            website_id = request.website.id
            id_master = snap.search(cr, uid, [('name', '=', 'master_'+str(website_id)),('website_id','=',website_id)],context=context)
            if id_master == []:
                snapshot_id = snap.create(cr, uid,{
                        'name':'master_'+str(website_id),
                        'website_id':website_id,
                        'website_ids': [(4, website_id)]
                    }, context=context)
                request.session['snapshot_id'] = snapshot_id
                request.context['snapshot_id'] = snapshot_id
        return snap.name_get(cr, uid, [snapshot_id], context=context)[0];

    def get_current_website(self, cr, uid, context=None):
        ids=self.search(cr, uid, [], context=context)
        url = request.httprequest.url
        
        websites = self.browse(cr, uid, ids, context=context)
        website = websites[0]
        for web in websites:
            if web.name in url:
                website = web
                break

        request.context['website_id'] = website.id

        #key = 'website_%s_snapshot_id' % request.website.id
        key='snapshot_id'
        if request.session.get(key):
            request.context['snapshot_id'] = request.session.get(key)
        elif website.snapshot_id:
            request.context['snapshot_id'] = website.snapshot_id.id

        return website