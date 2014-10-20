# -*- encoding: utf-8 -*-

from openerp import models, api

class lunch_cancel(models.Model):
    """ lunch cancel """
    _name = 'lunch.cancel'
    _description = 'cancel lunch order'

    @api.multi
    def cancel(self):
        return self.env['lunch.order.line'].cancel()
