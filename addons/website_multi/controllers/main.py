import re

import werkzeug

from openerp.addons.web import http
from openerp.http import request
from openerp.addons.website.controllers.main import Website


class website_multi(Website):

    @http.route('/website/add/<path:path>', type='http', auth="user", website=True)
    def pagenew(self, path, noredirect=False, add_menu=None):
        cr, uid, context = request.cr, request.uid, request.context

        xml_id = request.registry['website'].new_page(request.cr, request.uid, path, context=request.context)
        if add_menu:
            request.registry['website.menu'].create(cr, uid, {
                'name': path,
                'url': '/page/' + xml_id,
                'parent_id': request.website.menu_id.id,
                'website_id': request.website.id
            }, context=context)

        # Reverse action in order to allow shortcut for /page/<website_xml_id>
        url = "/page/" + re.sub(r"^website\.", '', xml_id)

        if noredirect:
            return werkzeug.wrappers.Response(url, mimetype='text/plain')

        return werkzeug.utils.redirect(url)
