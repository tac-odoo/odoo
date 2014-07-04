from openerp.osv import fields, osv


class website_config_settings(osv.osv_memory):
    _inherit = "website.config.settings"

    _columns = {
        'google_search_published': fields.related('website_id', 'google_search_published', type='boolean', string='Show Google\'s Custom Search on Website'),
        'google_search_cx': fields.related('website_id', 'google_search_cx', type='char', string='Google\'s Custom Search Engine ID'),
        'google_search_key': fields.related('website_id', 'google_search_key', type='char', string='Google\'s Custom Search API Key'),
    }
