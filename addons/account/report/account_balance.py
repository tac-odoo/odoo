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

from openerp import models,api
from common_report_header import common_report_header


class AccountBalanceReport(models.AbstractModel, common_report_header):
    _name = 'report.account.report_trialbalance'

    @api.one
    def _get_account(self, data):
        if data['model']=='account.account':
            return self.env['account.account'].browse(data['form']['id']).company_id.name
        return super(account_balance ,self)._get_account(data)

    @api.multi
    def lines(self, form, ids=None, done=None):
        def _process_child(accounts, disp_acc, parent):
                account_rec = [acct for acct in accounts if acct['id']==parent][0]
                currency_obj = self.env['res.currency']
                acc_id = self.env['account.account'].browse(account_rec['id'])
                currency = acc_id.currency_id and acc_id.currency_id or acc_id.company_id.currency_id
                res = {
                    'id': account_rec['id'],
                    'type': account_rec['type'],
                    'code': account_rec['code'],
                    'name': account_rec['name'],
                    'level': account_rec['level'],
                    'debit': account_rec['debit'],
                    'credit': account_rec['credit'],
                    'balance': account_rec['balance'],
                    'parent_id': account_rec['parent_id'],
                    'bal_type': '',
                }
                self.sum_debit += account_rec['debit']
                self.sum_credit += account_rec['credit']
                if disp_acc == 'movement':
                    if not currency_obj.is_zero(currency, res['credit']) or not currency_obj.is_zero(currency, res['debit']) or not currency_obj.is_zero(currency, res['balance']):
                        self.result_acc.append(res)
                elif disp_acc == 'not_zero':
                    if not currency_obj.is_zero(currency, res['balance']):
                        self.result_acc.append(res)
                else:
                    self.result_acc.append(res)
                if account_rec['child_id']:
                    for child in account_rec['child_id']:
                        _process_child(accounts,disp_acc,child)

        obj_account = self.env['account.account']
        if not ids:
            ids = self.ids
        if not ids:
            return []
        if not done:
            done={}

        ctx = self._context.copy()

        ctx['fiscalyear'] = form['fiscalyear_id']
        if form['filter'] == 'filter_period':
            ctx['period_from'] = form['period_from']
            ctx['period_to'] = form['period_to']
        elif form['filter'] == 'filter_date':
            ctx['date_from'] = form['date_from']
            ctx['date_to'] =  form['date_to']
        ctx['state'] = form['target_move']
        parents = ids
        child_ids = obj_account.with_context(ctx)._get_children_and_consol(self)
        if child_ids:
            ids = child_ids
        accounts = obj_account.with_context(ctx).read(ids, ['type','code','name','debit','credit','balance','parent_id','level','child_id'])

        for parent in parents:
                if parent in done:
                    continue
                done[parent] = 1
                _process_child(accounts,form['display_account'],parent)
        return self.result_acc


    @api.multi
    def render_html(self, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('account.report_trialbalance')
        
        
        docargs = {
            'doc_ids': self._ids,
            'doc_model': report.model,
            'docs': [],
            'time': time,
            'lines': self.lines,
            'sum_debit': self._sum_debit,
            'sum_credit': self._sum_credit,
            'get_fiscalyear':self._get_fiscalyear,
            'get_filter': self._get_filter,
            'get_account': self._get_account(data),
            'get_journal': self._get_journal,
            'get_start_date':self._get_start_date,
            'get_end_date':self._get_end_date,
            'get_target_move': self._get_target_move,
        }
        return report_obj.render('account.report_trialbalance', docargs)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
