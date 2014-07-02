from openerp.osv import fields, osv


class website(osv.osv):
    _inherit = "website"

    _columns = {
        'google_search_published': fields.boolean('Show Google\'s Custom Search on Website'),
        'google_search_cx': fields.char('Google\'s Custom Search Engine ID'),
    }
