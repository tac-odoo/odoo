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

    def create(self, cr, uid, values, context=None):
        self._read_template.clear_cache(self)
        return super(view, self).create(
            cr, uid,
            self._compute_defaults(cr, uid, values, context=context),
            context=context)

    def write(self, cr, uid, ids, vals, context=None):
        self._read_template.clear_cache(self)
        ret = super(view, self).write(
            cr, uid, ids,
            self._compute_defaults(cr, uid, vals, context=context),
            context)
        return ret

    _read_template_cache = dict(accepted_keys=('lang', 'inherit_branding', 'editable', 'translatable'))
    if config['dev_mode']:
        _read_template_cache['size'] = 0

    @tools.ormcache_context(**_read_template_cache)
    def _read_template(self, cr, uid, view_id, context=None):
        arch = self.read_combined(cr, uid, view_id, fields=['arch'], context=context)['arch']
        arch_tree = etree.fromstring(arch)

        if 'lang' in context:
            arch_tree = self.translate_qweb(cr, uid, view_id, arch_tree, context['lang'], context)

        self.distribute_branding(arch_tree)
        root = etree.Element('templates')
        root.append(arch_tree)
        arch = etree.tostring(root, encoding='utf-8', xml_declaration=True)
        return arch

    @tools.dummy_cache()
    def read_template(self, cr, uid, xml_id, context=None):
        if isinstance(xml_id, (int, long)):
            view_id = xml_id
        else:
            if '.' not in xml_id:
                raise ValueError('Invalid template id: %r' % (xml_id,))
            view_id = self.get_view_id(cr, uid, xml_id, context=context)
        return self._read_template(cr, uid, view_id, context=context)

    @tools.ormcache(skiparg=3)
    def get_view_id(self, cr, uid, xml_id, context=None):
        return self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, xml_id, raise_if_not_found=True)

    def clear_cache(self):
        self._read_template.clear_cache(self)
