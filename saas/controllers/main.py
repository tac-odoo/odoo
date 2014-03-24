# -*- coding: utf-8 -*-

from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp import SUPERUSER_ID

import operator
import werkzeug.urls

class saas(http.Controller):
    
    def create_db(self, fields):
        params = dict(map(operator.itemgetter('name', 'value'), fields))
        db_created = request.session.proxy("db").create_database(
            params['super_admin_pwd'],
            params['db_name'],
            bool(params.get('demo_data')),
            params['db_lang'],
            params['create_admin_pwd'])
        if db_created:
            request.session.authenticate(params['db_name'], 'admin', params['create_admin_pwd'])
        return db_created

    @http.route(['/saas/create_instance'], type='http', auth="public", website=True, multilang=True)
    def contactus(self, instance=None, **kwargs):
        
        saas = request.registry['saas.instance']
        ids = saas.search(request.cr, SUPERUSER_ID, [('name','=',instance)])
        
        instance = instance.lower()
        
        fields = [
            {'name': 'super_admin_pwd', 'value': 'admin'}, 
            {'name': 'db_name', 'value': instance}, 
            {'name': 'demo_data', 'value': 'off'}, 
            {'name': 'db_lang', 'value': 'en_US'}, 
            {'name': 'create_admin_pwd', 'value': 'admin'},
            {'name': 'create_confirm_pwd', 'value': 'admin'}
        ]
        
        if not ids:
            instance_data = {
                'name':instance,
                'active':True
            }
            id = saas.create(request.cr, SUPERUSER_ID, instance_data, request.context)
            if id:
                duplicate_attrs = (
                    'admin',
                    'saastmpl',
                    instance
                )
                self.create_db(fields)
                #request.session.proxy("db").duplicate_database(*duplicate_attrs)

        url = "http://%s.odoo.co.in" % (instance)
        return request.redirect(url)
