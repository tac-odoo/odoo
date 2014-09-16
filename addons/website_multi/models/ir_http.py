from openerp.osv import orm
from openerp.http import request


class ir_http(orm.AbstractModel):

    _inherit = 'ir.http'

    def _dispatch(self):
        if request.website_enabled:
            request.context['website_id'] = request.website.id
            request.website = request.website.with_context(request.context)

        return super(ir_http, self)._dispatch()
