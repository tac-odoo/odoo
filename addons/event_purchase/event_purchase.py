# -*- coding: utf-8 ⁻*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2013-TODAY OpenERP S.A. (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from collections import defaultdict
from openerp.osv import osv, fields, expression
from openerp.osv.expression import normalize_domain
from openerp.tools.translate import _


class EventParticipation(osv.Model):
    _inherit = 'event.participation'

    STATES = [
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('done', 'Done'),
        ('error', 'Error'),  # TODO: implement specific error cases
        ('cancel', 'Cancelled'),
    ]

    PO_STATE_2_PART_STATE = {
        'draft': 'draft',
        'sent': 'draft',
        'confirmed': 'confirm',
        'approved': 'confirm',
        'except_picking': 'error',
        'except_invoice': 'error',
        'done': 'done',
        'cancel': 'cancel',
    }

    def _store_get_participations_self(self, cr, uid, ids, context=None):
        return ids

    def _store_get_participations_from_purchase_order(self, cr, uid, ids, context=None):
        if not ids:
            return []
        Participation = self.pool.get('event.participation')
        return Participation.search(cr, uid, [('purchase_order_line_id.order_id', 'in', ids)], context=context)

    def _get_state(self, cr, uid, ids, fieldname, args, context=None):
        if not ids:
            return {}
        cr.execute("SELECT id, state FROM event_participation WHERE id IN %s", (tuple(ids),))
        # by default used stored value
        result = dict(cr.fetchall())

        # for participation linked to a purchase order, get the real state
        # from the related purchase order.
        actions = defaultdict(list)
        part_filter = [
            ('id', 'in', ids),
            ('purchase_order_line_id', '!=', False)
        ]
        part_ids = self.search(cr, uid, part_filter, context=context)
        for p in self.browse(cr, uid, part_ids, context=context):
            order = p.purchase_order_id
            cached_state = result[p.id]
            part_state = self.PO_STATE_2_PART_STATE[order.state]
            result[p.id] = part_state
            if cached_state != part_state:
                actions[part_state].append(p.id)

        # trigger states changes for all item in batch mode
        if actions:
            for new_state, part_ids in actions.iteritems():
                button_action = getattr(self, 'button_set_' + new_state, None)
                if button_action:
                    button_action(cr, uid, part_ids, context=context)
        return result

    def _set_state(self, cr, uid, id, fieldname, value, args, context=None):
        cr.execute("UPDATE event_participation SET state = %s WHERE id = %s",
                   (value, id,))
        return True

    _columns = {
        'purchase_order_line_id': fields.many2one('purchase.order.line', 'Purchase Line'),
        'purchase_order_id': fields.related('purchase_order_line_id', 'order_id',
                                            string='Purchase Order', type='many2one',
                                            relation='purchase.order', readonly=True,),
        'state': fields.function(_get_state, type='selection', selection=STATES,
                                 string='State', fnct_inv=_set_state,
                                 store={
                                     'event.participation': (_store_get_participations_self, ['purchase_order_line_id'], 10),
                                     'purchase.order': (_store_get_participations_from_purchase_order, ['state'], 10),
                                 })
    }


class EventSeance(osv.Model):
    _inherit = 'event.seance'

    def _dummy_resource_id(self, cr, uid, ids, fieldname, args, context=None):
        return dict.fromkeys(ids, False)

    def _search_resource_id(self, cr, uid, ids, fieldname, args, context=None):
        for a in args:
            if isinstance(a, (list, tuple)) and len(a) == 3 and a[0] == fieldname:
                value = a[2]
                break
        else:
            return []
        seance_filter = [
            '|',
                ('address_id', '=', value),
                ('main_speaker_id', '=', value),
        ]
        result = [('id', 'in', self.search(cr, uid, seance_filter, context=context))]
        return result

    _columns = {
        'resource_id': fields.function(_dummy_resource_id, type='many2one',
                                       string='Resource', relation='res.partner',
                                       fnct_search=_search_resource_id),
    }

    def _search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False, access_rights_uid=None):
        if context is None:
            context = {}
        partner_id = context.get('search_purchase_import_seance_partner_id')
        if partner_id:
            args = normalize_domain(args)
            partner = self.pool.get('res.partner').browse(cr, user, partner_id, context=context)
            partner_args = []

            if partner.speaker:
                # Ensure used can only import seance which speaker is registered to
                Course = self.pool.get('event.course')
                allowed_course_ids = Course.search(cr, user, [('speaker_id', '=', partner_id)], context=context)
                allowed_course_ids += [False]  # for allowing seance without any course
                partner_args = [('course_id', 'in', allowed_course_ids)]

            Participation = self.pool.get('event.participation')
            past_part_ids = Participation.search(cr, user,
                                                 [('partner_id', '=', partner_id),
                                                  ('purchase_order_line_id', '!=', False)],
                                                 context=context)
            past_seances = set(p.seance_id.id for p in Participation.browse(cr, user, past_part_ids, context=context))
            past_seances_filter = [('id', 'not in', list(past_seances))]

            args = expression.AND((partner_args, past_seances_filter, args))

        _super = super(EventSeance, self)
        return _super._search(cr, user, args, offset=offset, limit=limit, order=order,
                              context=context, count=count, access_rights_uid=access_rights_uid)


class PurchaseOrderImportLineFromSeance(osv.TransientModel):
    _name = 'purchase.order.import.line.from.seance'
    _columns = {
        'order_id': fields.many2one('purchase.order', 'Order', required=True),
        'partner_id': fields.many2one('res.partner', 'Partner', required=True),
        'seance_ids': fields.many2many('event.seance', 'purchase_order_import_line_from_seance_rel',
                                       id1='import_wizard_id', id2='seance_id',
                                       string='Seances'),
    }

    def default_get(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        partner_id = context.get('default_partner_id')
        if partner_id:
            Partner = self.pool.get('res.partner')
            partner = Partner.browse(cr, uid, partner_id, context=context)
            if not any(partner[f] for f in ['speaker', 'room', 'equipment']):
                raise osv.except_osv(
                    _('Error!'),
                    _('Partner should be at last one of: speaker, room, equipment'))
        return super(PurchaseOrderImportLineFromSeance, self).default_get(cr, uid, fields_list, context=context)

    def _prepare_purchase_order_line_from_seance(self, cr, uid, partner, order, seance, context=None):
        OrderLine = self.pool.get('purchase.order.line')
        partner_roles = [r for r in ['speaker', 'room', 'equipment'] if partner[r]]
        if not partner_roles:
            raise osv.except_osv(
                _('Error!'),
                _('Partner should be at last one of: speaker, room, equipment'))
        role = partner_roles[0]
        role_check_field = {
            'room': 'room_ok',
            'speaker': 'speakers_ok',
            'equipment': 'equipments_ok'
        }[role]

        p = None
        for part in seance.resource_participation_ids:
            if part.partner_id.id == partner.id and part.role == role:
                p = part
                break
        else:
            # resource participation currently does not exist
            if seance[role_check_field]:
                raise osv.except_osv(
                    _('Error!'),
                    _("There is already enough %s on this seance '%s'" % (role, seance.name,)))
            if role == 'room':
                seance.write({'address_id': partner.id})
            elif role == 'speaker':
                # TODO: handle multiple speakers
                seance.write({'main_speaker_id': partner.id})
            elif role == 'equipment':
                pass  # TODO handle for equipment

            Seance = self.pool.get('event.seance')
            for part in Seance.browse(cr, uid, seance.id, context=context).resource_participation_ids:
                if part.partner_id.id == partner.id and part.role == role:
                    p = part
                    break

        if not p:
            raise osv.except_osv(
                _('Error!'),
                _("No resource participation found for partner '%s' (id: %d)") % (partner.name, partner.id))

        if p.purchase_order_line_id and p.purchase_order_line_id.order_id.state != 'cancel':
            raise osv.except_osv(
                _('Error!'),
                _('You can not add participation already assign to a purchase order'))
        if not p.purchase_product_id:
            raise osv.except_osv(
                _('Error!'),
                _('You can only add participations having a product'))
        values = {
            'product_id': p.purchase_product_id.id,
            'product_qty': p.purchase_qty,
        }
        changes = OrderLine.onchange_product_id(cr, uid, [],
                                                order.pricelist_id.id,
                                                p.purchase_product_id.id,
                                                p.purchase_qty,
                                                p.purchase_product_id.uom_po_id.id,
                                                partner.id,
                                                fiscal_position_id=order.fiscal_position.id,
                                                date_planned=p.seance_id.date_begin,
                                                price_unit=p.purchase_price,
                                                context=context)
        values.update(changes.get('value') or {},
                      price_unit=p.purchase_price)
        if values.get('taxes_id'):
            values['taxes_id'] = [(6, 0, values['taxes_id'])]
        return (p.id, values)

    def button_import_lines(self, cr, uid, ids, context=None):
        OrderLine = self.pool.get('purchase.order.line')
        Participation = self.pool.get('event.participation')
        prepare_order_line = self._prepare_purchase_order_line_from_seance

        for wizard in self.browse(cr, uid, ids, context=context):
            order = wizard.order_id
            partner = wizard.partner_id
            for seance in wizard.seance_ids:
                (participation_id, values) = prepare_order_line(cr, uid, partner, order, seance, context=context)
                new_order_line_id = OrderLine.create(cr, uid, values, context=context)
                Participation.write(cr, uid, [participation_id],
                                    {'purchase_order_line_id': new_order_line_id},
                                    context=context)
        return True
