# -*- coding: utf-8 -*-
import urlparse
from openerp import api, fields, models


class HrConfigSettings(models.TransientModel):
    _inherit = 'hr.config.settings'

    alias_manage = fields.Boolean('Alias Manage')
    material_alias_prefix = fields.Char('Use alias to report internal material issue')
    alias_domain = fields.Char("Alias Domain")

    @api.multi
    def get_default_alias_domain(self):
        alias_domain = self.env['ir.config_parameter'].get_param("mail.catchall.domain")
        if not alias_domain:
            domain = self.env["ir.config_parameter"].get_param("web.base.url")
            try:
                alias_domain = urlparse.urlsplit(domain).netloc.split(':')[0]
            except Exception:
                pass
        return {'alias_domain': alias_domain}

    @api.multi
    def set_default_alias_manage(self):
        config_value = self.alias_manage
        self.env['ir.values'].set_default('hr.config.settings', 'alias_manage', config_value)

    @api.onchange('alias_manage')
    def onchange_alias_manage(self):
        if not self.alias_manage:
            self.material_alias_prefix = False

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
