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
from openerp.osv import osv
from openerp.tools.translate import _
from openerp.report import report_sxw
from common_report_header import common_report_header


class third_party_ledger(report_sxw.rml_parse, common_report_header):

    def __init__(self, cr, uid, name, context=None):
        super(third_party_ledger, self).__init__(cr, uid, name, context=context)
        self.init_bal_sum = 0.0
        self.localcontext.update({
            'time': time,
            'get_account': self._get_account,
            'get_filter': self._get_filter,
            'get_start_date': self._get_start_date,
            'get_end_date': self._get_end_date,
            'get_fiscalyear': self._get_fiscalyear,
            'get_journal': self._get_journal,
            'get_partners':self._get_partners,
            'get_target_move': self._get_target_move,
        })

    def _get_filter(self, data):
        if data['form']['filter'] == 'unreconciled':
            return _('Unreconciled Entries')
        return super(third_party_ledger, self)._get_filter(data)

    def set_context(self, objects, data, ids, report_type=None):
        obj_move = self.pool.get('account.move.line')
        obj_partner = self.pool.get('res.partner')
        self.query = obj_move._query_get(self.cr, self.uid, obj='l', context=data['form'].get('used_context', {}))
        ctx2 = data['form'].get('used_context',{}).copy()
        self.initial_balance = data['form'].get('initial_balance', True)
        if self.initial_balance:
            ctx2.update({'initial_bal': True})
        self.init_query = obj_move._query_get(self.cr, self.uid, obj='l', context=ctx2)
        self.reconcil = True
        if data['form']['filter'] == 'unreconciled':
            self.reconcil = False
        self.result_selection = data['form'].get('result_selection', 'customer')
        self.amount_currency = data['form'].get('amount_currency', False)
        self.target_move = data['form'].get('target_move', 'all')
        PARTNER_REQUEST = ''
        move_state = ['draft','posted']
        if self.target_move == 'posted':
            move_state = ['posted']
        if self.result_selection == 'supplier':
            self.ACCOUNT_TYPE = ['payable']
        elif self.result_selection == 'customer':
            self.ACCOUNT_TYPE = ['receivable']
        else:
            self.ACCOUNT_TYPE = ['payable','receivable']

        self.cr.execute(
            "SELECT a.id " \
            "FROM account_account a " \
            "LEFT JOIN account_account_type t " \
                "ON (a.user_type=t.id) " \
                'WHERE t.type IN %s' \
                "AND a.deprecated is False", (tuple(self.ACCOUNT_TYPE), ))
        self.account_ids = [a for (a,) in self.cr.fetchall()]
        params = [tuple(move_state), tuple(self.account_ids)]
        #if we print from the partners, add a clause on active_ids
        if (data['model'] == 'res.partner') and ids:
            PARTNER_REQUEST =  "AND l.partner_id IN %s"
            params += [tuple(ids)]
        self.cr.execute(
                "SELECT DISTINCT l.partner_id " \
                "FROM account_move_line AS l, account_account AS account, " \
                " account_move AS am " \
                "WHERE l.partner_id IS NOT NULL " \
                    "AND l.account_id = account.id " \
                    "AND am.id = l.move_id " \
                    "AND am.state IN %s"
                    "" + self.query +" " \
                    "AND l.account_id IN %s " \
                    " " + PARTNER_REQUEST + " " \
                    "AND account.deprecated is False ", params)
        self.partner_ids = [res['partner_id'] for res in self.cr.dictfetchall()]
        objects = obj_partner.browse(self.cr, self.uid, self.partner_ids)
        return super(third_party_ledger, self).set_context(objects, data, self.partner_ids, report_type)

    def _get_partners(self):
        # TODO: deprecated, to remove in trunk
        if self.result_selection == 'customer':
            return _('Receivable Accounts')
        elif self.result_selection == 'supplier':
            return _('Payable Accounts')
        elif self.result_selection == 'customer_supplier':
            return _('Receivable and Payable Accounts')
        return ''




class report_partnerledger(osv.AbstractModel):
    _name = 'report.account.report_partnerledger'
    _inherit = 'report.abstract_report'
    _template = 'account.report_partnerledger'
    _wrapped_report_class = third_party_ledger


class report_partnerledgerother(osv.AbstractModel):
    _name = 'report.account.report_partnerledgerother'
    _inherit = 'report.abstract_report'
    _template = 'account.report_partnerledgerother'
    _wrapped_report_class = third_party_ledger

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
