# -*- coding: utf-8 -*-
from openerp import api, models, fields


class res_partner(models.Model):

    _inherit = "res.partner"

    @api.multi
    @api.depends('street', 'zip', 'country_id', 'state_id', 'city')
    def _compute_sendable_address(self):
        for partner in self:
            partner.has_sendable_address = bool(partner.street and partner.city and partner.zip and partner.country_id)


    has_sendable_address = fields.Boolean(string='Has correct address', readonly=True, store=False, compute=_compute_sendable_address)
