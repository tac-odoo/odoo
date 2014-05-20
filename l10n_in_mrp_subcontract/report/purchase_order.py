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
from openerp.tools.translate import _
from openerp.tools import amount_to_text_en
from operator import itemgetter

class purchase_order_revise(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(purchase_order_revise, self).__init__(cr, uid, name, context=context)
        self.t_pkg_frwrd = 0.0
        self.t_freight = 0.0
        self.t_insurance = 0.0
        self.localcontext.update({
            'time': time,
            'line_address': self.line_address,
            'calculate_price': self.calculate_price,
            'calculate_tax': self.calculate_tax,
            'convert': self.convert,
            'other_charges':self._other_charges,
            'pkg_frwrd':self._pkg_frwrd,
            'freight':self._freight,
            'insurance':self._insurance,
            'user': self.pool.get('res.users').browse(cr, uid, uid, context)
        })

    def _pkg_frwrd(self):
        return self.t_pkg_frwrd

    def _freight(self):
        return self.t_freight

    def _insurance(self):
        return self.t_insurance

    def convert(self, amount, cur):
        amt_en = amount_to_text_en.amount_to_text(amount, 'en', cur)
        return amt_en

    def calculate_price(self, line):
        price = 0.0
        if line:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
        return price

    def _other_charges(self, order):
        pur_obj=self.pool.get('purchase.order')
        cr, uid = self.cr, self.uid
        #method to get all extra charges individualy
        pkg_frwrd, freight, insurance = pur_obj.other_charges(cr, uid, order)

        self.t_pkg_frwrd = pkg_frwrd
        self.t_freight = freight
        self.t_insurance = insurance
        return True

    def line_address(self, company):
        if not company:
            return {}

        address = ''
        if company.street: address += company.street
        if company.street2: address += address and ','+company.street2 or company.street2
        if company.street2: address += address and ','+company.city or company.city
        if company.street2: address += address and company.state_id and ','+company.state_id.name or company.state_id.name 
        if company.street2: address += address and company.country_id and ','+company.country_id.name or company.country_id.name
        if company.street2: address += address and ','+company.zip or company.zip

        # first line (notice that missing elements are filtered out before the join)
        res = ' | '.join(filter(bool, [
            address                  and '%s: %s' % (_('Address:'), address),
            company.phone            and '%s: %s' % (_('Phone'), company.phone),
            company.fax              and '%s: %s' % (_('Fax'), company.fax),
            company.email            and '%s: %s' % (_('Email'), company.email),
            company.website          and '%s: %s' % (_('Website'), company.website),
            company.vat              and '%s: %s' % (_('TIN'), company.vat),
        ]))
        return res

    def calculate_tax(self, purchase_id):
        tax_grouped = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        purchase = self.pool.get('purchase.order').browse(self.cr, self.uid, purchase_id)
        cur = purchase.currency_id
        company_currency = self.pool['res.company'].browse(self.cr, self.uid, purchase.company_id.id).currency_id.id
        for line in purchase.order_line:
            base_price = line.purchase_unit_rate * (1 - (line.discount or 0.0) / 100.0)
            for tax in tax_obj.compute_all(self.cr, self.uid, line.taxes_id, base_price, line.line_qty, line.product_id, purchase.partner_id)['taxes']:
                val={}
                val['name'] = tax['name']
                val['amount'] = tax['amount']
                val['manual'] = False
                val['sequence'] = tax['sequence']
                val['base'] = cur_obj.round(self.cr, self.uid, cur, tax['price_unit'] * line['line_qty'])

                val['base_code_id'] = tax['base_code_id']
                val['tax_code_id'] = tax['tax_code_id']
                val['base_amount'] = cur_obj.compute(self.cr, self.uid, purchase.currency_id.id, company_currency, val['base'] * tax['base_sign'], context={'date': purchase.date_order or time.strftime('%Y-%m-%d')}, round=False)
                val['tax_amount'] = cur_obj.compute(self.cr, self.uid, purchase.currency_id.id, company_currency, val['amount'] * tax['tax_sign'], context={'date': purchase.date_order or time.strftime('%Y-%m-%d')}, round=False)
                #if not set account_id on tax
                val['account_id'] = tax['account_collected_id'] or False#or line.account_id.id
                val['account_analytic_id'] = tax['account_analytic_collected_id']

                key = (val['tax_code_id'], val['base_code_id'], val['account_id'], val['account_analytic_id'])
                if not key in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += val['base']
                    tax_grouped[key]['base_amount'] += val['base_amount']
                    tax_grouped[key]['tax_amount'] += val['tax_amount']
        res_list = []
        for t in tax_grouped.values():
            t['base'] = cur_obj.round(self.cr, self.uid, cur, t['base'])
            t['amount'] = cur_obj.round(self.cr, self.uid, cur, t['amount'])
            t['base_amount'] = cur_obj.round(self.cr, self.uid, cur, t['base_amount'])
            t['tax_amount'] = cur_obj.round(self.cr, self.uid, cur, t['tax_amount'])
            res_list.append(t)

        return sorted(res_list, key=itemgetter('sequence'))

report_sxw.report_sxw('report.purchase.order.revise','purchase.order','addons/l10n_in_mrp_subcontract/report/purchase_order.rml',parser=purchase_order_revise,header=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

