# -*- encoding: utf-8 -*-

from openerp import models, api

class lunch_validation(models.Model):
    """ lunch validation """
    _name = 'lunch.validation'
    _description = 'lunch validation for order'

    @api.multi
    def confirm(self):
        return self.env['lunch.order.line'].confirm()
