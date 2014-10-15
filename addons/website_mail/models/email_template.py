# -*- coding: utf-8 -*-

from openerp.osv import osv, fields
from openerp.tools.translate import _


class EmailTemplate(osv.Model):
    _inherit = 'email.template'
    
    _columns = {
            'theme_xml_id': fields.char('Theme XML id') 
    }
    
    def action_edit_html(self, cr, uid, ids, context=None):
        if not len(ids) == 1:
            raise ValueError('One and only one ID allowed for this action')
        template = self.browse(cr, uid, ids,context=context)
        url = '/website_mail/email_designer?model=email.template&res_id=%d&enable_editor=1' % (ids[0],)
        if template.theme_xml_id:
            url+='&theme_id=%s'%(template.theme_xml_id)
        return {
            'name': _('Edit Template'),
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }
