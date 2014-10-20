# -*- encoding: utf-8 -*-

from openerp import models, api

class lunch_order_order(models.TransientModel):
    """ lunch order meal """
    _name = 'lunch.order.order'
    _description = 'Wizard to order a meal'

    @api.multi
    def order(self):
        return self.env['lunch.order.line'].order()
