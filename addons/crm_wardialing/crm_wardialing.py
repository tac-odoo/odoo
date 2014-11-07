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

	to_call = fields.Boolean("Call Center Call", default = False)
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
		self.state = "done"
		self.to_call = False

	@api.one
	def get_info(self):
		return {"id": self.id,
				"description": self.description,
				"partner_id": self.opportunity_id.partner_id.id,
				"partner_name": self.opportunity_id.partner_id.name,
				"partner_image_small": self.opportunity_id.partner_id.image_small,
				"partner_email": self.opportunity_id.partner_id.email,
				"partner_title": self.opportunity_id.partner_id.title.name,
				"partner_phone": self.opportunity_id.partner_id.phone,
				"partner_mobile": self.opportunity_id.partner_id.mobile,
				"opportunity_name": self.opportunity_id.name,
				"opportunity_id": self.opportunity_id.id,
				"opportunity_priority": self.opportunity_id.priority,
				"opportunity_planned_revenue": self.opportunity_id.planned_revenue,
				"opportunity_title_action": self.opportunity_id.title_action,
				"opportunity_company_currency": self.opportunity_id.company_currency.id,
				"opportunity_probability": self.opportunity_id.probability,
				"max_priority": self.opportunity_id._all_columns.get('priority').column.selection[-1][0]}

	@api.model
	def get_list(self, current_search):
		return {"phonecalls": self.search([('to_call','=',True),('user_id','=',self.env.user[0].id)], order='sequence, id').get_info()}

	@api.model
	def get_pbx_config(self):
		return {'pbx_ip':self.env['ir.config_parameter'].get_param('crm.wardialing.pbx_ip'),
				'wsServer':self.env['ir.config_parameter'].get_param('crm.wardialing.wsServer'),
				'login':self.env.user[0].sip_login,
				'password':self.env.user[0].sip_password,
				'physicalPhone':self.env.user[0].sip_physicalPhone,}
				
class crm_lead(models.Model):
	_inherit = "crm.lead"
	in_call_center_queue = fields.Boolean("Is in the Call Center Queue", compute='compute_is_call_center')

	@api.one
	def compute_is_call_center(self):
		phonecall = self.env['crm.phonecall'].search([('opportunity_id','=',self.id),('to_call','=',True),('user_id','=',self.env.user[0].id)])
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
		phonecall.to_call = True
		phonecall.opportunity_id = self.id
		phonecall.partner_id = self.partner_id
		phonecall.state = 'pending'
		return {
			'type': 'ir.actions.client',
			'tag': 'reload_panel',
		}

	@api.multi
	def delete_call_center_call(self):
		phonecall = self.env['crm.phonecall'].search([('opportunity_id','=',self.id),('to_call','=',True),('user_id','=',self.env.user[0].id)])
		phonecall.unlink()
		return {
			'type': 'ir.actions.client',
			'tag': 'reload_panel',
		}

class crm_phonecall_log_wizard(models.TransientModel):
	_name = 'crm.phonecall.log.wizard'

	@api.multi
	def _default_description(self):
		if(self._context.get('phonecall').get('description') == "There is no description"):
			return ""
		else:
			return self._context.get('phonecall').get('description')		
	
	@api.multi
	def _default_opportunity_name(self):
		return self._context.get('phonecall').get('opportunity_name')

	@api.multi
	def _default_duration(self):
		return self._context.get('phonecall').get('duration')
		
	description = fields.Text('Description', default = _default_description)
	opportunity_name = fields.Char(default = _default_opportunity_name, readonly=True)
	duration = fields.Float('Duration', default = _default_duration, readonly=True)
	@api.multi
	def save(self):
		phonecall = self.env['crm.phonecall'].browse(self._context.get('phonecall').get('id'))
		phonecall.description = self.description
		return {
			'type': 'ir.actions.client',
			'tag': 'reload_panel',
		}

class res_users(models.Model):
	_inherit = 'res.users'

	sip_login = fields.Char("SIP Login / Browser's Extension")
	sip_password = fields.Char('SIP Password')
	sip_physicalPhone = fields.Char("Physical Phone's Number")