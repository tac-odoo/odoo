
from openerp.osv import fields, osv

class event_config_settings(osv.osv_memory):
    _inherit = 'marketing.config.settings'

    _columns = {
        'group_publish_events': fields.boolean('Publish your event',
            implied_group='website_event.group_publish_events',
            help='Publish your event in the web.'),
        'module_website_event_track': fields.boolean('Manage advanced event features',
            help='Manage advanced event features like etracking, agenda, sponsors.\n'
                '-This installs the module website_event_track.'),
    }
