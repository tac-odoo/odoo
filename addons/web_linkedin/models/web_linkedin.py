# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import base64
from datetime import datetime, timedelta
import logging
import simplejson
import urllib2
from urlparse import urlparse, urlunparse
import werkzeug.urls

import openerp
import openerp.addons.web
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import SUPERUSER_ID
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

BASE_API_URL = "https://api.linkedin.com/v1"
company_fields = "(id,name,logo-url,description,industry,website-url,locations,universal-name)"
people_fields = '(id,picture-url,public-profile-url,first-name,last-name,' \
                    'formatted-name,location,phone-numbers,im-accounts,' \
                    'main-address,headline,positions,summary,specialties)'
_logger = logging.getLogger(__name__)

class web_linkedin_settings(osv.osv_memory):
    _inherit = 'sale.config.settings'
    _columns = {
        'api_key': fields.char(string="API Key", size=50, help="LinkedIn API Key"),
        'secret_key': fields.char(string="Secret Key", help="LinkedIn Secret Key"),
        'server_domain': fields.char(),
    }
    
    def get_default_linkedin(self, cr, uid, fields, context=None):
        key = self.pool.get("ir.config_parameter").get_param(cr, uid, "web.linkedin.apikey") or ""
        dom = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        secret_key = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.linkedin.secretkey')
        return {'api_key': key, 'server_domain': dom+"/linkedin/authentication", 'secret_key': secret_key}
    
    def set_linkedin(self, cr, uid, ids, context=None):
        self_record = self.browse(cr, uid, ids[0], context)
        config_pool = self.pool.get("ir.config_parameter")
        apikey = self_record["api_key"] or ""
        secret_key = self_record["secret_key"] or ""
        config_pool.set_param(cr, uid, "web.linkedin.apikey", apikey, groups=['base.group_users'])
        config_pool.set_param(cr, uid, "web.linkedin.secretkey", secret_key, groups=['base.group_users'])

#TODO: Change name to linkedin_partner
class web_linkedin_fields(osv.Model):
    _inherit = 'res.partner'

    def _get_url(self, cr, uid, ids, name, arg, context=None):
        res = dict((id, False) for id in ids)
        for partner in self.browse(cr, uid, ids, context=context):
            res[partner.id] = partner.linkedin_url
        return res

    def linkedin_check_similar_partner(self, cr, uid, linkedin_datas, context=None):
        res = []
        res_partner = self.pool.get('res.partner')
        for linkedin_data in linkedin_datas:
            partner_ids = res_partner.search(cr, uid, ["|", ("linkedin_id", "=", linkedin_data['id']), 
                    "&", ("linkedin_id", "=", False), 
                    "|", ("name", "ilike", linkedin_data['firstName'] + "%" + linkedin_data['lastName']), ("name", "ilike", linkedin_data['lastName'] + "%" + linkedin_data['firstName'])], context=context)
            if partner_ids:
                partner = res_partner.read(cr, uid, partner_ids[0], ["image", "mobile", "phone", "parent_id", "name", "email", "function", "linkedin_id"], context=context)
                if partner['linkedin_id'] and partner['linkedin_id'] != linkedin_data['id']:
                    partner.pop('id')
                if partner['parent_id']:
                    partner['parent_id'] = partner['parent_id'][0]
                for key, val in partner.items():
                    if not val:
                        partner.pop(key)
                res.append(partner)
            else:
                res.append({})
        return res

    _columns = {
        'linkedin_id': fields.char(string="LinkedIn ID"),
        'linkedin_url': fields.char(string="LinkedIn url", store=True),
        'linkedin_public_url': fields.function(_get_url, type='text', string="LinkedIn url", 
            help="This url is set automatically when you join the partner with a LinkedIn account."),
    }

    def get_empty_list_help(self, cr, uid, help, context=None):
        apikey = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.linkedin.apikey', default=False, context=context)
        secret_key = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.linkedin.secretkey', default=False, context=context)
        if apikey and secret_key:
            #Either we can achive it by including no_result method
            return _("""<p class="oe_view_nocontent_create">
                    Click to add a contact in your address book or <a href='#' class="oe_import_contacts">Import Contacts from Linkedin</a>.
                  </p><p>
                    OpenERP helps you easily track all activities related to
                    a customer; discussions, history of business opportunities,
                    documents, etc.
                  </p>""")
        else:
            return super(web_linkedin_fields, self).super(cr, uid, help, context=context)

class linkedin_users(osv.Model):
    _inherit = 'res.users'

    _columns = {
        'linkedin_token': fields.char("LinkedIn Token"),
        'linkedin_token_validity': fields.datetime("LinkedIn Token Validity")
    }

#TODO: Need to check mechanism about Refresh token in linkedin so that authorization part not asked, otherwise we will get authorization part each time
class linkedin(osv.AbstractModel):
    _name = 'linkedin'
    limit = 5

    #TO Implement
    def sync_linkedin_contacts(self, cr, uid, from_url, context=None):
        #This method will import all first level contact from linkedin
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'x-li-format': 'json'}
        token = self.get_token(cr, uid, context=context)
        params = {
            'oauth2_access_token': token
        }
        if not self.need_authorization(cr, uid, context=context):
            connection_uri = BASE_API_URL + "/people/~/connections:{people_fields}".format(people_fields=people_fields)
            status, res = self.send_request(cr, connection_uri, params=params, headers=headers, type="GET", context=context)
            #TODO: It is possible that update_contacts return osv.exception if user doesn't have rights, handle the exception nicely
            self.update_contacts(cr, uid, res, context=context)
            return True
        else:
            return {'status': 'need_auth', 'url': self._get_authorize_uri(cr, uid, from_url=from_url, context=context)}

    def update_contacts(self, cr, uid, records, context=None):
        li_records_obj = LinkedinRecords(self, cr, uid, records.get('values'), records.get('_total'))
        #there may be an issue of rights, current user may now have rights of create or write
        li_records_obj.create_contacts()
        li_records_obj.update_contacts()

    def get_customer_popup_data(self, cr, uid, context=None, **kw):
        result_data = {}
        if context is None:
            context = {}
        context.update(kw.get('local_context') or {})
        token = self.get_token(cr, uid, context=context)
        companies = {}
        people = {}
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'x-li-format': 'json'}
        params = {
            'oauth2_access_token': token
        }
        #search by universal-name
        if kw.get('search_uid'):
            uri = BASE_API_URL + "/companies/universal-name={company_name}:{company_fields}".format(company_name=kw['search_uid'], company_fields=company_fields)
            status, res = self.send_request(cr, uri, params=params, headers=headers, type="GET", context=context)
            companies.update(res)
            """
            #Not able to trace why this code returns 400 bad request error
            public_profile_url = werkzeug.url_quote_plus("http://www.linkedin.com/pub/%s"%(kw['search_uid']))
            print "\n\npublic_profile_url is ::: ",public_profile_url
            profile_uri = BASE_API_URL + "/people/url={public_profile_url}:{people_fields}".format(public_profile_url=public_profile_url, people_fields=people_fields)
            status, profile = self.send_request(cr, profile_uri, params=params, headers=headers, type="GET", context=context)
            print "\n\nprofile is ::: ", profile
            """
        search_params = dict(params.copy(), keywords=kw.get('search_term', "") or "", count=self.limit)
        company_search_uri = BASE_API_URL + "/company-search:(companies:{company_fields})".format(company_fields=company_fields)
        status, res = self.send_request(cr, company_search_uri, params=search_params, headers=headers, type="GET", context=context)
        companies.update(res)

        #Note: People search is allowed to only vetted API access request, please go through following link
        #https://help.linkedin.com/app/api-dvr
        people_search_uri = BASE_API_URL + "/people-search:(people:{people_fields})".format(people_fields=people_fields)
        status, res = self.send_request(cr, people_search_uri, params=search_params, headers=headers, type="GET", context=context)
        people.update(res or {})

        result_data['companies'] = companies
        result_data['people'] = people
        return result_data

    #To Implement, and simplify methods for need_auth and from_url part
    def get_people_from_company(self, cr, uid, company_universalname, limit, from_url, context=None):
        if context is None:
            context = {}

        if not self.need_authorization(cr, uid, context=context):
            #Facet based search
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'x-li-format': 'json'}
            params = {
                'oauth2_access_token': self.get_token(cr, uid, context=context),
                'company-name': company_universalname,
                'current-company': 'true',
                'count': limit
                
            }
            people_criteria_uri = BASE_API_URL + "/people-search:(people:{people_fields})".format(people_fields=people_fields)
            status, res = self.send_request(cr, people_criteria_uri, params=params, headers=headers, type="GET", context=context)
            return res
        else:
            return {'status': 'need_auth', 'url': self._get_authorize_uri(cr, uid, from_url=from_url, context=context)}

    def send_request(self, cr, uri, params={}, headers={}, type="GET", context=None):
        result = ""
        status = ""
        try:
            if type.upper() == "GET":
                data = werkzeug.url_encode(params)
                req = urllib2.Request(uri+ "?"+data)
                #req.add_header('x-li-format', 'json')
                for header_key, header_val in headers.iteritems():
                    req.add_header(header_key, header_val)
            elif type.upper() == 'POST':
                req = urllib2.Request(uri, params, headers)
            else:
                raise ('Method not supported [%s] not in [GET, POST]!' % (type))
            request = urllib2.urlopen(req)
            status = request.getcode()
            if int(status) in (204, 404):  # Page not found, no response
                result = {}
            else:
                content = request.read()
                result = simplejson.loads(content)
        except urllib2.HTTPError, e:
            if e.code in (400, 401, 410):
                raise e

            _logger.exception("Bad linkedin request : %s !" % e.read())
            #error_key = simplejson.loads(e.read())
            #error_key = error_key.get('error', {}).get('message', 'nc')
            #for 404 do not raise config warning
            #raise self.pool.get('res.config.settings').get_config_warning(cr, _("Something went wrong with your request to linkedin. \n\n %s"%(error_key)), context=context)
        return (status, result)

    #Get token must called after checking need_authorization
    def get_token(self, cr, uid, context=None):
        current_user = self.pool['res.users'].browse(cr, uid, uid, context=context)
        return current_user.linkedin_token

    def _get_authorize_uri(self, cr, uid, from_url, scope=False, context=None):
        """ This method return the url needed to allow this instance of OpenErp to access linkedin application """
        state_obj = dict(d=cr.dbname, f=from_url)

        base_url = self.get_base_url(cr, uid, context)
        client_id = self.get_client_id(cr, uid, context)

        params = {
            'response_type': 'code',
            'client_id': client_id,
            'state': simplejson.dumps(state_obj),
            #'scope': scope #Check scope attribute
            'redirect_uri': base_url + '/linkedin/authentication',
        }

        uri = self.get_uri_oauth(a='authorization') + "?%s" % werkzeug.url_encode(params)
        return uri

    def set_all_tokens(self, cr, uid, token_datas, context=None):
        #TODO: Set expires_in and access_token here in res.users
        data = {
            'linkedin_token': token_datas.get('access_token'),
            'linkedin_token_validity': datetime.now() + timedelta(seconds=token_datas.get('expires_in'))
        }
        self.pool['res.users'].write(cr, SUPERUSER_ID, uid, data, context=context)

    #TODO: This should only check whether refresh_token is there or not, if no then need to to authorize and return True 
    def need_authorization(self, cr, uid, context=None):
        current_user = self.pool['res.users'].browse(cr, uid, uid, context=context)
        print "\n\ncurrent_user.linkedin_token_validity is ::: ",current_user.linkedin_token_validity, datetime.now(), current_user.login
        if not current_user.linkedin_token_validity or \
                datetime.strptime(current_user.linkedin_token_validity.split('.')[0], DEFAULT_SERVER_DATETIME_FORMAT) < (datetime.now() + timedelta(minutes=1)):
            return True
        return False

    def get_base_url(self, cr, uid, context=None):
        return self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url', default='http://www.openerp.com?NoBaseUrl', context=context)

    def get_client_id(self, cr, uid, context=None):
        return self.pool.get('ir.config_parameter').get_param(cr, SUPERUSER_ID, 'web.linkedin.apikey', default=False, context=context)

    def get_client_secret(self, cr, uid, context=None):
        return self.pool.get('ir.config_parameter').get_param(cr, SUPERUSER_ID, 'web.linkedin.secretkey', default=False, context=context)

    def get_uri_oauth(self, a=''):  # a = action
        return "https://www.linkedin.com/uas/oauth2/%s" % (a,)

class LinkedinRecords(object):
    """
    This represents linkedin records, it provides utility to differentiate reocrds,
    whether records is to create or it is to update, 
    basically it creates or updates records fetched from linkedin
    cursor: database cursor,
    user_id: current user,
    linkedin_obj: Its a linkedin model object
    """

    def __init__(self, linkedin_obj, cursor, user_id, records, total, context=None):
        self.records = records
        self.id_based_records = dict((d['id'], d) for d in records)
        self.total = total
        #We can also remove records which are there in table but not retrieved from linkedin,
        #that means linkedin user has removed that contact from his/her account
        self.records_to_create = []
        self.records_to_update = []
        self.cr = cursor
        self.uid = user_id
        self.context = context or {}
        self.linkedin_obj = linkedin_obj
        self.check_create_or_update()

    def check_create_or_update(self):
        ids = self.id_based_records.keys()
        read_res = self.linkedin_obj.pool.get('res.partner').search_read(self.cr, self.uid, [('linkedin_id', 'in', ids)], ['linkedin_id'], context=self.context)
        to_update = [x['linkedin_id'] for x in read_res]
        to_create = list(set(ids).difference(to_update))
        for id in to_update:
            self.records_to_update.append(self.id_based_records.get(id))
        for id in to_create:
            self.records_to_create.append(self.id_based_records.get(id))
        print "\n\nrecords_to_create and records_to_update are ::: ",self.records_to_create,"\n\n\n", self.records_to_update

    def create_contacts(self):
        #Create contact from self.records_to_create
        pass

    def update_contacts(self):
        #Write contact from self.records_to_update
        pass