# -*- coding: utf-8 -*-

from openerp import models, fields, api
import ari
import requests
from requests import HTTPError
import time
from openerp.osv import osv, expression
from openerp.tools.translate import _
import openerp
#----------------------------------------------------------
# Models
#----------------------------------------------------------


class crm_phonecall(models.Model):
	_inherit = "crm.phonecall"

	_order = "sequence, id"

	in_queue = fields.Boolean('In Call Queue', default=True)
	sequence = fields.Integer('Sequence', select=True, help="Gives the sequence order when displaying a list of Phonecalls.")
	start_time = fields.Integer("Start time")

	@api.multi
	def init_call(self):
		self.start_time = int(time.time())	

	@api.multi
	def hangup_call(self):
		stop_time = int(time.time())
		duration = float(stop_time - self.start_time)
		self.duration = float(duration/60.0)
		print(self.duration)	
		self.state = "done"
		return {"duration":self.duration}

	@api.multi
	def rejected_call(self):
		self.state = "no_answer"

	@api.multi
	def remove_from_queue(self):
		self.in_queue = False
		if(self.state == "to_do"):
			self.state = "cancel"
		return {
			'type': 'ir.actions.client',
			'tag': 'reload_panel',
		}

	@api.one
	def get_info(self):
		return {"id": self.id,
				"description": self.description,
				"name": self.name,
				"state": self.state,
				"duration": self.duration,
				"partner_id": self.opportunity_id.partner_id.id,
				"partner_name": self.opportunity_id.partner_id.name,
				"partner_image_small": self.opportunity_id.partner_id.image_small,
				"partner_email": self.opportunity_id.partner_id.email,
				"partner_title": self.opportunity_id.partner_id.title.name,
				"partner_phone": self.partner_phone or self.opportunity_id.partner_id.phone or self.opportunity_id.partner_id.mobile or False,
				"opportunity_name": self.opportunity_id.name,
				"opportunity_id": self.opportunity_id.id,
				"opportunity_priority": self.opportunity_id.priority,
				"opportunity_planned_revenue": self.opportunity_id.planned_revenue,
				"opportunity_title_action": self.opportunity_id.title_action,
				"opportunity_date_action": self.opportunity_id.date_action,
				"opportunity_company_currency": self.opportunity_id.company_currency.id,
				"opportunity_probability": self.opportunity_id.probability,
				"max_priority": self.opportunity_id._all_columns.get('priority').column.selection[-1][0]}

	@api.model
	def get_list(self, current_search):
		return {"phonecalls": self.search([('in_queue','=',True),('user_id','=',self.env.user[0].id)], order='sequence, state,id').get_info()}

	@api.model
	def get_pbx_config(self):
		return {'pbx_ip':self.env['ir.config_parameter'].get_param('crm.wardialing.pbx_ip'),
				'wsServer':self.env['ir.config_parameter'].get_param('crm.wardialing.wsServer'),
				'login':self.env.user[0].sip_login,
				'password':self.env.user[0].sip_password,
				'physicalPhone':self.env.user[0].sip_physicalPhone,}
				
class crm_lead(models.Model):
	_inherit = "crm.lead"
	in_call_center_queue = fields.Boolean("Is in the Call Queue", compute='compute_is_call_center')

	@api.one
	def compute_is_call_center(self):
		phonecall = self.env['crm.phonecall'].search([('opportunity_id','=',self.id),('in_queue','=',True),('state','=','to_do'),('user_id','=',self.env.user[0].id)])
		if phonecall:
			self.in_call_center_queue = True
		else:
			self.in_call_center_queue = False	

	@api.multi
	def create_call_center_call(self):
		phonecall = self.env['crm.phonecall'].create({
				'name' : self.name
		});
		phonecall.user_id = self.env.user[0].id
		phonecall.opportunity_id = self.id
		phonecall.partner_id = self.partner_id
		phonecall.state = 'to_do'
		phonecall.partner_phone = self.partner_id.phone
		phonecall.partner_mobile = self.partner_id.mobile
		phonecall.in_queue = True
		return {
			'type': 'ir.actions.client',
			'tag': 'reload_panel',
		}

	@api.multi
	def delete_call_center_call(self):
		phonecall = self.env['crm.phonecall'].search([('opportunity_id','=',self.id),('in_queue','=',True),('user_id','=',self.env.user[0].id)])
		phonecall.unlink()
		return {
			'type': 'ir.actions.client',
			'tag': 'reload_panel',
		}

class crm_phonecall_log_wizard(models.TransientModel):
	_name = 'crm.phonecall.log.wizard'
		
	description = fields.Text('Description')
	name = fields.Char(readonly=True)
	opportunity_name = fields.Char(readonly=True)
	opportunity_planned_revenue = fields.Char(readonly=True)
	opportunity_title_action = fields.Char()
	opportunity_date_action = fields.Date()
	opportunity_probability = fields.Float(readonly=True)
	partner_name = fields.Char(readonly=True)
	partner_phone = fields.Char(readonly=True)
	partner_email = fields.Char(readonly=True)
	partner_image_small = fields.Char(readonly=True)
	duration = fields.Float('Duration', readonly=True)

	@api.multi
	def save(self):
		phonecall = self.env['crm.phonecall'].browse(self._context.get('phonecall_id'))
		opportunity = self.env['crm.lead'].browse(self._context.get('opportunity_id'))
		phonecall.description = self.description
		phonecall.in_queue = False
		opportunity.title_action = self.opportunity_title_action
		opportunity.date_action = self.opportunity_date_action
		return {
			'type': 'ir.actions.client',
			'tag': 'reload_panel',
		}

	@api.multi
	def save_keep(self):
		phonecall = self.env['crm.phonecall'].browse(self._context.get('phonecall_id'))
		opportunity = self.env['crm.lead'].browse(self._context.get('opportunity_id'))
		phonecall.description = self.description
		opportunity.title_action = self.opportunity_title_action
		opportunity.date_action = self.opportunity_date_action
		return {
			'type': 'ir.actions.client',
			'tag': 'reload_panel',
		}

class res_users(models.Model):
	_inherit = 'res.users'

	sip_login = fields.Char("SIP Login / Browser's Extension")
	sip_password = fields.Char('SIP Password')
	sip_physicalPhone = fields.Char("Physical Phone's Number")