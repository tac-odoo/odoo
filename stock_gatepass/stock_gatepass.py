# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

import time

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import workflow

class stock_picking(osv.Model):
    _inherit = 'stock.picking'

    _columns = {
        'gate_pass_id': fields.many2one('stock.gatepass', 'Gate Pass'),
    }

stock_picking()

#class stock_picking_in(osv.Model):
#    _inherit = "stock.picking.in"

#    _columns = {
#        'gate_pass_id': fields.many2one('stock.gatepass', 'Gate Pass'),
#    }

#stock_picking_in()

#class stock_picking_out(osv.Model):
#    _inherit = "stock.picking.out"

#    _columns = {
#        'gate_pass_id': fields.many2one('stock.gatepass', 'Gate Pass'),
#    }

#stock_picking_out()

class gate_pass_type(osv.Model):
    _name = 'gatepass.type'
    _description = 'Gate Pass Type'

    _columns = {
        'name': fields.char('Name', size=256, select=1),
        'code': fields.char('Code', size=16, select=1),
        'approval_required': fields.boolean('Approval State'),
        'return_type': fields.selection([('return', 'Returnable'), ('non_return', 'Non-returnable')], 'Return Type', required=True),
        'active': fields.boolean('Active'),
        'sales_delivery': fields.boolean('Sales Delivery')
    }

    _defaults = {
        'active': True,
        'return_type': 'return'
    }

gate_pass_type()

class stock_gatepass(osv.Model):
    _name = 'stock.gatepass'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = 'Gate Pass'
    _order = "name desc"

    _track = {
        'state': {
            'stock_gatepass.mt_gatepass_pending': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'pending',
            'stock_gatepass.mt_gatepass_done': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'done'
        },
    }

    def _get_total_amount(self, cr, uid, ids, name, args, context=None):
        result = {}
        for gatepass in self.browse(cr, uid, ids, context=context):
            total = 0.0
            for line in gatepass.line_ids:
                total += (line.product_qty * line.price_unit)
            result[gatepass.id] = total
        return result

    def onchange_type(self, cr, uid, ids, type_id=False):
        result = {}
        if type_id:
            type = self.pool.get('gatepass.type').browse(cr, uid, type_id)
            result['return_type'] = type.return_type
            result['approval_required'] = type.approval_required
            result['sales_delivery'] = type.sales_delivery
        return {'value': result}

    _columns = {
        'name': fields.char('Name', size=256, readonly=True, states={'draft': [('readonly', False)]}, track_visibility='always'),
        'driver_id': fields.many2one('res.partner', 'Driver', readonly=True, states={'draft': [('readonly', False)]}),
        'person_id': fields.many2one('res.partner', 'Delivery Person', readonly=True, states={'draft': [('readonly', False)]}),
        'user_id': fields.many2one('res.users', 'User', required=True, readonly=True),
        'date': fields.datetime('Create Date', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'approve_date': fields.datetime('Approve Date', readonly=True, states={'draft': [('readonly', False)]}),
        'type_id': fields.many2one('gatepass.type', 'Type', required=True, readonly=True, states={'draft': [('readonly', False)]}, track_visibility='onchange'),
        'partner_id':fields.many2one('res.partner', 'Supplier', required=True, readonly=True, states={'draft': [('readonly', False)]}, track_visibility='onchange'),
        'line_ids': fields.one2many('stock.gatepass.line', 'gatepass_id', 'Products', readonly=True, states={'draft': [('readonly', False)]}),
        'description': fields.text('Remarks', readonly=True, states={'draft': [('readonly', False)], 'pending': [('readonly', False)]}),
        'company_id': fields.many2one('res.company', 'Company', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'amount_total': fields.function(_get_total_amount, type="float", string='Total', store=True, readonly=True, track_visibility='onchange'),
        'location_id': fields.many2one('stock.location', 'Source Location', readonly=True, states={'draft': [('readonly', False)]}),
        'state':fields.selection([('draft', 'Draft'), ('pending', 'Pending'), ('done', 'Done')], 'State', readonly=True, track_visibility='onchange'),
        'return_type': fields.selection([('return', 'Returnable'), ('non_return', 'Non-returnable')], 'Return Type', readonly=True, states={'draft': [('readonly', False)]}, track_visibility='onchange'),
#        'out_picking_id': fields.many2one('stock.picking.out', 'Delivery Order', readonly=True, states={'draft': [('readonly', False)]}, domain=[('type','=','out')]),
#        'in_picking_id': fields.many2one('stock.picking.in', 'Incoming Shipment', readonly=True, states={'draft': [('readonly', False)]}),
        'in_picking_id': fields.many2one('stock.picking', 'Incoming Shipment', readonly=True, states={'draft': [('readonly', False)]}),
        'out_picking_id': fields.many2one('stock.picking', 'Delivery Order', readonly=True, states={'draft': [('readonly', False)]}),
        'approval_required': fields.boolean('Approval State', readonly=True, states={'draft': [('readonly', False)]}),
        'sales_delivery': fields.boolean('Sales Delivery'),
    }

    _defaults = {
        'state': 'draft',
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'gate.pass', context=c),
        'user_id': lambda self, cr, uid, context: uid,
    }

    def onchange_delivery_order(self, cr, uid, ids, order_id=False, *args, **kw):
        result = {'line_ids': []}
        lines = []

        if not order_id:
            return {'value': result}

        order = self.pool.get('stock.picking').browse(cr, uid, order_id)
        products = order.move_lines

        for product in products:
            vals = dict(
                product_id = product.product_id.id,
                product_qty = product.product_qty,
                uom_id= product.product_uom.id,
                name = product.product_id.name,
                location_id = product.location_id.id,
                location_dest_id = product.location_dest_id.id,
            )

            #TODO: need to check in other ways whether sale module is installed or not instead of try and except..
            try:
                if product.sale_line_id:
                    vals['price_unit'] = product.sale_line_id.price_unit
            except:
                vals['price_unit'] = product.product_id.list_price
            lines.append(vals)
        result['line_ids'] = lines
        result['partner_id'] = order.partner_id.id
        return {'value': result}

    def create_delivery_order(self, cr, uid, gatepass, context=None):
        picking_out_obj = self.pool.get('stock.picking')
        move_obj = self.pool.get('stock.move')
        todo_moves = []

        obj_data = self.pool.get('ir.model.data')
        out_type_id = obj_data.get_object_reference(cr, uid, 'stock','picking_type_out')[1]

        for line in gatepass.line_ids:
            result = dict(name=line.product_id.name,
                product_id=line.product_id.id,
                product_qty=line.product_qty,
                product_uom=line.uom_id.id,
                location_id=line.location_id.id,
                location_dest_id=line.location_dest_id.id,
                origin=gatepass.name,
                picking_type_id=out_type_id,
            )
            move_id = move_obj.create(cr, uid, result, context=context)
            todo_moves.append(move_id)

        move_obj.action_confirm(cr, uid, todo_moves)
        move_obj.force_assign(cr, uid, todo_moves)

        out_picking_id = False

        for move in move_obj.browse(cr, uid, todo_moves):
            out_picking_id = move.picking_id.id
        return out_picking_id

    def create_incoming_shipment(self, cr, uid, gatepass, context=None):
        move_obj = self.pool.get('stock.move')
        obj_data = self.pool.get('ir.model.data')
        todo_moves = []

        supplier_location = self.pool.get('ir.model.data').get_object(cr, uid, 'stock', 'stock_location_suppliers')

        in_type_id = obj_data.get_object_reference(cr, uid, 'stock','picking_type_in')[1]

        for line in gatepass.line_ids:
            if line.product_id.container_id:
                result = dict(name=line.product_id.container_id.name,
                    product_id=line.product_id.container_id.id,
                    product_qty=1,
                    product_uom=line.product_id.container_id.uom_id.id,
                    location_id=supplier_location.id,
                    location_dest_id=line.location_id.id,
                    picking_type_id=in_type_id,
                    origin=gatepass.name
                )
            elif gatepass.type_id.approval_required == True:
                result = dict(name=line.product_id.name,
                    product_id=line.product_id.id,
                    product_qty=line.product_qty,
                    product_uom=line.uom_id.id,
                    location_id=supplier_location.id,
                    location_dest_id=line.location_id.id,
                    picking_type_id=in_type_id,
                    origin=gatepass.name
                )
            move_id = move_obj.create(cr, uid, result, context=context)
            todo_moves.append(move_id)

        move_obj.action_confirm(cr, uid, todo_moves)
        move_obj.force_assign(cr, uid, todo_moves)

        in_picking_id = False

        for move in move_obj.browse(cr, uid, todo_moves):
            in_picking_id = move.picking_id.id
        return in_picking_id

    def open_delivery_order(self, cr, uid, ids, context=None):
        out_picking_id = self.browse(cr, uid, ids[0], context=context).out_picking_id.id
        res = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'stock', 'view_picking_form')
        result = {
            'name': _('Delivery Order'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': res and res[1] or False,
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': out_picking_id,
        }
        return result

    def open_incoming_shipment(self, cr, uid, ids, context=None):
        in_picking_id = self.browse(cr, uid, ids[0], context=context).in_picking_id.id
        res = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'stock', 'view_picking_form')
        result = {
            'name': _('Incoming Shipment'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': res and res[1] or False,
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': in_picking_id,
        }
        return result

    def move_lines_get(self, cr, uid, ids, *args):
        res = []
        for gate in self.browse(cr, uid, ids, context={}):
            res += [x.id for x in gate.in_picking_id.move_lines]
        return res

    def test_moves_done(self, cr, uid, ids, context=None):
        for gate in self.browse(cr, uid, ids, context=context):
            if gate.in_picking_id.state != 'done':
                return False
        return True

    def check_returnable(self, cr, uid, ids, context=None):
        for gp in self.browse(cr, uid, ids, context=context):
            if gp.type_id.return_type == 'return':
                return True
        return False

    def action_confirm(self, cr, uid, ids, context=None):
        seq_obj = self.pool.get('ir.sequence')
        picking_pool = self.pool.get('stock.picking')

        for gatepass in self.browse(cr, uid, ids, context=context):
            if not gatepass.line_ids:
                raise osv.except_osv(_('Warning!'),_('You cannot confirm a gate pass which has no line.'))
            out_picking_id = gatepass.out_picking_id.id or False
            in_picking_id = False

            if not out_picking_id:
                out_picking_id = self.create_delivery_order(cr, uid, gatepass, context=context)

            if gatepass.type_id and gatepass.type_id.return_type == 'return':
                in_picking_id = self.create_incoming_shipment(cr, uid, gatepass, context=context)

            name = seq_obj.get(cr, uid, 'stock.gatepass')
            res = {
                'name': name,
                'approve_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'out_picking_id': out_picking_id,
                'in_picking_id': in_picking_id,
            }
            # Added the delivery person as follower
            if gatepass.person_id:
                res = dict(res, message_follower_ids = [(4, gatepass.person_id and gatepass.person_id.id)])
            self.write(cr, uid, [gatepass.id], res, context=context)
        return True

    def action_picking_create(self, cr, uid, ids, context=None):
        self.action_confirm(cr, uid, ids, context=context)
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        picking = self.browse(cr, uid, ids[0], context=context).in_picking_id.id
        self.pool.get('stock.picking').write(cr, uid, [picking], {'gate_pass_id': ids[0]}, context=context)
        self.write(cr, uid, ids, {'state': 'pending'}, context=context)
        return True

    def action_done(self, cr, uid, ids, context=None):
        for gatepass in self.browse(cr, uid, ids, context=context):
            if gatepass.return_type == 'non_return':
                self.action_confirm(cr, uid, [gatepass.id], context=context)
            self.write(cr, uid, [gatepass.id], {'state': 'done'}, context=context)
        return True

stock_gatepass()

class stock_gatepass_line(osv.Model):
    _name = 'stock.gatepass.line'
    _description = 'Gate Pass Lines'

    def _get_subtotal_amount(self, cr, uid, ids, name, args, context=None):
        result = {}
        for gp in self.browse(cr, uid, ids, context=context):
            result[gp.id] = (gp.product_qty * gp.price_unit)
        return result

    _columns = {
        'name': fields.text('Name', required=True),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'uom_id': fields.many2one('product.uom', 'Unit of Measure', required=True),
        'gatepass_id': fields.many2one('stock.gatepass', 'Gate Pass', required=True, ondelete='cascade'),
        'product_qty': fields.float('Quantity', required=True),
        'location_id': fields.many2one('stock.location', 'Source Location', required=True),
        'location_dest_id': fields.many2one('stock.location', 'Destination Location', required=True),
        'price_unit': fields.float('Approx. Value'),
        'prodlot_id': fields.many2one('stock.production.lot', 'Serial #'),
     }

    def _get_uom_id(self, cr, uid, *args):
        result = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'product', 'product_uom_unit')
        return result and result[1] or False

    def _default_stock_location(self, cr, uid, context=None):
        stock_location = self.pool.get('ir.model.data').get_object(cr, uid, 'stock', 'stock_location_stock')
        return stock_location.id

    def _default_dest_location(self, cr, uid, context=None):
        stock_location = self.pool.get('ir.model.data').get_object(cr, uid, 'stock', 'stock_location_customers')
        return stock_location.id

    _defaults = {
        'product_qty': 1,
        'uom_id': _get_uom_id,
        'location_id': _default_stock_location,
        'location_dest_id': _default_dest_location,
    }

    def onchange_product_id(self, cr, uid, ids, product_id=False):
        result = {}
        if product_id:
            product = self.pool.get('product.product').browse(cr, uid, product_id)
            result = dict(value=dict(name=product.name, uom_id=product.uom_id and product.uom_id.id or False, price_unit=product.list_price))
        return result

stock_gatepass_line()


class stock_move(osv.osv):
    _inherit = 'stock.move'

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = super(stock_move, self).write(cr, uid, ids, vals, context=context)
        from openerp import workflow
        if 'state' in vals:
            for move in self.browse(cr, uid, ids, context=context):
                if move.picking_id and move.picking_id.gate_pass_id:
                    gate_pass_id = move.picking_id.gate_pass_id.id
                    if self.pool.get('stock.gatepass').test_moves_done(cr, uid, [gate_pass_id], context=context):
                        workflow.trg_validate(uid, 'stock.gatepass', gate_pass_id, 'gate_pass_done', cr)
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
