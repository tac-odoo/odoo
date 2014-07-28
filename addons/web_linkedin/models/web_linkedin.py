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
                    'main-address,headline,positions,summary,specialties,email-address)'
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

    def sync_linkedin_contacts(self, cr, uid, from_url, context=None):
        """
            This method will import all first level contact from LinkedIn
        """
        if not self.need_authorization(cr, uid, context=context):
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'x-li-format': 'json'}
            params = {
                'oauth2_access_token': self.get_token(cr, uid, context=context)
            }
            connection_uri = "/people/~/connections:{people_fields}".format(people_fields=people_fields)
            status, res = self.send_request(cr, connection_uri, params=params, headers=headers, type="GET", context=context)
            #TODO: It is possible that update_contacts return osv.exception if user doesn't have rights, handle the exception nicely
            self.update_contacts(cr, uid, res, context=context)
            return True
        else:
            return {'status': 'need_auth', 'url': self._get_authorize_uri(cr, uid, from_url=from_url, context=context)}

    def update_contacts(self, cr, uid, records, context=None):
        li_records = dict((d['id'], d) for d in records.get('values', []))
        records_to_create, records_to_update = self.check_create_or_update(cr, uid, li_records, context=context)
        self.create_contacts(cr, uid, records_to_create, context=context)
        self.write_contacts(cr, uid, records_to_update, context=context)

    def check_create_or_update(self, cr, uid, records, context=None):
        records_to_update = {}
        records_to_create = []
        ids = records.keys()
        read_res = self.pool.get('res.partner').search_read(cr, uid, [('linkedin_id', 'in', ids)], ['linkedin_id'], context=context)
        to_update = [x['linkedin_id'] for x in read_res]
        to_create = list(set(ids).difference(to_update))
        for id in to_create:
            records_to_create.append(records.get(id))
        for res in read_res:
            records_to_update[res['id']] = records.get(res['linkedin_id'])
        return records_to_create, records_to_update

    def create_contacts(self, cr, uid, records_to_create, context=None):
        for record in records_to_create:
            if record['id'] != 'private':
                data_dict = self.create_data_dict(cr, uid, record, context=context)
                self.pool.get('res.partner').create(cr, uid, data_dict, context=context)

    #Currently all fields are re-written
    def write_contacts(self, cr, uid, records_to_update, context=None):
        for id, record in records_to_update.iteritems():
            data_dict = self.create_data_dict(cr, uid, record, context=context)
            self.pool.get('res.partner').write(cr, uid, id, data_dict, context=context)

    def create_data_dict(self, cr, uid, record, context=None):
        data_dict = {
            'name': record.get('formattedName', record.get("firstName", "")),
            'linkedin_url': record.get('publicProfileUrl', False),
            'linkedin_id': record.get('id', False),
        }
        #Should we add: email-address,summary
        positions = (record.get('positions') or {}).get('values', [])
        for position in positions:
            if position.get('isCurrent'):
                data_dict['function'] = position.get('title')
                company_name = False
                if position.get('company'):
                    company_name = position['company'].get('name')
                #To avoid recursion, it is quite possible that connection name and company_name is same 
                #in such cases import goes fail meanwhile due to osv exception, hence skipped such connection for parent_id
                if company_name != data_dict['name']:
                    parent_id = self.pool.get('res.partner').search(cr, uid, [('name', '=', company_name)])
                    if parent_id:
                        data_dict['parent_id'] = parent_id[0]
                
        image = record.get('pictureUrl') and self.url2binary(record['pictureUrl']) or False
        data_dict['image'] = image

        phone_numbers = (record.get('phoneNumbers') or {}).get('values', [])
        for phone in phone_numbers:
            if phone.get('phoneType') == 'mobile':
                data_dict['mobile'] = phone['phoneNumber']
            else:
                data_dict['phone'] = phone['phoneNumber']
        return data_dict 

    #TODO: Simplify this method
    def get_search_popup_data(self, cr, uid, context=None, **kw):
        """
            This method will return all needed data for LinkedIn Search Popup in single call.
            It returns companies(including search by universal name), people and warnings if any
        """
        result_data = {'warnings': []}
        if context is None:
            context = {}
        context.update(kw.get('local_context') or {})
        companies = {}
        people = {}
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'x-li-format': 'json'}
        params = {
            'oauth2_access_token': self.get_token(cr, uid, context=context)
        }
        #search by universal-name
        if kw.get('search_uid'):
            universal_search_uri = "/companies/universal-name={company_name}:{company_fields}".format(company_name=kw['search_uid'], company_fields=company_fields)
            status, res = self.send_request(cr, universal_search_uri, params=params, headers=headers, type="GET", context=context)
            companies.update(res)

            #Unable to get why this code returns 400 bad request error, as per linked API doc the call is proper but it returns 400 bad request error always
            #add warning in response and handle warning at client side
            try:
                public_profile_url = werkzeug.url_quote_plus("http://www.linkedin.com/pub/%s"%(kw['search_uid']))
                profile_uri = "/people/url={public_profile_url}:{people_fields}".format(public_profile_url=public_profile_url, people_fields=people_fields)
                status, profile = self.send_request(cr, profile_uri, params=params, headers=headers, type="GET", context=context)
                people.update(profile)
            except urllib2.HTTPError, e:
                if e.code == 400:
                    result_data['warnings'].append([_('LinkedIn error'), _('LinkedIn is temporary down for the searches by url.')])
                elif e.code in (401, 410):
                    raise e

        #Profile Information of current user
        profile_uri = "/people/~:(first-name,last-name)"
        status, res = self.send_request(cr, profile_uri, params=params, headers=headers, type="GET", context=context)
        result_data['current_profile'] = res

        #Companies search
        search_params = dict(params.copy(), keywords=kw.get('search_term', "") or "", count=self.limit)
        company_search_uri = "/company-search:(companies:{company_fields})".format(company_fields=company_fields)
        status, res = self.send_request(cr, company_search_uri, params=search_params, headers=headers, type="GET", context=context)
        #TODO: If companies is there then update the values attribute of companies result(it is possible that comapnies come up with universal-search)
        companies.update(res)

        #Note: People search is allowed to only vetted API access request, please go through following link
        #https://help.linkedin.com/app/api-dvr
        people_search_uri = "/people-search:(people:{people_fields})".format(people_fields=people_fields)
        status, res = self.send_request(cr, people_search_uri, params=search_params, headers=headers, type="GET", context=context)
        #TODO: If people is there then update the values attribute of people result(it is possible that people come up with public-url-search)
        people.update(res or {})

        result_data['companies'] = companies
        result_data['people'] = people
        return result_data

    #To simplify method for need_auth and from_url part
    def get_people_from_company(self, cr, uid, company_universalname, limit, from_url, context=None):
        if context is None:
            context = {}

        if not self.need_authorization(cr, uid, context=context):
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'x-li-format': 'json'}
            params = {
                'oauth2_access_token': self.get_token(cr, uid, context=context),
                'company-name': company_universalname,
                'current-company': 'true',
                'count': limit
                
            }
            people_criteria_uri = "/people-search:(people:{people_fields})".format(people_fields=people_fields)
            status, res = self.send_request(cr, people_criteria_uri, params=params, headers=headers, type="GET", context=context)
            return res
        else:
            return {'status': 'need_auth', 'url': self._get_authorize_uri(cr, uid, from_url=from_url, context=context)}

    def send_request(self, cr, uri, pre_uri=BASE_API_URL, params={}, headers={}, type="GET", context=None):
        result = ""
        status = ""
        try:
            if type.upper() == "GET":
                data = werkzeug.url_encode(params)
                req = urllib2.Request(pre_uri + uri + "?"+data)
                for header_key, header_val in headers.iteritems():
                    req.add_header(header_key, header_val)
            elif type.upper() == 'POST':
                req = urllib2.Request(pre_uri + uri, params, headers)
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
            #Should simply raise exception or simply add logger
            if e.code in (400, 401, 410):
                raise e

            _logger.exception("Bad linkedin request : %s !" % e.read())
        except urllib2.URLError, e:
            _logger.exception("Either there is no connection or remote server is down : %s !" % e.read())
            #for 404 do not raise config warning
            #raise self.pool.get('res.config.settings').get_config_warning(cr, _("Something went wrong with your request to linkedin. \n\n %s"%(error_key)), context=context)
        return (status, result)

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
        data = {
            'linkedin_token': token_datas.get('access_token'),
            'linkedin_token_validity': datetime.now() + timedelta(seconds=token_datas.get('expires_in'))
        }
        self.pool['res.users'].write(cr, SUPERUSER_ID, uid, data, context=context)

    def need_authorization(self, cr, uid, context=None):
        current_user = self.pool['res.users'].browse(cr, uid, uid, context=context)
        print "\n\ncurrent_user.linkedin_token_validity is ::: ",current_user.linkedin_token_validity, datetime.now(), current_user.login
        if not current_user.linkedin_token_validity or \
                datetime.strptime(current_user.linkedin_token_validity.split('.')[0], DEFAULT_SERVER_DATETIME_FORMAT) < (datetime.now() + timedelta(minutes=1)):
            return True
        return False

    def destroy_token(self, cr, uid, context=None):
        return self.pool['res.users'].write(cr, SUPERUSER_ID, uid, {'linkedin_token': False, 'linkedin_token_validity': False})

    def get_base_url(self, cr, uid, context=None):
        return self.pool.get('ir.config_parameter').get_param(cr, SUPERUSER_ID, 'web.base.url', default='http://www.openerp.com?NoBaseUrl', context=context)

    def get_client_id(self, cr, uid, context=None):
        return self.pool.get('ir.config_parameter').get_param(cr, SUPERUSER_ID, 'web.linkedin.apikey', default=False, context=context)

    def get_client_secret(self, cr, uid, context=None):
        return self.pool.get('ir.config_parameter').get_param(cr, SUPERUSER_ID, 'web.linkedin.secretkey', default=False, context=context)

    def test_linkedin_keys(self, cr, uid, context=None):
        return self.get_client_id(cr, uid, context=context) and self.get_client_secret(cr, uid, context=context) and True

    def get_uri_oauth(self, a=''):  # a = action
        return "https://www.linkedin.com/uas/oauth2/%s" % (a,)

    def url2binary(self, url):
        """Used exclusively to load images from LinkedIn profiles, must not be used for anything else."""
        _scheme, _netloc, path, params, query, fragment = urlparse(url)
        # media.linkedin.com is the master domain for LinkedIn media (replicated to CDNs),
        # so forcing it should always work and prevents abusing this method to load arbitrary URLs
        url = urlunparse(('http', 'media.licdn.com', path, params, query, fragment))
        bfile = urllib2.urlopen(url)
        return base64.b64encode(bfile.read())
