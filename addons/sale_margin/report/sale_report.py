# -*- coding: utf-8 -*-

from openerp import models, fields


class sale_report(models.Model):
    _inherit = "sale.report"

    margin = fields.Float('#Margin')

    def _select(self):
        return super(sale_report, self)._select() + ", l.margin as margin"

    def _group_by(self):
        return super(sale_report, self)._group_by() + ", l.margin"
