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

from openerp import models, fields, api, _
import time
import datetime
from openerp import tools
from openerp.osv.orm import except_orm
from openerp.tools.translate import _
from dateutil.relativedelta import relativedelta

def str_to_datetime(strdate):
    return datetime.datetime.strptime(strdate, tools.DEFAULT_SERVER_DATE_FORMAT)

class fleet_vehicle_cost(models.Model):
    _name = 'fleet.vehicle.cost'
    _description = 'Cost related to a vehicle'
    _order = 'date desc, vehicle_id asc'
   
    @api.one
    @api.depends('odometer_id')
    def _get_odometer(self):
        if self:
            self.odometer = self.odometer_id.value
       
    @api.one
    def _set_odometer(self, value):
        if not value:
            raise except_orm(_('Operation not allowed!'), _('Emptying the odometer value of a vehicle is not allowed.'))
        date = self.browse(self._id).date
        if not(date):
            date = fields.Date.today()
        vehicle_id = self.browse(self._id).vehicle_id
        data = {'value': value, 'date': date, 'vehicle_id': vehicle_id.id}
        odometer_id = self.env['fleet.vehicle.odometer'].create(data)
        return self.write({'odometer_id': odometer_id})
   
   
    name = fields.Char(related='vehicle_id.name', string='Name', store=True)
    vehicle_id = fields.Many2one(comodel_name='fleet.vehicle', string='Vehicle', required=True, help='Vehicle concerned by this log')
    cost_subtype_id = fields.Many2one(comodel_name='fleet.service.type', string='Type', help='Cost type purchased with this cost')
    amount = fields.Float(string='Total Price')
    cost_type = fields.Selection([('contract', 'Contract'), ('services','Services'), ('fuel','Fuel'), ('other','Other')], string='Category of the cost', default='other', help='For internal purpose only', required=True)
    parent_id = fields.Many2one(comodel_name='fleet.vehicle.cost', string='Parent', help='Parent cost to this current cost')
    cost_ids = fields.One2many(comodel_name='fleet.vehicle.cost', inverse_name='parent_id', string='Included Services')
    odometer_id = fields.Many2one(comodel_name='fleet.vehicle.odometer', string='Odometer', help='Odometer measure of the vehicle at the moment of this log')
    odometer = fields.Float(compute='_get_odometer', inverse='_set_odometer', string='Odometer Value', help='Odometer measure of the vehicle at the moment of this log')
    odometer_unit = fields.Selection(related='vehicle_id.odometer_unit', string='Unit', readonly=True)
    date = fields.Date(string='Date', help='Date when the cost has been executed')
    contract_id = fields.Many2one(comodel_name='fleet.vehicle.log.contract', string='Contract', help='Contract attached to this cost')
    auto_generated = fields.Boolean(string='Automatically Generated', readonly=True, required=True)
   
    @api.model
    def create(self, data):
        #make sure that the data are consistent with values of parent and contract records given
        if 'parent_id' in data and data['parent_id']:
            parent = self.browse(data['parent_id'])
            data['vehicle_id'] = parent.vehicle_id.id
            data['date'] = parent.date
            data['cost_type'] = parent.cost_type
        if 'contract_id' in data and data['contract_id']:
            contract = self.env['fleet.vehicle.log.contract'].browse(data['contract_id'])
            data['vehicle_id'] = contract.vehicle_id.id
            data['cost_subtype_id'] = contract.cost_subtype_id.id
            data['cost_type'] = contract.cost_type
        if 'odometer' in data and not data['odometer']:
            #if received value for odometer is 0, then remove it from the data as it would result to the creation of a
            #odometer log with 0, which is to be avoided
            del(data['odometer'])
        return super(fleet_vehicle_cost, self).create(data)
    

class fleet_vehicle_tag(models.Model):
    _name = 'fleet.vehicle.tag'

    name = fields.Char(string='Name', required=True, translate=True)


class fleet_vehicle_state(models.Model):
    _name = 'fleet.vehicle.state'
    _order = 'sequence asc'

    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer(string='Sequence', help="Used to order the note stages")

    _sql_constraints = [('fleet_state_name_unique','unique(name)', 'State name already exists')]


class fleet_vehicle_model(models.Model):

    @api.one
    @api.depends('modelname')
    def _model_name_get_fnc(self):
        name = self.modelname
        if self.brand_id.name:
            name = self.brand_id.name + ' / ' + name
        self.name = name

    @api.one
    @api.onchange('model_id')
    def on_change_brand(self):
        brand = self.env['fleet.vehicle.model.brand'].browse(self.model_id.id) 
        self.image_medium = brand.image,

    _name = 'fleet.vehicle.model'
    _description = 'Model of a vehicle'
    _order = 'name asc'

    name = fields.Char(compute='_model_name_get_fnc', string='Name', store=True)
    modelname = fields.Char(string='Model name', required=True)
    brand_id = fields.Many2one(comodel_name='fleet.vehicle.model.brand', string='Make', required=True, help='Make of the vehicle')
    vendors = fields.Many2many(comodel_name='res.partner', relation='fleet_vehicle_model_vendors', column1='model_id', column2='partner_id', string='Vendors')
    image = fields.Binary(related='brand_id.image', string="Logo")
    image_medium = fields.Binary(related='brand_id.image_medium', string="Logo (medium)")
    image_small = fields.Binary(related='brand_id.image_small', string="Logo (small)")


class fleet_vehicle_model_brand(models.Model):
    _name = 'fleet.vehicle.model.brand'
    _description = 'Brand model of the vehicle'

    _order = 'name asc'

    @api.multi
    def _get_image(self):
#         result = dict.fromkeys(ids, False)
        for obj in self:
            obj.image_medium = tools.image_get_resized_images(obj.image)
            obj.image_small = tools.image_get_resized_images(obj.image)
#         return result

    @api.multi
    def _set_image(self, value):
        return self.write([self._id], {'image': tools.image_resize_image_big(value)})

    name = fields.Char(string='Make', required=True)
    image = fields.Binary(string='Logo',
            help="This field holds the image used as logo for the brand, limited to 1024x1024px.")
    image_medium = fields.Binary(compute='_get_image', inverse='_set_image',
            string="Medium-sized photo", multi="_get_image",
            store = {
                'fleet.vehicle.model.brand': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Medium-sized logo of the brand. It is automatically "\
                 "resized as a 128x128px image, with aspect ratio preserved. "\
                 "Use this field in form views or some kanban views.")
    image_small = fields.Binary(compute='_get_image', inverse='_set_image',
            string="Smal-sized photo", multi="_get_image",
            store = {
                'fleet.vehicle.model.brand': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Small-sized photo of the brand. It is automatically "\
                 "resized as a 64x64px image, with aspect ratio preserved. "\
                 "Use this field anywhere a small image is required.")


class fleet_vehicle(models.Model):

    _inherit = 'mail.thread'

    @api.one
    @api.depends('license_plate')
    def _vehicle_name_get_fnc(self):
        if self.model_id:
            self.name = self.model_id.brand_id.name + '/' + self.model_id.modelname + ' / ' + self.license_plate
        else:
            self.name = ' '


    def return_action_to_open(self, cr, uid, ids, context=None):
        """ This opens the xml view specified in xml_id for the current vehicle """
        if context is None:
            context = {}
        if context.get('xml_id'):
            res = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid ,'fleet', context['xml_id'], context=context)
            res['context'] = context
            res['context'].update({'default_vehicle_id': ids[0]})
            res['domain'] = [('vehicle_id','=', ids[0])]
            return res
        return False

    def act_show_log_cost(self, cr, uid, ids, context=None):
        """ This opens log view to view and add new log for this vehicle, groupby default to only show effective costs
            @return: the costs log view
        """
        if context is None:
            context = {}
        res = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid ,'fleet','fleet_vehicle_costs_act', context=context)
        res['context'] = context
        res['context'].update({
            'default_vehicle_id': ids[0],
            'search_default_parent_false': True
        })
        res['domain'] = [('vehicle_id','=', ids[0])]
        return res

    @api.multi
    def _get_odometer(self):
        for record in self:
            ids = self.env['fleet.vehicle.odometer'].search([('vehicle_id', '=', record.id)], limit=1, order='value desc')
            if len(ids) > 0:
                self.odometer = ids.value
            else:
                self.odometer = 0.0

    @api.one
    def _set_odometer(self):
        if self.odometer_count:
            date = fields.Date.today()
            data = {'value': self.odometer_count, 'date': date, 'vehicle_id': self.id}
            return self.env['fleet.vehicle.odometer'].create(data)

    @api.multi
    def _search_get_overdue_contract_reminder(self, obj, name, args):
        res = []
        for field, operator, value in args:
            assert operator in ('=', '!=', '<>') and value in (True, False), 'Operation not supported'
            if (operator == '=' and value == True) or (operator in ('<>', '!=') and value == False):
                search_operator = 'in'
            else:
                search_operator = 'not in'
            today = fields.Date.today()
            self._cr.execute('select cost.vehicle_id, count(contract.id) as contract_number FROM fleet_vehicle_cost cost left join fleet_vehicle_log_contract contract on contract.cost_id = cost.id WHERE contract.expiration_date is not null AND contract.expiration_date < %s AND contract.state IN (\'open\', \'toclose\') GROUP BY cost.vehicle_id', (today,))
            res_ids = [x[0] for x in self._cr.fetchall()]
            res.append(('id', search_operator, res_ids))
        return res

    def _search_contract_renewal_due_soon(self, obj, name, args):
        res = []
        for field, operator, value in args:
            assert operator in ('=', '!=', '<>') and value in (True, False), 'Operation not supported'
            if (operator == '=' and value == True) or (operator in ('<>', '!=') and value == False):
                search_operator = 'in'
            else:
                search_operator = 'not in'
            today = fields.Date.today()
            datetime_today = datetime.datetime.strptime(today, tools.DEFAULT_SERVER_DATE_FORMAT)
            limit_date = str((datetime_today + relativedelta(days=+15)).strftime(tools.DEFAULT_SERVER_DATE_FORMAT))
            self._cr.execute('select cost.vehicle_id, count(contract.id) as contract_number FROM fleet_vehicle_cost cost left join fleet_vehicle_log_contract contract on contract.cost_id = cost.id WHERE contract.expiration_date is not null AND contract.expiration_date > %s AND contract.expiration_date < %s AND contract.state IN (\'open\', \'toclose\') GROUP BY cost.vehicle_id', (today, limit_date))
            res_ids = [x[0] for x in self._cr.fetchall()]
            res.append(('id', search_operator, res_ids))
        return res

    @api.multi
    def _get_contract_reminder_fnc(self):
        for record in self:
            overdue = False
            due_soon = False
            total = 0
            name = ''
            for element in record.log_contracts:
                if element.state in ('open', 'toclose') and element.expiration_date:
                    current_date_str = fields.Date.today()
                    due_time_str = element.expiration_date
                    current_date = str_to_datetime(current_date_str)
                    due_time = str_to_datetime(due_time_str)
                    diff_time = (due_time-current_date).days
                    if diff_time < 0:
                        overdue = True
                        total += 1
                    if diff_time < 15 and diff_time >= 0:
                            due_soon = True;
                            total += 1
                    if overdue or due_soon:
                        ids = self.env['fleet.vehicle.log.contract'].search([('vehicle_id', '=', record.id), ('state', 'in', ('open', 'toclose'))], limit=1, order='expiration_date asc')
                        if len(ids) > 0:
                            #we display only the name of the oldest overdue/due soon contract
                            name=(self.env['fleet.vehicle.log.contract'].browse(self._ids[0]).cost_subtype_id.name)

            record.contract_renewal_overdue = overdue
            record.contract_renewal_due_soon = due_soon
            record.contract_renewal_total = (total - 1) #we remove 1 from the real total for display purposes
            record.contract_renewal_name = name


    @api.one
    def _get_default_state(self):
        try:
            model, model_id = self.env['ir.model.data'].get_object_reference('fleet', 'vehicle_state_active')
        except ValueError:
            model_id = False
        return model_id
    
    @api.multi
    def _count_all(self):
        Odometer = self.env['fleet.vehicle.odometer']
        LogFuel = self.env['fleet.vehicle.log.fuel']
        LogService = self.env['fleet.vehicle.log.services']
        LogContract = self.env['fleet.vehicle.log.contract']
        Cost = self.env['fleet.vehicle.cost']
 
        for vehicle_id in self:
            vehicle_id.odometer_count = Odometer.search_count([('vehicle_id', '=', vehicle_id.id)])
            vehicle_id.fuel_logs_count = LogFuel.search_count([('vehicle_id', '=', vehicle_id.id)])
            vehicle_id.service_count = LogService.search_count([('vehicle_id', '=', vehicle_id.id)])
            vehicle_id.contract_count = LogContract.search_count([('vehicle_id', '=', vehicle_id.id)])
            vehicle_id.cost_count = Cost.search_count([('vehicle_id', '=', vehicle_id.id), ('parent_id', '=', False)])

    _name = 'fleet.vehicle'
    _description = 'Information on a vehicle'
    _order= 'license_plate asc'

    name = fields.Char(compute='_vehicle_name_get_fnc', string='Name', store=True)
    company_id = fields.Many2one(comodel_name='res.company', string='Company')
    license_plate = fields.Char(string='License Plate', required=True, help='License plate number of the vehicle (ie: plate number for a car)')
    vin_sn = fields.Char(string='Chassis Number', help='Unique number written on the vehicle motor (VIN/SN number)', copy=False)
    driver_id = fields.Many2one(comodel_name='res.partner', string='Driver', help='Driver of the vehicle')
    model_id = fields.Many2one(comodel_name='fleet.vehicle.model', string='Model', required=True, help='Model of the vehicle')
    log_fuel = fields.One2many(comodel_name='fleet.vehicle.log.fuel', inverse_name='vehicle_id', string='Fuel Logs')
    log_services = fields.One2many(comodel_name='fleet.vehicle.log.services', inverse_name='vehicle_id', string='Services Logs')
    log_contracts = fields.One2many(comodel_name='fleet.vehicle.log.contract', inverse_name='vehicle_id', string='Contracts')
    cost_count = fields.Integer(compute='_count_all', string="Costs" )
    contract_count = fields.Integer(compute='_count_all', string='Contracts')
    service_count = fields.Integer(compute='_count_all', string='Services')
    fuel_logs_count = fields.Integer(compute='_count_all', string='Fuel Logs')
    odometer_count = fields.Integer(compute='_count_all', string='Odometer')
    acquisition_date = fields.Date(string='Acquisition Date', required=False, help='Date when the vehicle has been bought')
    color = fields.Char(string='Color', help='Color of the vehicle')
    state_id = fields.Many2one(comodel_name='fleet.vehicle.state', string='State', default=_get_default_state, help='Current state of the vehicle', ondelete="set null")
    location = fields.Char(string='Location', help='Location of the vehicle (garage, ...)')
    seats = fields.Integer(string='Seats Number', help='Number of seats of the vehicle')
    doors = fields.Integer(string='Doors Number', default=5, help='Number of doors of the vehicle')
    tag_ids = fields.Many2many(comodel_name='fleet.vehicle.tag', relation='fleet_vehicle_vehicle_tag_rel', column1='vehicle_tag_id', column2='tag_id', string='Tags', copy=False)
    odometer = fields.Float(compute='_get_odometer', inverse='_set_odometer', string='Last Odometer', help='Odometer measure of the vehicle at the moment of this log')
    odometer_unit = fields.Selection([('kilometers', 'Kilometers'),('miles','Miles')], string='Odometer Unit', default='kilometers', help='Unit of the odometer ',required=True)
    transmission = fields.Selection([('manual', 'Manual'), ('automatic', 'Automatic')], string='Transmission', help='Transmission Used by the vehicle')
    fuel_type = fields.Selection([('gasoline', 'Gasoline'), ('diesel', 'Diesel'), ('electric', 'Electric'), ('hybrid', 'Hybrid')], string='Fuel Type', help='Fuel Used by the vehicle')
    horsepower = fields.Integer(string='Horsepower')
    horsepower_tax = fields.Float(string='Horsepower Taxation')
    power = fields.Integer(string='Power', help='Power in kW of the vehicle')
    co2 = fields.Float(string='CO2 Emissions', help='CO2 emissions of the vehicle')
    image = fields.Binary(related='model_id.image', string="Logo")
    image_medium = fields.Binary(related='model_id.image_medium', string="Logo (medium)")
    image_small = fields.Binary(related='model_id.image_small', string="Logo (small)")
    contract_renewal_due_soon = fields.Boolean(compute='_get_contract_reminder_fnc', fnct_search='_search_contract_renewal_due_soon', string='Has Contracts to renew', multi='contract_info')
    contract_renewal_overdue = fields.Boolean(compute='_get_contract_reminder_fnc', fnct_search='_search_get_overdue_contract_reminder', string='Has Contracts Overdued', multi='contract_info')
    contract_renewal_name = fields.Text(compute='_get_contract_reminder_fnc', string='Name of contract to renew soon', multi='contract_info')
    contract_renewal_total = fields.Integer(compute='_get_contract_reminder_fnc', string='Total of contracts due or overdue minus one', multi='contract_info')
    car_value = fields.Float(string='Car Value', help='Value of the bought vehicle')


    @api.one
    @api.depends('model_id')
    def on_change_model(self):
        model = self.env['fleet.vehicle.model'].browse(model_id.id)
    
        self.image_medium = model.image


    @api.model
    def create(self, data):
        vehicle_id = super(fleet_vehicle, self).create(data)
        vehicle_id.message_post(body=_('%s %s has been added to the fleet!') % (vehicle_id.model_id.name,vehicle_id.license_plate))
        return vehicle_id
    
    @api.multi
    def write(self, vals):
        """
        This function write an entry in the openchatter whenever we change important information
        on the vehicle like the model, the drive, the state of the vehicle or its license plate
        """
        for vehicle in self:
            changes = []
            if 'model_id' in vals and vehicle.model_id.id != vals['model_id']:
                value = vehicle.env['fleet.vehicle.model'].browse(vals['model_id']).name
                oldmodel = vehicle.model_id.name or _('None')
                changes.append(_("Model: from '%s' to '%s'") %(oldmodel, value))
            if 'driver_id' in vals and vehicle.driver_id.id != vals['driver_id']:
                value = vehicle.env['res.partner'].browse(vals['driver_id']).name
                olddriver = (vehicle.driver_id.name) or _('None')
                changes.append(_("Driver: from '%s' to '%s'") %(olddriver, value))
            if 'state_id' in vals and vehicle.state_id.id != vals['state_id']:
                value = vehicle.env['fleet.vehicle.state'].browse(vals['state_id']).name
                oldstate = vehicle.state_id.name or _('None')
                changes.append(_("State: from '%s' to '%s'") %(oldstate, value))
            if 'license_plate' in vals and vehicle.license_plate != vals['license_plate']:
                old_license_plate = vehicle.license_plate or _('None')
                changes.append(_("License Plate: from '%s' to '%s'") %(old_license_plate, vals['license_plate']))

            if len(changes) > 0:
                vehicle.message_post([vehicle.id], body=", ".join(changes))

        return super(fleet_vehicle, self).write(vals)


class fleet_vehicle_odometer(models.Model):
    _name='fleet.vehicle.odometer'
    _description='Odometer log for a vehicle'
    _order='date desc'

    @api.multi
    @api.depends('vehicle_id', 'date')
    def _vehicle_log_name_get_fnc(self):
        for record in self:
            print "------------", record.vehicle_id
            if record.vehicle_id:
                name = record.vehicle_id.name
                if record.date:
                    name = name+ ' / '+ str(record.date)
                record.name = name
            else:
                record.name = ' '
     
    @api.one
    @api.depends('vehicle_id')
    def on_change_vehicle(self):
        odometer_unit = self.env['fleet.vehicle'].browse(self.vehicle_id.id).odometer_unit       
        self.unit = odometer_unit
     
    name = fields.Char(compute='_vehicle_log_name_get_fnc', string='Name', store=True)
    date = fields.Date(string='Date', default=fields.Date.today())
    value = fields.Float(string='Odometer Value', group_operator="max")
    vehicle_id = fields.Many2one(comodel_name='fleet.vehicle', string='Vehicle', required=True)
    unit = fields.Selection(related='vehicle_id.odometer_unit', string="Unit", readonly=True)


class fleet_vehicle_log_fuel(models.Model):

    @api.one
    @api.onchange('vehicle_id')
    def on_change_vehicle(self):
        vehicle = self.env['fleet.vehicle'].browse(self.vehicle_id.id)
        odometer_unit = vehicle.odometer_unit
        driver = vehicle.driver_id.id
        
        self.odometer_unit = odometer_unit
        self.purchaser_id = driver

    @api.one
    @api.onchange('liter', 'price_per_liter', 'amount')
    def on_change_liter(self):
        #need to cast in float because the value receveid from web client maybe an integer (Javascript and JSON do not
        #make any difference between 3.0 and 3). This cause a problem if you encode, for example, 2 liters at 1.5 per
        #liter => total is computed as 3.0, then trigger an onchange that recomputes price_per_liter as 3/2=1 (instead
        #of 3.0/2=1.5)
        #If there is no change in the result, we return an empty dict to prevent an infinite loop due to the 3 intertwine
        #onchange. And in order to verify that there is no change in the result, we have to limit the precision of the 
        #computation to 2 decimal
        if self.liter > 0 and self.price_per_liter > 0 and round(self.liter*self.price_per_liter,2) != self.amount:
            self.amount = round(self.liter * self.price_per_liter,2)
        elif self.amount > 0 and self.liter > 0 and round(self.amount/self.liter,2) != self.price_per_liter:
            self.price_per_liter = round(self.amount / self.liter,2)
        elif self.amount > 0 and self.price_per_liter > 0 and round(self.amount/self.price_per_liter,2) != self.liter:
            self.liter = round(self.amount / self.price_per_liter,2)

    @api.one
    @api.onchange('liter', 'price_per_liter', 'amount')
    def on_change_price_per_liter(self):
        #need to cast in float because the value receveid from web client maybe an integer (Javascript and JSON do not
        #make any difference between 3.0 and 3). This cause a problem if you encode, for example, 2 liters at 1.5 per
        #liter => total is computed as 3.0, then trigger an onchange that recomputes price_per_liter as 3/2=1 (instead
        #of 3.0/2=1.5)
        #If there is no change in the result, we return an empty dict to prevent an infinite loop due to the 3 intertwine
        #onchange. And in order to verify that there is no change in the result, we have to limit the precision of the 
        #computation to 2 decimal
        if self.liter > 0 and self.price_per_liter > 0 and round(self.liter*self.price_per_liter,2) != self.amount:
            self.amount = round(self.liter * self.price_per_liter,2)
        elif self.amount > 0 and self.price_per_liter > 0 and round(self.amount/self.price_per_liter,2) != self.liter:
            self.liter = round(self.amount / self.price_per_liter,2)
        elif self.amount > 0 and self.liter > 0 and round(self.amount/self.liter,2) != self.price_per_liter:
            self.price_per_liter = round(self.amount / self.liter,2)


    @api.one
    @api.onchange('liter', 'price_per_liter', 'amount')
    def on_change_amount(self):
        #need to cast in float because the value receveid from web client maybe an integer (Javascript and JSON do not
        #make any difference between 3.0 and 3). This cause a problem if you encode, for example, 2 liters at 1.5 per
        #liter => total is computed as 3.0, then trigger an onchange that recomputes price_per_liter as 3/2=1 (instead
        #of 3.0/2=1.5)
        #If there is no change in the result, we return an empty dict to prevent an infinite loop due to the 3 intertwine
        #onchange. And in order to verify that there is no change in the result, we have to limit the precision of the 
        #computation to 2 decimal
        if self.amount > 0 and self.liter > 0 and round(self.amount/self.liter,2) != self.price_per_liter:
            self.price_per_liter = round(self.amount / self.liter,2)
        elif self.amount > 0 and self.price_per_liter > 0 and round(self.amount/self.price_per_liter,2) != self.liter:
            self.liter = round(self.amount / self.price_per_liter,2)
        elif self.liter > 0 and self.price_per_liter > 0 and round(self.liter*self.price_per_liter,2) != self.amount:
            self.amount = round(self.liter * self.price_per_liter,2)

    @api.model
    def _get_default_service_type(self):
        try:
            model, model_id = self.env['ir.model.data'].get_object_reference('fleet', 'type_service_refueling')
        except ValueError:
            model_id = False
        return model_id

    _name = 'fleet.vehicle.log.fuel'
    _description = 'Fuel log for vehicles'
    _inherits = {'fleet.vehicle.cost': 'cost_id'}

    liter = fields.Float(string='Liter')
    price_per_liter = fields.Float(string='Price Per Liter')
    purchaser_id = fields.Many2one(comodel_name='res.partner', string='Purchaser', domain="['|',('customer','=',True),('employee','=',True)]")
    inv_ref = fields.Char(string='Invoice Reference', size=64)
    vendor_id = fields.Many2one(comodel_name='res.partner', string='Supplier', domain="[('supplier','=',True)]")
    notes = fields.Text(string='Notes')
    cost_id = fields.Many2one(comodel_name='fleet.vehicle.cost', string='Cost', required=True, ondelete='cascade')
    cost_amount = fields.Float(related='cost_id.amount', string='Amount', store=True) #we need to keep this field as a related with store=True because the graph view doesn't support (1) to address fields from inherited table and (2) fields that aren't stored in database
        
    _defaults = {
        'date': fields.Date.today(),
        'cost_subtype_id': _get_default_service_type,
        'cost_type': 'fuel',
    }


class fleet_vehicle_log_services(models.Model):
 
    @api.one
    @api.onchange('vehicle_id')
    def on_change_vehicle(self):
        vehicle = self.env['fleet.vehicle'].browse(self.vehicle_id.id)
        odometer_unit = vehicle.odometer_unit
        driver = vehicle.driver_id.id

        self.odometer_unit = odometer_unit
        self.purchaser_id = driver

  
    @api.model
    def _get_default_service_type(self):
        try:
            model, model_id = self.env['ir.model.data'].get_object_reference('fleet', 'type_service_service_8')
        except ValueError:
            model_id = False
        return model_id

    _inherits = {'fleet.vehicle.cost': 'cost_id'}
    _name = 'fleet.vehicle.log.services'
    _description = 'Services for vehicles'
 
    purchaser_id = fields.Many2one(comodel_name='res.partner', string='Purchaser', domain="['|',('customer','=',True),('employee','=',True)]")
    inv_ref = fields.Char(string='Invoice Reference')
    vendor_id = fields.Many2one(comodel_name='res.partner', string='Supplier', domain="[('supplier','=',True)]")
    cost_amount = fields.Float(related='cost_id.amount', string='Amount', store=True) #we need to keep this field as a related with store=True because the graph view doesn't support (1) to address fields from inherited table and (2) fields that aren't stored in database
    notes = fields.Text(string='Notes')
    cost_id = fields.Many2one(comodel_name='fleet.vehicle.cost', string='Cost', required=True, ondelete='cascade')
         
    _defaults = {
        'date': fields.Date.today(),
        'cost_subtype_id': _get_default_service_type,
        'cost_type': 'services'
    }


class fleet_service_type(models.Model):
    _name = 'fleet.service.type'
    _description = 'Type of services available on a vehicle'

    name = fields.Char(string='Name', required=True, translate=True)
    category = fields.Selection([('contract', 'Contract'), ('service', 'Service'), ('both', 'Both')], string='Category', required=True, help='Choose wheter the service refer to contracts, vehicle services or both')


class fleet_vehicle_log_contract(models.Model):

    @api.multi
    def scheduler_manage_auto_costs(self):
        #This method is called by a cron task
        #It creates costs for contracts having the "recurring cost" field setted, depending on their frequency
        #For example, if a contract has a reccuring cost of 200 with a weekly frequency, this method creates a cost of 200 on the first day of each week, from the date of the last recurring costs in the database to today
        #If the contract has not yet any recurring costs in the database, the method generates the recurring costs from the start_date to today
        #The created costs are associated to a contract thanks to the many2one field contract_id
        #If the contract has no start_date, no cost will be created, even if the contract has recurring costs
        vehicle_cost_obj = self.env['fleet.vehicle.cost']
        d = datetime.datetime.strptime(fields.Date.today(), tools.DEFAULT_SERVER_DATE_FORMAT).date()
        contract_ids = self.env['fleet.vehicle.log.contract'].search([('state','!=','closed')], offset=0, limit=None, order=None, count=False)
        deltas = {'yearly': relativedelta(years=+1), 'monthly': relativedelta(months=+1), 'weekly': relativedelta(weeks=+1), 'daily': relativedelta(days=+1)}
        for contract in self.env['fleet.vehicle.log.contract'].browse(contract_ids):
            if not contract.start_date or contract.cost_frequency == 'no':
                continue
            found = False
            last_cost_date = contract.start_date
            if contract.generated_cost_ids:
                last_autogenerated_cost_id = vehicle_cost_obj.search(['&', ('contract_id','=',contract.id), ('auto_generated','=',True)], offset=0, limit=1, order='date desc', count=False)
                if last_autogenerated_cost_id:
                    found = True
                    last_cost_date = vehicle_cost_obj.browse(last_autogenerated_cost_id[0]).date
            startdate = datetime.datetime.strptime(last_cost_date, tools.DEFAULT_SERVER_DATE_FORMAT).date()
            if found:
                startdate += deltas.get(contract.cost_frequency)
            while (startdate <= d) & (startdate <= datetime.datetime.strptime(contract.expiration_date, tools.DEFAULT_SERVER_DATE_FORMAT).date()):
                data = {
                    'amount': contract.cost_generated,
                    'date': startdate.strftime(tools.DEFAULT_SERVER_DATE_FORMAT),
                    'vehicle_id': contract.vehicle_id.id,
                    'cost_subtype_id': contract.cost_subtype_id.id,
                    'contract_id': contract.id,
                    'auto_generated': True
                }
                cost_id = self.env['fleet.vehicle.cost'].create(data)
                startdate += deltas.get(contract.cost_frequency)
        return True

    @api.multi
    def scheduler_manage_contract_expiration(self):
        #This method is called by a cron task
        #It manages the state of a contract, possibly by posting a message on the vehicle concerned and updating its status
        datetime_today = datetime.datetime.strptime(fields.Date.today(), tools.DEFAULT_SERVER_DATE_FORMAT)
        limit_date = (datetime_today + relativedelta(days=+15)).strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
        ids = self.search(['&', ('state', '=', 'open'), ('expiration_date', '<', limit_date)], offset=0, limit=None, order=None, count=False)
        res = {}
        for contract in self:
            if contract.vehicle_id.id in res:
                res[contract.vehicle_id.id] += 1
            else:
                res[contract.vehicle_id.id] = 1

        for vehicle, value in res.items():
            self.env['fleet.vehicle'].message_post(vehicle, body=_('%s contract(s) need(s) to be renewed and/or closed!') % (str(value)))
        return self.write({'state': 'toclose'})


    @api.one
    def run_scheduler(self):
        self.scheduler_manage_auto_costs()
        self.scheduler_manage_contract_expiration()
        return True


    @api.multi
    def _vehicle_contract_name_get_fnc(self):
#         res = {}
        for record in self:
            name = record.vehicle_id.name
            if record.cost_subtype_id.name:
                name += ' / '+ record.cost_subtype_id.name
            if record.date:
                name += ' / '+ record.date
            record.name = name
#         return res

    @api.one
    @api.depends('vehicle_id')
    def on_change_vehicle(self):
        odometer_unit = self.env['fleet.vehicle'].browse(vehicle_id.id).odometer_unit
        
        self.odometer_unit = odometer_unit

    @api.one
    def compute_next_year_date(self, strdate):
        oneyear = datetime.timedelta(days=365)
        curdate = str_to_datetime(strdate)
        return datetime.datetime.strftime(curdate + oneyear, tools.DEFAULT_SERVER_DATE_FORMAT)

    @api.one
    def on_change_start_date(self, strdate, enddate):
        if (strdate):
            return {'value': {'expiration_date': self.compute_next_year_date(strdate),}}
        return {}

    @api.multi
    def get_days_left(self):
        """return a dict with as value for each contract an integer
        if contract is in an open state and is overdue, return 0
        if contract is in a closed state, return -1
        otherwise return the number of days before the contract expires
        """
#         res = {}
        for record in self:
            if (record.expiration_date and (record.state == 'open' or record.state == 'toclose')):
                today = str_to_datetime(time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT))
                renew_date = str_to_datetime(record.expiration_date)
                diff_time = (renew_date-today).days
                record.days_left = diff_time > 0 and diff_time or 0
            else:
                record.days_left = -1


    @api.multi
    def act_renew_contract(self):
        assert len(self._ids) == 1, "This operation should only be done for 1 single contract at a time, as it it suppose to open a window as result"
        for element in self:
            #compute end date
            startdate = str_to_datetime(element.start_date)
            enddate = str_to_datetime(element.expiration_date)
            diffdate = (enddate - startdate)
            default = {
                'date': fields.Date.today(),
                'start_date': datetime.datetime.strftime(str_to_datetime(element.expiration_date) + datetime.timedelta(days=1), tools.DEFAULT_SERVER_DATE_FORMAT),
                'expiration_date': datetime.datetime.strftime(enddate + diffdate, tools.DEFAULT_SERVER_DATE_FORMAT),
            }
            newid = super(fleet_vehicle_log_contract, element).copy(default)
        mod, modid = self.env['ir.model.data'].get_object_reference('fleet', 'fleet_vehicle_log_contract_form')
        return {
            'name':_("Renew Contract"),
            'view_mode': 'form',
            'view_id': modid,
            'view_type': 'tree,form',
            'res_model': 'fleet.vehicle.log.contract',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'domain': '[]',
            'res_id': newid,
            'context': {'active_id':newid}, 
        }

    @api.one
    def _get_default_contract_type(self):
        try:
            model, model_id = self.env['ir.model.data'].get_object_reference('fleet', 'type_contract_leasing')
        except ValueError:
            model_id = False
        return model_id


    @api.one
    @api.depends('cost_ids')
    def on_change_indic_cost(self):
        totalsum = 0.0
        for element in cost_ids:
            if element and len(element) == 3 and isinstance(element[2], dict):
                totalsum += element[2].get('amount', 0.0)

        self.sum_cost = totalsum

    @api.multi
    def _get_sum_cost(self):
#         res = {}
        for contract in self:
            totalsum = 0
            for cost in contract.cost_ids:
                totalsum += cost.amount
            self.sum_cost = totalsum
#         return res

    _inherits = {'fleet.vehicle.cost': 'cost_id'}
    _name = 'fleet.vehicle.log.contract'
    _description = 'Contract information on a vehicle'
    _order='state desc,expiration_date'

    name = fields.Text(compute='_vehicle_contract_name_get_fnc', string='Name', store=True)
    start_date = fields.Date(string='Contract Start Date', default=fields.Date.today(), help='Date when the coverage of the contract begins')
    expiration_date = fields.Date(string='Contract Expiration Date', default=lambda self: self.compute_next_year_date(fields.Date.today()), 
                                  help='Date when the coverage of the contract expirates (by default, one year after begin date)')
    days_left = fields.Integer(compute='get_days_left', string='Warning Date')
    insurer_id = fields.Many2one(comodel_name='res.partner', string='Supplier')
    purchaser_id = fields.Many2one(comodel_name='res.partner', string='Contractor', default=lambda self: self.env['res.users'].browse(self._uid).partner_id.id or False, help='Person to which the contract is signed for')
    ins_ref = fields.Char(string='Contract Reference', size=64, copy=False)
    state = fields.Selection([('open', 'In Progress'), ('toclose','To Close'), ('closed', 'Terminated')],
                                  string='Status', readonly=True, default='open',
                                  help='Choose wheter the contract is still valid or not', copy=False)
    notes = fields.Text(string='Terms and Conditions', help='Write here all supplementary informations relative to this contract', copy=False)
    cost_generated = fields.Float(string='Recurring Cost Amount', help="Costs paid at regular intervals, depending on the cost frequency. If the cost frequency is set to unique, the cost will be logged at the start date")
    cost_frequency = fields.Selection([('no','No'), ('daily', 'Daily'), ('weekly','Weekly'), ('monthly','Monthly'), ('yearly','Yearly')], string='Recurring Cost Frequency', default='no', help='Frequency of the recuring cost', required=True)
    generated_cost_ids = fields.One2many(comodel_name='fleet.vehicle.cost', inverse_name='contract_id', string='Generated Costs')
    sum_cost = fields.Float(compute='_get_sum_cost', string='Indicative Costs Total')
    cost_id = fields.Many2one(comodel_name='fleet.vehicle.cost', string='Cost', required=True, ondelete='cascade')
    cost_amount = fields.Float(related='cost_id.amount', string='Amount', store=True) #we need to keep this field as a related with store=True because the graph view doesn't support (1) to address fields from inherited table and (2) fields that aren't stored in database

    _defaults = {
        'date': fields.Date.today(),
        'cost_subtype_id': _get_default_contract_type,
        'cost_type': 'contract',
    }

    @api.one
    def contract_close(self):
        return self.write({'state': 'closed'})

    @api.one
    def contract_open(self):
        return self.write({'state': 'open'})


class fleet_contract_state(models.Model):
    _name = 'fleet.contract.state'
    _description = 'Contains the different possible status of a leasing contract'

    name = fields.Char(string='Contract Status', required=True)
