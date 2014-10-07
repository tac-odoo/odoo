# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012-today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from openerp import api, fields, models


class base_config_settings(models.TransientModel):
    _inherit = "base.config.settings"

    default_print_provider = fields.Many2one('print.provider', string='Default Print Provider')


    @api.model
    def get_default_print_provider(self, fields):
        default_provider = False
        if('default_print_provider' in fields):
            default_provider = self.env['ir.values'].get_default('print.order', 'provider_id')
        return {
            'default_print_provider': default_provider
        }

    @api.multi
    def set_default_print_provider(self):
        for wizard in self:
            self.env['ir.values'].sudo().set_default('print.order', 'provider_id', wizard.default_print_provider.id)
