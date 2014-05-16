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
from openerp.tools.translate import _
from openerp.report import report_sxw

class picking_revise(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(picking_revise, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time, 
            'yes_no': self.yes_no,
            'from_location': self.from_location,
            'to_location': self.to_location,
            'line_address': self.line_address
        })

    def yes_no(self, state):
        recieved = 'NO'
        if state == 'done': recieved = 'YES'
        return recieved


    def from_location(self, lines):
        where = ''
        for l in lines:
            if l.picking_id:
                if l.picking_id.pass_to_qc:
                    where = l.location_dest_id.name
                else:
                    where = l.location_id.name
                break
        return where

    def to_location(self, lines):
        to = ''
        for l in lines:
            if l.picking_id:
                if l.picking_id.pass_to_qc:
                    to = l.picking_id.move_loc_id and l.picking_id.move_loc_id.name or l.location_dest_id.name
                else:
                    to = l.location_dest_id.name
                break
        return to


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

report_sxw.report_sxw('report.stock.picking.list.in.revise', 'stock.picking.in', 'addons/l10n_in_mrp_subcontract/report/picking.rml', parser=picking_revise, header=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

