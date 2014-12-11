# -*- encoding: utf-8 -*-
#################################################################################
#                                                                               #
# Copyright (C) 2009  Renato Lima - Akretion                                    #
#                                                                               #
#This program is free software: you can redistribute it and/or modify           #
#it under the terms of the GNU Affero General Public License as published by    #
#the Free Software Foundation, either version 3 of the License, or              #
#(at your option) any later version.                                            #
#                                                                               #
#This program is distributed in the hope that it will be useful,                #
#but WITHOUT ANY WARRANTY; without even the implied warranty of                 #
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the                  #
#GNU General Public License for more details.                                   #
#                                                                               #
#You should have received a copy of the GNU General Public License              #
#along with this program.  If not, see <http://www.gnu.org/licenses/>.          #
#################################################################################

import openerp
from openerp import SUPERUSER_ID
from openerp import api, fields, models


class account_tax_code_template(models.Model):
    """ Add fields used to define some brazilian taxes """
    _inherit = 'account.tax.code.template'
    domain = fields.Char(string='Domain', help="This field is only used if you develop your own module allowing developers to create specific taxes in a custom domain.")
    tax_discount = fields.Boolean(string='Discount this Tax in Prince', help="Mark it for (ICMS, PIS, COFINS and others taxes included).")

    @api.one
    def generate_tax_code(self, company_id):
        """This function generates the tax codes from the templates of tax
        code that are children of the given one passed in argument. Then it
        returns a dictionary with the mappping between the templates and the
        real objects.

        :param tax_code_root_id: id of the root of all the tax code templates
                                 to process.
        :param company_id: id of the company the wizard is running for
        :returns: dictionary with the mappping between the templates and the
                  real objects.
        :rtype: dict
        """
        obj_tax_code_template = self.env['account.tax.code.template']
        obj_tax_code = self.env['account.tax.code']
        tax_code_template_ref = {}
        company = company_id

        #find all the children of the tax_code_root_id
        children_tax_code_template = self.tax_code_root_id and obj_tax_code_template.search([('parent_id', 'child_of', [self.tax_code_root_id.id])], order='id') or []
        for tax_code_template in children_tax_code_template:
            parent_id = tax_code_template.parent_id and ((tax_code_template.parent_id.id in tax_code_template_ref) and tax_code_template_ref[tax_code_template.parent_id.id]) or False
            vals = {
                'name': (self.tax_code_root_id.id == tax_code_template.id) and company.name or tax_code_template.name,
                'code': tax_code_template.code,
                'info': tax_code_template.info,
                'parent_id': parent_id,
                'company_id': company_id,
                'sign': tax_code_template.sign,
                'domain': tax_code_template.domain,
                'tax_discount': tax_code_template.tax_discount,
            }
            #check if this tax code already exists
            rec_list = obj_tax_code.search([('name', '=', vals['name']),
                                            ('parent_id', '=', parent_id),
                                            ('code', '=', vals['code']),
                                            ('company_id', '=', vals['company_id'])])
            if not rec_list:
                #if not yet, create it
                new_tax_code = obj_tax_code.create(vals)
                #recording the new tax code to do the mapping
                tax_code_template_ref[tax_code_template.id] = new_tax_code.id
        return tax_code_template_ref


class account_tax_code(models.Model):
    """ Add fields used to define some brazilian taxes """
    _inherit = 'account.tax.code'
    domain = fields.Char(string='Domain', help="This field is only used if you develop your own module allowing developers to create specific taxes in a custom domain.")
    tax_discount = fields.Boolean(string='Discount this Tax in Prince', help="Mark it for (ICMS, PIS, COFINS and others taxes included).")


def get_precision_tax():
    def change_digit_tax(cr):
        res = openerp.registry(cr.dbname)['decimal.precision'].precision_get(cr, SUPERUSER_ID, 'Account')
        return (16, res+2)
    return change_digit_tax


class account_tax_template(models.Model):
    """ Add fields used to define some brazilian taxes """
    _inherit = 'account.tax.template'

    tax_discount = fields.Boolean(string='Discount this Tax in Prince', help="Mark it for (ICMS, PIS e etc.).")
    base_reduction = fields.Float(string='Redution', required=True, default=0, digits_compute=get_precision_tax(),  help="Um percentual decimal em % entre 0-1.")
    amount_mva = fields.Float(string='MVA Percent', required=True, default=0, digits_compute=get_precision_tax(),  help="Um percentual decimal em % entre 0-1.")
    type = fields.Selection([('percent', 'Percentage'),
                             ('fixed', 'Fixed Amount'),
                             ('none', 'None'),
                             ('code', 'Python Code'),
                             ('balance', 'Balance'),
                             ('quantity', 'Quantity')], 'Tax Type', required=True,
                            help="The computation method for the tax amount.")

    @api.multi
    def _generate_tax(self, tax_code_template_ref, company_id):
        """
        This method generate taxes from templates.

        :param tax_templates: list of browse record of the tax templates to process
        :param tax_code_template_ref: Taxcode templates reference.
        :param company_id: id of the company the wizard is running for
        :returns:
            {
            'tax_template_to_tax': mapping between tax template and the newly generated taxes corresponding,
            'account_dict': dictionary containing a to-do list with all the accounts to assign on new taxes
            }
        """
        result = super(account_tax_template, self)._generate_tax(tax_code_template_ref, company_id)
        tax_templates = self.browse(result['tax_template_to_tax'].keys())
        for tax_template in tax_templates:
            if tax_template.tax_code_id:
                tax_template.write({'domain': tax_template.tax_code_id.domain, 'tax_discount': tax_template.tax_code_id.tax_discount})
        return result

    @api.onchange('tax_code_id')
    def onchange_tax_code_id(self):
        result = {'value': {}}

        if not self.tax_code_id:
            return result

        if self.tax_code_id:
            result['value']['tax_discount'] = self.tax_code_id.tax_discount
            result['value']['domain'] = self.tax_code_id.domain
        return result


class account_tax(models.Model):
    """ Add fields used to define some brazilian taxes """
    _inherit = 'account.tax'

    tax_discount = fields.Boolean(string='Discount this Tax in Prince',
                                  help="Mark it for (ICMS, PIS e etc.).")
    base_reduction = fields.Float(string='Redution', required=True,
                                  default=0,
                                  digits_compute=get_precision_tax(),
                                  help="Um percentual decimal em % entre 0-1.")
    amount_mva = fields.Float(string='MVA Percent', required=True,
                              default=0,
                              digits_compute=get_precision_tax(),
                              help="Um percentual decimal em % entre 0-1.")
    type = fields.Selection([('percent', 'Percentage'),
                             ('fixed', 'Fixed Amount'),
                             ('none', 'None'),
                             ('code', 'Python Code'),
                             ('balance', 'Balance'),
                             ('quantity', 'Quantity')], string='Tax Type', required=True,
                            help="The computation method for the tax amount.")

    @api.onchange('tax_code_id')
    def onchange_tax_code_id(self):
        result = {'value': {}}

        if not self.tax_code_id:
            return result
        if self.tax_code_id:
            result['value']['tax_discount'] = self.tax_code_id.tax_discount
            result['value']['domain'] = self.tax_code_id.domain

        return result
