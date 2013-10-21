# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-TODAY OpenERP SA (<http://www.openerp.com>).
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

from openerp.osv import fields, osv, expression


class res_partner(osv.osv):
    _inherit = 'res.partner'

    _contact_type = [
        ('standalone', 'Standalone Contact'),
        ('attached', 'Attached to existing Contact'),
    ]

    def _get_contact_type(self, cr, uid, ids, field_name, args, context=None):
        result = dict.fromkeys(ids, 'standalone')
        for partner in self.browse(cr, uid, ids, context=context):
            if partner.contact_id:
                result[partner.id] = 'attached'
        return result

    _columns = {
        'contact_type': fields.function(_get_contact_type, type='selection', selection=_contact_type,
                                        string='Contact Type', required=True, select=1, store=True),
        'contact_id': fields.many2one('res.partner', 'Main Contact',
                                      domain=[('is_company','=',False),('contact_type','=','standalone')]),
        'other_contact_ids': fields.one2many('res.partner', 'contact_id', 'Others Positions'),

        # Person specific fields
        'birthdate_date': fields.date('Birthdate'),  # add a 'birthdate' as date field, i.e different from char 'birthdate' introduced v6.1!
        'nationality_id': fields.many2one('res.country', 'Nationality'),
    }

    _defaults = {
        'contact_type': 'standalone',
    }

    def _basecontact_check_context(self, cr, user, mode, context=None):
        if context is None:
            context = {}
        # Remove 'search_show_all_positions' for non-search mode.
        # Keeping it in context can result in unexpected behaviour (ex: reading
        # one2many might return wrong result - i.e with "attached contact" removed
        # even if it's directly linked to a company).
        if mode != 'search':
            context.pop('search_show_all_positions', None)
        return context

    def search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        if context.get('search_show_all_positions') is False:
            # display only standalone contact matching ``args`` or having
            # attached contact matching ``args``
            args = expression.normalize_domain(args)
            attached_contact_args = expression.AND((args, [('contact_type', '=', 'attached')]))
            attached_contact_ids = super(res_partner, self).search(cr, user, attached_contact_args,
                                                                   context=context)
            args = expression.OR((
                expression.AND(([('contact_type', '=', 'standalone')], args)),
                [('other_contact_ids', 'in', attached_contact_ids)],
            ))
        return super(res_partner, self).search(cr, user, args, offset=offset, limit=limit,
                                               order=order, context=context, count=count)

    def create(self, cr, user, vals, context=None):
        context = self._basecontact_check_context(cr, user, 'create', context)
        if not vals.get('name') and vals.get('contact_id'):
            vals['name'] = self.browse(cr, user, vals['contact_id'], context=context).name
        return super(res_partner, self).create(cr, user, vals, context=context)

    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        context = self._basecontact_check_context(cr, user, 'read', context)
        return super(res_partner, self).read(cr, user, ids, fields=fields, context=context, load=load)

    def write(self, cr, user, ids, vals, context=None):
        context = self._basecontact_check_context(cr, user, 'write', context)
        return super(res_partner, self).write(cr, user, ids, vals, context=context)

    def unlink(self, cr, user, ids, context=None):
        context = self._basecontact_check_context(cr, user, 'unlink', context)
        return super(res_partner, self).unlink(cr, user, ids, context=context)

    def _commercial_partner_compute(self, cr, uid, ids, name, args, context=None):
        """ Returns the partner that is considered the commercial
        entity of this partner. The commercial entity holds the master data
        for all commercial fields (see :py:meth:`~_commercial_fields`) """
        result = super(res_partner, self)._commercial_partner_compute(cr, uid, ids, name, args, context=context)
        for partner in self.browse(cr, uid, ids, context=context):
            if partner.contact_type == 'attached' and not partner.parent_id:
                result[partner.id] = partner.contact_id.id
        return result

    def onchange_contact_id(self, cr, uid, ids, contact_id, context=None):
        if contact_id:
            name = self.browse(cr, uid, contact_id, context=context).name
            return {'value': {'name': name}}
        return {}


class ir_actions_window(osv.osv):
    _inherit = 'ir.actions.act_window'

    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        action_ids = ids
        if isinstance(ids, (int, long)):
            action_ids = [ids]
        actions = super(ir_actions_window, self).read(cr, user, action_ids, fields=fields, context=context, load=load)
        for action in actions:
            if action.get('res_model', '') == 'res.partner':
                # By default, only show standalone contact
                action_context = action.get('context', '{}') or '{}'
                if 'search_show_all_positions' not in action_context:
                    action['context'] = action_context.replace('{',
                            "{'search_show_all_positions': False,", 1)
        if isinstance(ids, (int, long)):
            if actions:
                return actions[0]
            return False
        return actions
