
from openerp.osv import fields, osv

class event_config_settings(osv.osv_memory):
    _inherit = 'marketing.config.settings'

    _columns = {
        'group_publish_events': fields.boolean('Publish your event',
            implied_group='website_event.group_publish_events',
            help='Publish your event in the web.'),
        'group_advanced_event_features': fields.boolean('Manage advanced event features',
            implied_group='website_event.group_advanced_event_features',
            help='Manage advanced event features like etracking, agenda, sponsors.'),
    }
