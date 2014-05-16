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

class account_l10n_in_mrp_subcontract(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(account_l10n_in_mrp_subcontract, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.x = 0.0
        self.localcontext.update({
            'time': time,
            'add':self._add,
            'get_lines':self._get_lines,
            'amount_to_text': self._amount_to_text,
            'get_quantity': self._get_quantity,
            'get_excise': self._get_excise_cess,
            'convert_int': self._convert_int,
            'get_lines':self._get_lines,
            'payable_amounts':self._payable_amounts
        })

    def _add(self,address):
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

    def _get_lines(self, lines,symbol):
        t_lines = []
        total = len(lines)
        if total <= 0: return []
        add_l = 15 - total % 15

        #Exactly 15 break all flow ;)
        if add_l != 0:
            add_l = add_l -1

        for l in lines:
            t_lines.append({
                            'name':l.name,
                            'quantity':l.quantity,
                            'uos': l.uos_id and l.uos_id.name or '',
                            'price_unit': l.price_unit or '0.0',
                            'price_subtotal': l.price_subtotal or '0.0',
                            'symbol':symbol
                            })
        for add in range(0,add_l):
            t_lines.append({
                            'name':'',
                            'quantity':'',
                            'uos': '',
                            'price_unit': 0.0,
                            'price_subtotal': 0.0,
                            'symbol':''
                            })
        count = 0
        for add_brk in t_lines:
            count += 1
            if count%15 == 0:
                add_brk.update({'action':'break'})
            else:
                add_brk.update({'action':'nobreak'})
        return t_lines


    def _amount_to_text(self, amount):
        account_invoice_obj = self.pool.get('account.invoice')
        val = account_invoice_obj.amount_to_text(amount)
        return val
    
    def _get_quantity(self, id):
        account_invoice_obj = self.pool.get('account.invoice')
        val = account_invoice_obj._get_qty_total(self.cr, self.uid, self.ids)
        return int(val[id.id])

    def _payable_amounts(self, tax_line):
        pay_amt = 0.0
        for line in tax_line:
            if line.tax_categ in ('excise','cess','hedu_cess'):
                pay_amt += line.amount
        return pay_amt

    def _get_excise_cess(self, ids):
        cess_excise_amount = []
        account_invoice_obj = self.pool.get('account.invoice')
        excise_amount = 0.0
        cess_amount = 0.0
        for invoice in account_invoice_obj.browse(self.cr, self.uid, self.ids):
            for line in invoice.tax_line:
                if line.tax_categ == 'excise':
                    excise_amount += line.amount
#                    val = account_invoice_obj.amount_to_text(excise_amount)
#                    cess_excise_amount.append(val)
                if line.tax_categ == 'cess':
                    cess_amount += line.amount
#                    val = account_invoice_obj.amount_to_text(cess_amount)
#                    cess_excise_amount.append(val)
            val = account_invoice_obj.amount_to_text(excise_amount)
            cess_excise_amount.append(val)
            val = account_invoice_obj.amount_to_text(cess_amount)
            cess_excise_amount.append(val)
        self.x += self.x
        return cess_excise_amount 
    
    def excise_total(self):
        return self.x
    
    def _convert_int(self, amount):
        if isinstance(amount, (int, float)):
            amount = int(amount)
        return amount

report_sxw.report_sxw(
    'report.account.invoice.mrp.subcontract',
    'account.invoice',
    'addons/l10n_in_mrp_subcontract/report/account_print_invoice.rml',
    parser=account_l10n_in_mrp_subcontract,
    header=False
)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
