from openerp.osv import osv, fields
from openerp import SUPERUSER_ID
from openerp.addons.website.models.website import slugify
from openerp.addons.web.http import request


class website(osv.osv):

    _inherit = "website"

    def _get_menu(self, cr, uid, ids, name, arg, context=None):
        result = {}
        menu_obj = self.pool['website.menu']

        for id in ids:
            menu_ids = menu_obj.search(cr, uid, [
                ('parent_id', '=', False),
                ('website_id', '=', id)
            ], order='id', context=context)
            result[id] = menu_ids and menu_ids[0] or False

        return result

    _columns = {
        'menu_id': fields.function(_get_menu, relation='website.menu', type="many2one", string="Main Menu")
    }

    _defaults = {
        'user_id': lambda s, c, u, x: s.pool['ir.model.data'].xmlid_to_res_id(c, SUPERUSER_ID, 'base.public_user'),
        'company_id': lambda s, c, u, x: s.pool['ir.model.data'].xmlid_to_res_id(c, SUPERUSER_ID, 'base.main_company')
    }

    def new_page(self, cr, uid, name, template='website.default_page', ispage=True, context=None):
        context = context or {}
        imd = self.pool.get('ir.model.data')
        view = self.pool.get('ir.ui.view')
        template_module, template_name = template.split('.')

        # completely arbitrary max_length
        page_name = slugify(name, max_length=50)
        page_xmlid = "%s.%s" % (template_module, page_name)

        try:
            # existing page
            imd.get_object_reference(cr, uid, template_module, page_name)
        except ValueError:
            # new page
            _, template_id = imd.get_object_reference(cr, uid, template_module, template_name)
            website_id = context.get('website_id')
            key = template_module + '.' + page_name
            page_id = view.copy(cr, uid, template_id, {
                'website_id': website_id,
                'key': key
            }, context=context)
            page = view.browse(cr, uid, page_id, context=context)
            page.write({
                'arch': page.arch.replace(template, page_xmlid),
                'name': page_name,
                'page': ispage,
            })
            imd.create(cr, uid, {
                'name': page_name,
                'module': template_module,
                'model': 'ir.ui.view',
                'res_id': page_id,
                'noupdate': True
            }, context=context)
        return page_xmlid

    def get_current_website(self, cr, uid, context=None):
        domain_name = request.httprequest.host.split(":")[0].lower()
        ids = self.search(cr, uid, [
            ('name', '=', domain_name)
        ], context=context)
        website = self.browse(cr, uid, ids and ids[0] or 1, context=context)
        return website

    def get_template(self, cr, uid, ids, template, context=None):
        if isinstance(template, (int, long)):
            view_id = template
        else:
            if '.' not in template:
                template = 'website.%s' % template
            module, xmlid = template.split('.', 1)
            website_id = request.context.get('website_id')
            view_id = self.pool['ir.ui.view'].search(cr, uid, [
                ('key', '=', template),
                '|',
                ('website_id', '=', website_id),
                ('website_id', '=', False)
            ], order="website_id", limit=1, context=context)

        return self.pool["ir.ui.view"].browse(cr, uid, view_id, context=context)
