# -*- coding: utf-8 -*-
import copy
import logging

from lxml import etree, html

from openerp import SUPERUSER_ID, tools
from openerp.addons.website.models import website
from openerp.http import request
from openerp.osv import osv, fields

_logger = logging.getLogger(__name__)


class view(osv.osv):
    _inherit = "ir.ui.view"
    _columns = {
        'page': fields.boolean("Whether this view is a web page template (complete)"),
        'website_meta_title': fields.char("Website meta title", size=70, translate=True),
        'website_meta_description': fields.text("Website meta description", size=160, translate=True),
        'website_meta_keywords': fields.char("Website meta keywords", translate=True),
        'customize_show': fields.boolean("Show As Optional Inherit"),
        'website_id': fields.many2one('website', ondelete='cascade', string="Website"),
    }

    _sql_constraints = [
        ('key_website_id_uniq', 'unique(key, website_id)',
            'Key must be unique per website.'),
    ]

    _defaults = {
        'page': False,
        'customize_show': False,
    }

    def _view_obj(self, cr, uid, view_id, context=None):
        if isinstance(view_id, basestring):
            return self.pool['ir.model.data'].xmlid_to_object(
                cr, uid, view_id, raise_if_not_found=True, context=context
            )
        elif isinstance(view_id, (int, long)):
            return self.browse(cr, uid, view_id, context=context)

        # assume it's already a view object (WTF?)
        return view_id

    # Returns all views (called and inherited) related to a view
    # Used by translation mechanism, SEO and optional templates
    def _views_get(self, cr, uid, view_id, options=True, bundles=False, context=None, root=True):
        """ For a given view ``view_id``, should return:

        * the view itself
        * all views inheriting from it, enabled or not
          - but not the optional children of a non-enabled child
        * all views called from it (via t-call)
        """

        try:
            view = self._view_obj(cr, uid, view_id, context=context)
        except ValueError:
            _logger.warning("Could not find view object with view_id '%s'" % (view_id))
            # Shall we log that ? Yes, you should !
            return []

        while root and view.inherit_id:
            view = view.inherit_id

        result = [view]

        node = etree.fromstring(view.arch)
        xpath = "//t[@t-call]"
        if bundles:
            xpath += "| //t[@t-call-assets]"
        for child in node.xpath(xpath):
            try:
                called_view = self._view_obj(cr, uid, child.get('t-call', child.get('t-call-assets')), context=context)
            except ValueError:
                continue
            if called_view not in result:
                result += self._views_get(cr, uid, called_view, options=options, bundles=bundles, context=context)

        extensions = view.inherit_children_ids
        if not options:
            # only active children
            extensions = (v for v in view.inherit_children_ids if v.active)

        # Keep options in a deterministic order regardless of their applicability
        for extension in sorted(extensions, key=lambda v: v.id):
            for r in self._views_get(
                    cr, uid, extension,
                    # only return optional grandchildren if this child is enabled
                    options=extension.active,
                    context=context, root=False):
                if r not in result:
                    result.append(r)
        return result

    def extract_embedded_fields(self, cr, uid, arch, context=None):
        return arch.xpath('//*[@data-oe-model != "ir.ui.view"]')

    def save_embedded_field(self, cr, uid, el, context=None):
        Model = self.pool[el.get('data-oe-model')]
        field = el.get('data-oe-field')

        converter = self.pool['website.qweb'].get_converter_for(el.get('data-oe-type'))
        value = converter.from_html(cr, uid, Model, Model._fields[field], el)

        if value is not None:
            # TODO: batch writes?
            ids = [int(el.get('data-oe-id'))]
            Model.write(cr, uid, ids, {
                field: value
            }, context=context)
            self._translation_resync(cr, uid, el.get('data-oe-model'), ids, field, context=context)

    def to_field_ref(self, cr, uid, el, context=None):
        # filter out meta-information inserted in the document
        attributes = dict((k, v) for k, v in el.items()
                          if not k.startswith('data-oe-'))
        attributes['t-field'] = el.get('data-oe-expression')

        out = html.html_parser.makeelement(el.tag, attrib=attributes)
        out.tail = el.tail
        return out

    def replace_arch_section(self, cr, uid, view_id, section_xpath, replacement, context=None):
        # the root of the arch section shouldn't actually be replaced as it's
        # not really editable itself, only the content truly is editable.

        [view] = self.browse(cr, uid, [view_id], context=context)
        arch = etree.fromstring(view.arch.encode('utf-8'))
        # => get the replacement root
        if not section_xpath:
            root = arch
        else:
            # ensure there's only one match
            [root] = arch.xpath(section_xpath)

        root.text = replacement.text
        root.tail = replacement.tail
        # replace all children
        del root[:]
        for child in replacement:
            root.append(copy.deepcopy(child))

        return arch

    @tools.ormcache_context(accepted_keys=('website_id',))
    def get_view_id(self, cr, uid, xml_id, context=None):
        if context and 'website_id' in context and not isinstance(xml_id, (int, long)):
            domain = [('key', '=', xml_id), '|', ('website_id', '=', context['website_id']), ('website_id', '=', False)]
            [xml_id] = self.search(cr, uid, domain, order='website_id', limit=1, context=context)
        else:
            xml_id = super(view, self).get_view_id(cr, uid, xml_id, context=context)
        return xml_id

    def render(self, cr, uid, id_or_xml_id, values=None, engine='ir.qweb', context=None):
        if request and getattr(request, 'website_enabled', False):
            engine = 'website.qweb'

            if isinstance(id_or_xml_id, list):
                id_or_xml_id = id_or_xml_id[0]

            if not context:
                context = {}

            company = self.pool['res.company'].browse(cr, SUPERUSER_ID, request.website.company_id.id, context=context)

            qcontext = dict(
                context.copy(),
                website=request.website,
                url_for=website.url_for,
                slug=website.slug,
                res_company=company,
                user_id=self.pool.get("res.users").browse(cr, uid, uid),
                translatable=context.get('lang') != request.website.default_lang_code,
                editable=request.website.is_publisher(),
                menu_data=self.pool['ir.ui.menu'].load_menus_root(cr, uid, context=context) if request.website.is_user() else None,
            )

            # add some values
            if values:
                qcontext.update(values)

            # in edit mode ir.ui.view will tag nodes
            if qcontext.get('editable'):
                context = dict(context, inherit_branding=True)
            elif request.registry['res.users'].has_group(cr, uid, 'base.group_website_publisher'):
                context = dict(context, inherit_branding_auto=True)

            view_obj = request.website.get_template(id_or_xml_id)
            if 'main_object' not in qcontext:
                qcontext['main_object'] = view_obj

            values = qcontext

        return super(view, self).render(cr, uid, id_or_xml_id, values=values, engine=engine, context=context)

    def _pretty_arch(self, arch):
        # remove_blank_string does not seem to work on HTMLParser, and
        # pretty-printing with lxml more or less requires stripping
        # whitespace: http://lxml.de/FAQ.html#why-doesn-t-the-pretty-print-option-reformat-my-xml-output
        # so serialize to XML, parse as XML (remove whitespace) then serialize
        # as XML (pretty print)
        arch_no_whitespace = etree.fromstring(
            etree.tostring(arch, encoding='utf-8'),
            parser=etree.XMLParser(encoding='utf-8', remove_blank_text=True))
        return etree.tostring(
            arch_no_whitespace, encoding='unicode', pretty_print=True)

    def save(self, cr, uid, res_id, value, xpath=None, context=None):
        """ Update a view section. The view section may embed fields to write

        :param str model:
        :param int res_id:
        :param str xpath: valid xpath to the tag to replace
        """
        res_id = int(res_id)

        arch_section = html.fromstring(
            value, parser=html.HTMLParser(encoding='utf-8'))

        if xpath is None:
            # value is an embedded field on its own, not a view section
            self.save_embedded_field(cr, uid, arch_section, context=context)
            return

        for el in self.extract_embedded_fields(cr, uid, arch_section, context=context):
            self.save_embedded_field(cr, uid, el, context=context)

            # transform embedded field back to t-field
            el.getparent().replace(el, self.to_field_ref(cr, uid, el, context=context))

        arch = self.replace_arch_section(cr, uid, res_id, xpath, arch_section, context=context)
        self.write(cr, uid, res_id, {
            'arch': self._pretty_arch(arch)
        }, context=context)
        self._translation_resync(cr, uid, 'ir.ui.view', [res_id], 'arch', context=context)

        view = self.browse(cr, SUPERUSER_ID, res_id, context=context)
        if view.model_data_id:
            view.model_data_id.write({'noupdate': True})

    # When the English version of a field is modified, the algorithm tries to
    # resync translation if the distance between modified strings is not too
    # big. It allows to not retranslate data where a typo has been fixed in
    # the English version.
    def _translation_resync(self, cr, uid, model, ids, field, context=None):
        context = context or {}
        model_obj = self.pool.get(model)
        trans_obj = self.pool.get('ir.translation')
        translate = model_obj._all_columns[field].column.translate
        if not translate:
            return
        chunk = (lambda x: [x]) if (translate is True) else translate

        for record in model_obj.browse(cr, uid, ids, context=context):
            val = getattr(record, field)
            if not val: continue
            origins = list(chunk(val))

            trans_ids = trans_obj.search(cr, uid, [
                            ('name','=',model+','+field),('type','=','model'),
                            ('res_id', '=', record.id)], context=context)

            for term in trans_obj.browse(cr, uid, trans_ids, context=context):
                if term.src not in origins:
                    newsrc = difflib.get_close_matches(term.src, origins, 1, 0.9)
                    if newsrc:
                        trans_obj.write(cr, uid, term.id, {'src': newsrc[0]}, context=context)
                    elif translate is True:
                        trans_obj.write(cr, uid, term.id, {'state': 'to_translate', 'src': val}, context=context)
        return True
