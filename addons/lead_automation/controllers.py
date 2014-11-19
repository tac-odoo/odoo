# -*- coding: utf-8 -*-
from openerp import http

# class Addons/leadAutomation(http.Controller):
#     @http.route('/addons/lead_automation/addons/lead_automation/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/addons/lead_automation/addons/lead_automation/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('addons/lead_automation.listing', {
#             'root': '/addons/lead_automation/addons/lead_automation',
#             'objects': http.request.env['addons/lead_automation.addons/lead_automation'].search([]),
#         })

#     @http.route('/addons/lead_automation/addons/lead_automation/objects/<model("addons/lead_automation.addons/lead_automation"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('addons/lead_automation.object', {
#             'object': obj
#         })
