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
from openerp.tools import amount_to_text_en
from operator import itemgetter
from openerp.tools.translate import _
from openerp.report import report_sxw

class order_revise(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(order_revise, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time, 
            'convert': self.convert,
            'calculate_price': self.calculate_price,
            'calculate_tax': self.calculate_tax,
            'line_address': self.line_address
        })

    def convert(self, amount, cur):
        amt_en = amount_to_text_en.amount_to_text(amount, 'en', cur)
        return amt_en

    def calculate_price(self, line):
        price = 0.0
        if line:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
        return price

    def calculate_tax(self, sale_id):
        tax_grouped = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        sale = self.pool.get('sale.order').browse(self.cr, self.uid, sale_id)
        cur = sale.currency_id
        company_currency = self.pool['res.company'].browse(self.cr, self.uid, sale.company_id.id).currency_id.id
        for line in sale.order_line:
            for tax in tax_obj.compute_all(self.cr, self.uid, line.tax_id, (line.price_unit* (1-(line.discount or 0.0)/100.0)), line.product_uom_qty, line.product_id, sale.partner_id)['taxes']:
                val={}
                val['name'] = tax['name']
                val['amount'] = tax['amount']
                val['manual'] = False
                val['sequence'] = tax['sequence']
                val['base'] = cur_obj.round(self.cr, self.uid, cur, tax['price_unit'] * line['product_uom_qty'])

                val['base_code_id'] = tax['base_code_id']
                val['tax_code_id'] = tax['tax_code_id']
                val['base_amount'] = cur_obj.compute(self.cr, self.uid, sale.currency_id.id, company_currency, val['base'] * tax['base_sign'], context={'date': sale.date_order or time.strftime('%Y-%m-%d')}, round=False)
                val['tax_amount'] = cur_obj.compute(self.cr, self.uid, sale.currency_id.id, company_currency, val['amount'] * tax['tax_sign'], context={'date': sale.date_order or time.strftime('%Y-%m-%d')}, round=False)
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

    def _show_discount(self, uid, context=None):
        cr = self.cr
        try: 
            group_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'sale', 'group_discount_per_so_line')[1]
        except:
            return False
        return group_id in [x.id for x in self.pool.get('res.users').browse(cr, uid, uid, context=context).groups_id]

report_sxw.report_sxw('report.sale.order.revise', 'sale.order', 'addons/l10n_in_mrp_subcontract/report/sale_order.rml', parser=order_revise,header=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

