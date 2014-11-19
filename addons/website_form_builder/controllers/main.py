# -*- coding: utf-8 -*-
import base64

import json
import collections

from openerp import http, SUPERUSER_ID
from openerp.http import request
from openerp.tools.translate import _

class form_builder(http.Controller):
              
    def __init__(self):
        
        self.filter = {'char': self.char, 'text': self.text, 'many2one': self.many2one, 
                       'one2many': self.one2many, 'many2many':self.many2many, 'selection': self.selection, 
                       'boolean': self.boolean,'integer': self.integer,'float': self.float}
    
        self.custom_label    = "%s\n________________________________________________\n\n" % _("Custom infos")   # Extra data from custom fields
        self.meta_label      = "%s\n________________________________________________\n\n" % _("Metadata")       # meta data
        
        self._TECHNICAL      = ['context']

    # List of filters following type of field to be fault tolerent
    def get_int(self,x):
        return int(''.join(ele for ele in x if ele.isdigit()) or 0)

    def get_float(self,x):
        return float(''.join(ele for ele in x if ele.isdigit() or ele == '.') or 0.0)

    def char(self, label, input):
        return input
    
    def text(self, label, input):
        return input
    
    def many2one(self, label, input):
        return int(self.get_int(input))
    
    def one2many(self, label, input):
        output = []
        input = input.split(',')
        for elem in input:
            input_int = int(self.get_int(elem))
            if input_int :
                output.append(input_int)     
        return output
    
    def many2many(self, label, input, *args):
        op = (6,0)
        if len(args) == 1: op = args[0]
        output = self.one2many(label,input)
        return [op + (output,)]
    
    def selection(self, label, input):
        return int(self.get_int(input))
    
    def boolean(self, label, input):
        return (input != 0)
    
    def integer(self, label, input):
        return int(self.get_int(input))
    
    def float(self, label, input):
        return float(self.get_float(input))

    # Extract all data sent by the form and sort its on several properties
    def extractData(self, model, **kwargs):
        print kwargs
        data = {
            'files'     : [],                    # List of attached files
            'post'      : {},                    # Dict of values to create entry on the model
            'custom'    : self.custom_label,
            'meta'      : self.meta_label,
            'error'     : '',
            'message'   : { 
                            'body'           : _('<p>Attatched files : </p>'),
                            'model'          : model["name"],
                            'type'           : 'comment',
                            'no_auto_thread' : False,
                            'attachment_ids' : [],
                }
        }

        for field_name, field_value in kwargs.items():  
            print field_name, ' : ', field_value, '\n'
            if hasattr(field_value, 'filename'):
                field_value.field_name = field_name
                data['files'].append(field_value)

            elif field_name in request.registry[model['name']]._all_columns and field_name not in model['blacklist']:
                type = request.registry[model['name']]._all_columns[field_name].column._type;
                field_filtered = self.filter[type](field_name,field_value);
                if field_filtered: data['post'][field_name] = field_filtered
                
            elif field_name not in self._TECHNICAL:
                data['custom'] += "%s : %s\n" % (field_name, field_value)
                
                
        environ = request.httprequest.headers.environ
        
        data['meta'] += "%s : %s\n%s : %s\n%s : %s\n%s : %s\n" % ("IP"                , environ.get("REMOTE_ADDR"), 
                                                                  "USER_AGENT"        , environ.get("HTTP_USER_AGENT"),
                                                                  "ACCEPT_LANGUAGE"   , environ.get("HTTP_ACCEPT_LANGUAGE"),
                                                                  "REFERER"           , environ.get("HTTP_REFERER"))
        
        data['error'] = list(set(field for field in model['required'] if not data['post'].get(field)))
        
        return data
    
    def insertMessage(self, model, data, id_record):
        if model['name'] == 'mail.mail': return True;
        data['message']['res_id'] = id_record
        print data['message']
        return request.registry['mail.message'].create(request.cr, SUPERUSER_ID, data['message'], request.context);

    def insertRecord(self, model, data):
        values = data['post'];
        if model['default_field'] not in values : values[model['default_field']] = ''
        values[model['default_field']] += "\n\n" + data['custom'] + "\n\n" + data['meta']
        print 'INSERT :: ', values
        return request.registry[model['name']].create(request.cr, SUPERUSER_ID, values, request.context);

    # Link all files attached on the form
    def insertAttachment(self, model, data):
        id_list = []
        for file in data['files']:
            file.field_name = file.field_name.split('[')[0]
            attachment_value = {
                'name': file.filename,
                'res_name': file.filename,
                'datas': base64.encodestring(file.read()),
                'datas_fname': file.filename,
            }
            id_file = request.registry['ir.attachment'].create(request.cr, SUPERUSER_ID, attachment_value, context=request.context)
            id_list.append(id_file)
            if file.field_name in request.registry[model['name']]._all_columns and file.field_name not in model['blacklist']:

                if file.field_name not in data['post'].keys(): 
                    data['post'][file.field_name] = []
                data['post'][file.field_name].append((4,id_file))

            else:
                data['message']['attachment_ids'].append((4,id_file))
        return id_list

    def insert(self, model, data):
        id_list   = self.insertAttachment(model, data)
        id_record = self.insertRecord(model, data)
        self.insertMessage(model, data, id_record)  
        return request.registry['ir.attachment'].write(request.cr, SUPERUSER_ID, id_list, {'res_id': id_record}, context=request.context)
        
    def authorized_fields(self, model):
        request.registry['website.form'].get_authorized_fields(request.cr, SUPERUSER_ID, model['name'])
    
    @http.route('/page/website.form.thankyou', type='http', auth="public", website=True)
    def form_thankyou(self):
        return request.website.render("website_form_builder.form_thankyou")

    @http.route('/page/website.form.error', type='http', auth="public", website=True)
    def form_error(self):
        return request.website.render("website_form_builder.form_error")


    @http.route('/website_form/<model>', type='http', auth="public", website=True)
    def contactus(self,model, ** kwargs):

        obj_form = request.registry['website.form']
        id_model = obj_form.search(request.cr,SUPERUSER_ID,[('model_id', '=', model),],context=request.context)
        if not id_model: #if not authorized model
            return request.website.render("website_form_builder.xmlresponse",{'response':False})

        # return all meta-fields of the selected model
        formModel = obj_form.browse(request.cr, SUPERUSER_ID, id_model)

        model = {
            'name'              : model,
            'default_field'     : formModel.metadata_field_id.name,
            'blacklist'         : [field.name for field in formModel.blacklist_field_ids],
            'required'          : obj_form.get_required(request.cr, SUPERUSER_ID, model),
        }

        data = self.extractData(model, **kwargs) 
        
        print "error : ", data['error'], "\n\n"
        try:     
            if(any(data['error'])) :    success = 0
            else :                      success = self.insert(model, data)
        except ValueError:
            print ValueError
            success = 0

        if data['error'] : 
            response = json.dumps({'id': success, 'fail_required' : data['error']});
        else : 
            response = json.dumps({'id': success, 'fail_required': None});

        return request.website.render("website_form_builder.xmlresponse",{'response':response})
