# -*- coding: utf-8 -*-

from openerp import models, fields, api, _

class hr_applicant(models.Model):
    _inherit = 'hr.applicant'

    attachment_ids = fields.One2many('ir.attachment', 'res_id',
        domain= lambda self: [('res_model', '=', self._name)],
        auto_join=True,
        string='Attachments')
    attachment_content = fields.Text(related='attachment_ids.index_content', string='Resume Content')
