from openerp.tools import xml_import


class xml_import(xml_import):

    def _tag_template(self, cr, el, data_node=None, mode=None):
        rec_model, id = super(xml_import, self)._tag_template(cr, el, data_node=None, mode=None)

        if 'website_id' in el.attrib:
            xml_id = el.get('website_id')
            self.pool[rec_model].write(cr, self.uid, id, {
                'website_id': self.pool['ir.model.data'].xml_id_to_res_id(cr, self.uid, xml_id)
            })

        return rec_model, id
