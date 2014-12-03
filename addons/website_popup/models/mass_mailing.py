# -*- coding: utf-8 -*-

from openerp import api, fields, models


class MassMailingList(models.Model):
    _inherit = 'mail.mass_mailing.list'

    popup_content = fields.Html(string="Popup content", translate=True, required=True, default=lambda self: self._default_content())
    popup_redirect_url = fields.Char(string="Popup Redirect URL")

    @api.model
    def _default_content(self):
        return """<div class="text-center">
                    <h2>Grow Your Business With Odoo Apps</h2>
                    <h3>Join Odoo newsletter &amp; get answer instantly.</h3>
                    <h3>Where Should We Send Your</h3>
                    <h1>FREE</h1>
                    Guide with sample Theme
                    <h1> Odoo Design Templates</h1>
                  </div>"""
