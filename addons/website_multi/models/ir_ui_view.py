from openerp import tools
from openerp.osv import osv, fields


class view(osv.osv):

    _inherit = "ir.ui.view"

    _columns = {
        'website_id': fields.many2one('website', ondelete='cascade', string="Website"),
        'key': fields.char('Key')
    }

    _sql_constraints = [(
        'key_website_id_unique',
        'unique(key, website_id)',
        'Key must be unique per website.'
    )]
