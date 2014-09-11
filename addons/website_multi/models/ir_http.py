from openerp.osv import orm
from openerp.http import request


class ir_http(orm.AbstractModel):

    _inherit = 'ir.http'

    def _dispatch(self):
        result = super(ir_http, self)._dispatch()

        if request.website_enabled:
            request.context['website_id'] = request.website.id

        return result
