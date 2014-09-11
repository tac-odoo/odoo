from openerp.osv import orm
from openerp.addons.base.ir.ir_qweb import QWebContext


class QWeb(orm.AbstractModel):

    _inherit = "ir.qweb"

    def render(self, cr, uid, id_or_xml_id, qwebcontext=None, loader=None, context=None):
        if qwebcontext is None:
            qwebcontext = {}

        if not isinstance(qwebcontext, QWebContext):
            qwebcontext = QWebContext(cr, uid, qwebcontext, loader=loader, context=context)

        context = context or {}

        website_id = context.get('website_id')
        if website_id:
            id_or_xml_id = self.pool['ir.ui.view'].search(cr, uid, [
                ('key', '=', id_or_xml_id),
                '|',
                ('website_id', '=', website_id),
                ('website_id', '=', False)
            ], order="website_id", limit=1, context=context)[0]

        qwebcontext['__template__'] = id_or_xml_id
        stack = qwebcontext.get('__stack__', [])
        if stack:
            qwebcontext['__caller__'] = stack[-1]
        stack.append(id_or_xml_id)
        qwebcontext['__stack__'] = stack
        qwebcontext['xmlid'] = str(stack[0])    # Temporary fix
        return self.render_node(self.get_template(id_or_xml_id, qwebcontext), qwebcontext)
