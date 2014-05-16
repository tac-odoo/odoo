from openerp.osv import osv, fields

class mail_bubble(osv.Model):
    _name = 'mail.bubble'
    #_inherit = ['mail.thread']
    _auto = False

    _columns = {
        'name': fields.text('Name'),
        'model': fields.char('Resource Model', size=128),
        'res_id': fields.integer("Resource ID"),
        'message_count': fields.integer("Message Count"),
        'partner_id': fields.integer("Partner ID"),
        'message_date': fields.date("Message Date"),
        'subject': fields.char("Subject"),
        'author_id': fields.integer("Author"),
        'msg_body': fields.text("Message Body")
    }

    def get_name(self, cr, uid, tech_name, context=None):
        mod_id = self.pool.get('ir.model').search(cr,uid,args=[('model', '=', tech_name)])
        mod_name=self.pool.get('ir.model').name_get(cr,uid,mod_id,context=context)  
        mod_name = mod_name[0][1] if mod_name else tech_name        
        return mod_name

    def bubble_read(self, cr, uid, ids=None, domain=None, context=None):
        result_ids = self.search(cr, uid, domain, context=context)
        result = self.read(cr, uid, result_ids, [], context=context)
        for res in result:
            model_name = self.get_name(cr, uid, res.get('model'), context=context)
            res.update({'model_name': model_name})
        print result
        
        return {v['res_id']:v for v in result}.values()        
        #return result
            
    def init(self, cr):
        cr.execute("""create or replace view mail_bubble as
            SELECT 
                id,
                name,
                model,
                res_id,
                message_count,
                partner_id,
                message_date,
                subject,
                author_id,
                msg_body
           FROM (
            SELECT mm.id AS id, mm.record_name AS name, mm.model AS model, mm.res_id AS res_id, count(*) as message_count, mn.partner_id AS partner_id, mm.date AS message_date, mm.subject AS subject, mm.author_id AS author_id, mm.body AS msg_body
            FROM mail_message mm, mail_notification mn
            WHERE mm.id = mn.message_id and mm.model != 'FALSE' and mn.read != 'TRUE' 
            GROUP BY mm.id,
                mm.record_name,
                mm.model,
                mm.res_id,
                mn.read,
                mn.partner_id,
                mm.date,
                mm.subject,
                mm.author_id,          
                mm.body
           ) AS foobar
        """)
