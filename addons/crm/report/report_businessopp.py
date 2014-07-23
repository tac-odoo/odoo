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

import os, time

import random
import StringIO

from openerp.report.render import render
from openerp.report.interface import report_int
theme.use_color = 1

class external_pdf(render):

    """ Generate External PDF """

    def __init__(self, pdf):
        render.__init__(self)
        self.pdf = pdf
        self.output_type = 'pdf'

    def _render(self):
        return self.pdf

class report_custom(report_int):

    """ Create Custom Report """

    def create(self, cr, uid, ids, datas, context=None):

        """ @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of IDs
            @param context: A standard dictionary for contextual values """

        assert len(ids), 'You should provide some ids!'
        responsible_data = {}
        responsible_names = {}
        data = []
        minbenef = 999999999999999999999
        maxbenef = 0

        cr.execute('select probability, planned_revenue, planned_cost, user_id,\
                 res_users.name as name from crm_case left join res_users on \
                 (crm_case.user_id=res_users.id) where crm_case.id IN %s order by user_id',(tuple(ids),))

        res = cr.dictfetchall()
        for row in res:
            proba = row['probability'] or 0 / 100.0
            cost = row['planned_cost'] or 0
            revenue = row['planned_revenue'] or 0
            userid = row['user_id'] or 0

            benefit = revenue - cost
            if benefit > maxbenef:
                maxbenef = benefit
            if benefit < minbenef:
                minbenef = benefit

            tuple_benefit = (proba * 100,  benefit)
            responsible_data.setdefault(userid, [])
            responsible_data[userid].append(tuple_benefit)

            tuple_benefit = (proba * 100, cost, benefit)
            data.append(tuple_benefit)

            responsible_names[userid] = (row['name'] or '/').replace('/','//')

        minbenef -= maxbenef * 0.05
        maxbenef *= 1.2

        ratio = 0.5
        minmaxdiff2 = (maxbenef - minbenef)/2

        for l in responsible_data.itervalues():
            for i in range(len(l)):
                percent, benef = l[i]
                proba = percent/100

                current_ratio = 1 + (ratio-1) * proba

                newbenef = minmaxdiff2 + ((benef - minbenef - minmaxdiff2) * current_ratio)

                l[i] = (percent, newbenef)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

