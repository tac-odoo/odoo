from openerp.osv import fields, osv


class website_config_settings(osv.osv_memory):
    _inherit = "website.config.settings"

    _columns = {
        'google_search_published': fields.related('website_id', 'google_search_published', type='boolean', string='Show Google\'s Custom Search on Website')
    }
