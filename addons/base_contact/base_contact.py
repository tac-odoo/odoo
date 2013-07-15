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

import inspect
from openerp import tools
from openerp.osv import fields, osv, orm

class function_stored_location(fields.function):
    """This field allow to store computed address in language-agnostic format
       and to recompute language-specific address value uppon read
    """

    def __init__(self, fnct, arg=None, fnct_inv=None, fnct_inv_arg=None, type='float', fnct_search=None, obj=None, store=False, multi=False, **args):
        rval = super(function_stored_location, self).__init__(fnct, arg=arg, fnct_inv=fnct_inv, fnct_inv_arg=fnct_inv_arg,
                                                                type=type, fnct_search=fnct_search, obj=obj, store=store,
                                                                multi=multi, **args)
        if store and type != 'many2one':
            # force classic read to false as we want to compute values based on user language
            self._classic_read = False
        return rval

    def get(self, cr, obj, ids, name, uid=False, context=None, values=None):
        f = inspect.currentframe()
        called_from = ''
        if f:
            fback = f.f_back
            if fback:
                called_from = fback.f_code.co_name
        if called_from == '_store_set_values':
            # we force lang to en_US, as we want stored value be language
            # agnostic, otherwise group_by might return different values
            # depending on the translated coutry name, ...
            if context is None:
                context = {}
            context = dict(context, lang='en_US')
        return super(function_stored_location, self).get(cr, obj, ids, name, uid=uid, context=context, values=values)


# XXX: this is required for the following case:
# - menu "Sale Order" have action with context {'show_address': 1}
# - create a new "Sale Order", affect a customer (linked to another context)
# - open the customer form
#   => when reading the "contact_id" field on partner - the name_get() is called
#      with the current context which is {'show_address': 1} - the contact is display
#      with it's address, which is not what we want here.
class many2one_use_context(fields.many2one):
    """many2one variant that use context set on fields init"""
    def get(self, cr, obj, ids, name, user=None, context=None, values=None):
        if self._context and isinstance(self._context, dict):
            context = context.copy()
            context.update(self._context)
        return super(many2one_use_context, self).get(cr, obj, ids, name, user=user, context=context, values=values)


class res_partner(osv.osv):
    _inherit = 'res.partner'

    def _basecontact_location_display(self, cr, uid, ids, name, args, context=None):
        """compute partner location (address wo/ company)"""
        res = {}
        for partner in self.browse(cr, uid, ids, context=context):
            res[partner.id] = self._display_address(cr, uid, partner, without_company=True, context=context)
        return res

    def _commercial_partner_compute(self, cr, uid, ids, name, args, context=None):
        """ Returns the partner that is considered the commercial
        entity of this partner. The commercial entity holds the master data
        for all commercial fields (see :py:meth:`~_commercial_fields`) """
        result = super(res_partner, self)._commercial_partner_compute(cr, uid, ids, name, args, context=context)
        for partner in self.browse(cr, uid, ids, context=context):
            if partner.contact_type == 'attached' and not partner.parent_id:
                result[partner.id] = partner.contact_id.id
        return result

    #
    # "Contact Type" management
    #
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

    def onchange_contact_id(self, cr, uid, ids, contact_id, context=None):
        if contact_id:
            name = self.browse(cr, uid, contact_id, context=context).name
            return {'value': {'name': name}}
        return {}

    _columns = {
        'contact_type': fields.function(_get_contact_type, type='selection', selection=_contact_type,
                                        string='Contact Type', required=True, select=1, store=True),
        'contact_id': many2one_use_context('res.partner', 'Main Contact', domain=[('is_company','=',False),('contact_type','=','standalone')],
                                        context={'show_address': False}),
        'other_contact_ids': fields.one2many('res.partner', 'contact_id', 'Others Positions'),
        # Special computed address to allow grouping on address
        # TODO: update stored value when changing country address definition
        'contact_location': function_stored_location(_basecontact_location_display,  type='char', string='Location',
                                        store=True),

        # Person specific fields
        'birthdate': fields.date('Birthdate'),  # TODO: why is birthdate become a 'char' field in v6.1?
        'nationality_id': fields.many2one('res.country', 'Nationality'),
    }

    _defaults = {
        'contact_type': 'standalone',
    }

    def _basecontact_check_context(self, cr, user, mode, context=None):
        if context is None:
            context = {}
        # Remove 'search_show_all_positions' for non-search mode.
        # Keeping in context can give bad side-effects (ex: reading one2many
        # might retrun wrong result - i.e with "attached contact" removed
        # even if it's directly linked to a company).
        if mode != 'search':
            context.pop('search_show_all_positions', None)
        return context

    def search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        show_all_positions = context.get('search_show_all_positions')
        if show_all_positions is False:
            other_positions_args = [('contact_type', '=', 'standalone')]
            if args:
                other_positions_args.insert(0, '&')
            args[:0] = other_positions_args
        return super(res_partner, self).search(cr, user, args, offset=offset, limit=limit,
                                               order=order, context=context, count=count)

    def create(self, cr, user, vals, context=None):
        context = self._basecontact_check_context(cr, user, 'create', context)
        if not vals.get('name') and vals.get('contact_id'):
            vals['name'] = self.browse(cr, user, vals['contact_id'], context=context)
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


class ir_actions_window(osv.osv):
    _inherit = 'ir.actions.act_window'

    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        action_ids = ids
        if isinstance(ids, (int, long)):
            action_ids = [ids]
        actions = super(ir_actions_window, self).read(cr, user, action_ids, fields=fields, context=context, load=load)
        for action in actions:
            if action.get('res_model', '') == 'res.partner':
                action_context = action.get('context', '{}') or '{}'
                if 'search_show_all_positions' not in action_context:
                    action['context'] = action_context.replace('{',
                            "{'search_show_all_positions': False,", 1)
        if isinstance(ids, (int, long)):
            if actions:
                return actions[0]
            return False
        return actions
