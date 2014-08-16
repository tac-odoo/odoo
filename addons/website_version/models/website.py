# -*- coding: utf-8 -*-
from openerp.osv import osv,fields
from openerp.http import request


#domain=[('website_id','=',_my_fonction())]
def _my_fonction():
    return 1


class NewWebsite(osv.Model):
    _inherit = "website"

    _columns = {
        'snapshot_id':fields.many2one("website_version.snapshot",string="Snapshot"),
    }

    def get_current_snapshot(self,cr,uid,context=None):
        id=request.session.get('snapshot_id')

        if id is None:
            snap = request.registry['website_version.snapshot']
            website_id=self.get_current_website(cr, uid, context=context).id
            id_master=snap.search(cr, uid, [('name', '=', 'master_'+str(website_id)),('website_id','=',website_id)],context=context)
            if id_master == []:
                snapshot_id=snap.create(cr, uid,{'name':'master_'+str(website_id),'website_id':website_id}, context=context)
                request.session['snapshot_id']=snapshot_id
            return 'master_'+str(website_id)
        else:
            ob=self.pool['website_version.snapshot'].browse(cr,uid,[id],context=context)
            return ob[0].name

    def get_current_website(self, cr, uid, context=None):
        #from pudb import set_trace; set_trace()
        website = super(NewWebsite,self).get_current_website(cr, uid, context=context)

        request.context['website_id'] = website.id
        request.session['website_id'] = website.id

        #key = 'website_%s_snapshot_id' % request.website.id
        key='snapshot_id'
        if request.session.get(key):
            request.context['snapshot_id'] = request.session.get(key)
        elif website.snapshot_id:
            request.context['snapshot_id'] = website.snapshot_id.id
            request.session['snapshot_id'] = website.snapshot_id.id

        return website
