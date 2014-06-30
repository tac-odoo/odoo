# -*- coding: utf-8 -*-
from openerp.addons.web.http import request
from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools.translate import _

# defined for access rules
class sale_order(osv.Model):
    _inherit = "sale.order"

    def _cart_find_product_line(self, cr, uid, ids, product_id=None, line_id=None, context=None, **kwargs):
        line_ids = super(sale_order, self)._cart_find_product_line(cr, uid, ids, product_id, line_id, context=context)
        if line_id:
            return line_ids
        for so in self.browse(cr, uid, ids, context=context):
            domain = [('id', 'in', line_ids)]
            if context.get("event_ticket_id"):
                domain += [('event_ticket_id', '=', context.get("event_ticket_id"))]
            return self.pool.get('sale.order.line').search(cr, SUPERUSER_ID, domain, context=context)

    def _website_product_id_change(self, cr, uid, ids, order_id, product_id, line_id=None, context=None):
        values = super(sale_order,self)._website_product_id_change(cr, uid, ids, order_id, product_id, line_id=line_id, context=None)

        event_ticket_id = None
        if context.get("event_ticket_id"):
            event_ticket_id = context.get("event_ticket_id")
        elif line_id:
            line = self.pool.get('sale.order.line').browse(cr, SUPERUSER_ID, line_id, context=context)
            if line.event_ticket_id:
                event_ticket_id = line.event_ticket_id.id
        else:
            product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            if product.event_ticket_ids:
                event_ticket_id = product.event_ticket_ids[0].id

        if event_ticket_id:
            ticket = self.pool.get('event.event.ticket').browse(cr, uid, event_ticket_id, context=context)
            if product_id != ticket.product_id.id:
                raise osv.except_osv(_('Error!'),_("The ticket doesn't match with this product."))

            values['product_id'] = ticket.product_id.id
            values['event_id'] = ticket.event_id.id
            values['event_ticket_id'] = ticket.id
            values['price_unit'] = ticket.price
            values['name'] = "%s: %s" % (ticket.event_id.name, ticket.name)

        return values

class sale_order_line(osv.Model):
    _inherit = 'sale.order.line'

    def button_confirm(self, cr, uid, ids, context=None):
        '''
        Updated attendees details in attendee form and sales order lines.
        '''
        if context is None:
            context = {}
        result = super(sale_order_line, self).button_confirm(cr, uid, ids, context=context)
        attendee_obj = request.registry.get('event.registration')
        attendees_list = request.session.get('attendees_list', False)
        if attendees_list and attendees_list != []:
            sale_order_obj = request.registry.get('sale.order').browse(cr, uid, request.session.get('sale_order_id', False), context=context)
            attendee_ids = attendee_obj.search(cr, uid, [('origin', '=', sale_order_obj.name)])
            attendee_ids.reverse()
            for attendee, attendees_data in zip(attendee_obj.browse(cr, uid, attendee_ids, context=context), attendees_list):
                attendee_obj.write(cr, uid, [attendee.id], {
                    'name': attendees_data['name'],
                    'email': attendees_data['email'],
                    'phone': attendees_data['phone']
                }, context=context)

            ids.reverse()
            for attendee, saleorder_line in zip(attendee_obj.browse(cr, uid, attendee_ids, context= context), self.browse(cr, uid, ids, context=context)):
                name = saleorder_line.name + ' ( ' + attendee.name + ' )'
                self.write(cr, uid, saleorder_line.id, {'name': name}, context=context)
            request.session['attendees_list'] = []
        return result
