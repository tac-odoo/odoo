from openerp.osv import orm
from openerp.http import request


class ir_http(orm.AbstractModel):

    _inherit = 'ir.http'

    def _dispatch(self):
        result = super(ir_http, self)._dispatch()

        if hasattr(request, 'website_enabled'):
            import pudb
            pudb.set_trace()
            request.context['website_id'] = request.website.id
            request.website = request.website.with_context(request.context)

        return result
