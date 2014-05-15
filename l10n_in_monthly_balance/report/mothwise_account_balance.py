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

from openerp.report import report_sxw
from openerp.addons.account.report.common_report_header import common_report_header

class mothwise_account_balance(report_sxw.rml_parse, common_report_header):
    _name = 'report.mothwise.account.balance'

    def __init__(self, cr, uid, name, context=None):
        super(mothwise_account_balance, self).__init__(cr, uid, name, context=context)
        self.caddress = ''
        self.data = ''
        self.t_credit = 0.0
        self.t_balance = 0.0
        self.localcontext.update({
            'time': time,
            'lines': self.lines,
            'get_fiscalyear':self._get_fiscalyear,
            'get_filter': self._get_filter,
            'get_start_period': self.get_start_period,
            'get_end_period': self.get_end_period ,
            'get_account': self._get_account,
            'get_journal': self._get_journal,
            'get_start_date':self._get_start_date,
            'get_end_date':self._get_end_date,
            'get_target_move': self._get_target_move,
            'get_account_name':self._get_account_name,
            'cname':self._cname,
            'caddress':self._caddress,
            'total_d':self._total_d,
            'total_c':self._total_c,
            'total_b': self._total_b
        })
        self.context = context


    def _total_d(self):
        """
        Process
            -Calculate debit, credit and balance
         """
        debit = 0.0
        for l in self.data:
            debit += l['debit']
            self.t_credit += l['credit']
            self.t_balance += l['balance']
        return debit

    def _total_c(self):
        return self.t_credit

    def _total_b(self):
        return self.t_balance

    def _caddress(self):
        return self.caddress

    def _cname(self,account_id):
        """
        Process
            -get company name and detail values from account
        Return
            -Company Name,Address of Company
        """
        company = self.pool.get('account.account').browse(self.cr, self.uid, account_id).company_id
        self.caddress = self._cadd(company)
        return company.name 

    def _cadd(self,address):
        # get the information that will be injected into the display format
        # get the address format
        address_format = "%(street)s\n%(street2)s\n%(city)s %(state_code)s %(zip)s\n%(country_name)s"
        args = {
            'state_code': address.state_id and address.state_id.code or '',
            'state_name': address.state_id and address.state_id.name or '',
            'country_code': address.country_id and address.country_id.code or '',
            'country_name': address.country_id and address.country_id.name or '',
            'company_name': address.parent_id and address.parent_id.name or '',
        }
        for field in ('street', 'street2', 'zip', 'city', 'state_id', 'country_id'):
            args[field] = getattr(address, field) or ''
        address_format = '%(company_name)s\n' + address_format
        return address_format % args

    def _get_account_name(self, data):
        cr, uid = self.cr, self.uid
        acc = self.pool.get('account.account').browse(cr, uid, data['form']['account_id'][0])
        return acc.name or ''

    def set_context(self, objects, data, ids, report_type=None):
        new_ids = ids
        if (data['model'] == 'ir.ui.menu'):
            new_ids = 'chart_account_id' in data['form'] and [data['form']['chart_account_id']] or []
            objects = self.pool.get('account.account').browse(self.cr, self.uid, new_ids)
        return super(mothwise_account_balance, self).set_context(objects, data, new_ids, report_type=report_type)

    def _get_account(self, data):
        if data['model']=='account.account':
            return self.pool.get('account.account').browse(self.cr, self.uid, data['form']['id']).company_id.name
        return super(mothwise_account_balance ,self)._get_account(data)

    def lines(self, form, ids=None, done=None):
        """
        Process
            -Monthly period wise report
                -Find all child accounts of parent(Total Accounts = Own + Its child accounts)
                -Get context value to pass on _query_get method
                -Query to get values of account move line period wise
        Return
            -list of dictionary
        """
        moveline_obj = self.pool.get('account.move.line')
        cr,uid = self.cr,self.uid
        ctx = self.context.copy()
        ctx['fiscalyear'] = form['fiscalyear_id']
        if form['filter'] == 'filter_period':
            ctx['period_from'] = form['period_from']
            ctx['period_to'] = form['period_to']
        elif form['filter'] == 'filter_date':
            ctx['date_from'] = form['date_from']
            ctx['date_to'] =  form['date_to']
        ctx['state'] = form['target_move']

        account_ids = self.pool.get('account.account')._get_children_and_consol(cr, uid, [form['account_id'][0]], context=ctx)
        if not account_ids: return []
        move_query = moveline_obj._query_get(cr, uid, obj='l', context=ctx)

        cr.execute("""
                select
                    min(l.id) as id,
                    to_char(date,'MONTH') as name,
                    sum(l.debit-l.credit) as balance,
                    sum(l.debit) as debit,
                    sum(l.credit) as credit 
                from
                    account_move_line l
                left join
                    account_account a on (l.account_id=a.id)
                where 
                l.account_id in %s  
                AND """+move_query+"""
                group by
                    to_char(date,'MONTH'),to_char(date,'MM') 
                ORDER BY to_char(date,'MM')
                    """, (tuple(account_ids),))

        self.data = cr.dictfetchall()
        return self.data

report_sxw.report_sxw('report.mothwise.account.balance', 'account.account', 'addons/l10n_in_monthly_balance/report/mothwise_account_balance.rml', parser=mothwise_account_balance, header=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
