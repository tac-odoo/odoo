
from openerp.osv import fields, osv

class event_config_settings(osv.osv_memory):
    _inherit = 'marketing.config.settings'

    _columns = {
        'group_event_manage_tickets': fields.boolean('Manage Event Tickets',
            implied_group='event_sale.group_event_manage_tickets',
            help='Manage different kind of tickets: vip, free, ... '),
    }
