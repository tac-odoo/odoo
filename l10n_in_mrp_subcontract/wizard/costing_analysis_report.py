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
import pytz

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime
from dateutil.relativedelta import relativedelta

class costing_analysis_report(osv.osv_memory):
    _name = "costing.analysis.report"

    _columns = {
        'type': fields.selection([('date', 'DateWise'), ('order', 'OrderWise ')], 'Selection type'),
        'number_from': fields.integer('Number From'),
        'number_to': fields.integer('Number To'),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'draft': fields.boolean('Draft?'),
        'in_production': fields.boolean('Production Started?'),
        'ready': fields.boolean('Ready to Produce?'),
        'done': fields.boolean('Finished?'),
        'cancel': fields.boolean('Cancelled?'),
        'confirmed': fields.boolean('Awaiting Raw Materials?'),
        'picking_except':  fields.boolean('Picking Exception?'),
    }
    _defaults = {'type':'date', 'done':True}

    def date_to_datetime(self, cr, uid, userdate, context=None):
        """ Convert date values expressed in user's timezone to
        server-side UTC timestamp, assuming a default arbitrary
        time of 12:00 AM - because a time is needed.
    
        :param str userdate: date string in in user time zone
        :return: UTC datetime string for server-side use
        """
        # TODO: move to fields.datetime in server after 7.0
        user_date = datetime.strptime(userdate, DEFAULT_SERVER_DATETIME_FORMAT)
        if context and context.get('tz'):
            tz_name = context['tz']
        else:
            tz_name = self.pool.get('res.users').read(cr, 1, uid, ['tz'])['tz']
        if tz_name:
            utc = pytz.timezone('UTC')
            context_tz = pytz.timezone(tz_name)
            # not need if you give default datetime into entry ;)
            user_datetime = user_date  # + relativedelta(hours=24.0)
            local_timestamp = context_tz.localize(user_datetime, is_dst=False)
            user_datetime = local_timestamp.astimezone(utc)
            return user_datetime.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        return user_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    def _make_query_result(self, cr , uid, data, context=None):
        """
        Process
            -To make Query According to Datewise,Number Wise. 
        """
        search_criterea = ''
        #Date Wise Bifurcation
        if data.type == 'date':
            start = data.start_date
            end = data.end_date
            if start and end:
                start = self.date_to_datetime(cr, uid, start + ' 00:00:00', context=context)
                end = self.date_to_datetime(cr, uid, end + ' 23:59:59', context=context)
                search_criterea += " AND mp.date_planned > '" + str(start) + "' AND mp.date_finished < '" + str(end) + "' "
            elif start:
                start = self.date_to_datetime(cr, uid, start + ' 00:00:00', context=context)
                search_criterea += " AND mp.date_planned > '" + str(start) + "' "
            elif end:
                end = self.date_to_datetime(cr, uid, end + ' 23:59:59', context=context)
                search_criterea += " AND mp.date_finished < '" + str(end) + "' "
        else:
            #Number Wise Bifurcation
            number_from = data.number_from
            number_to = data.number_to
            if number_from <= 0 or number_to <= 0:
                raise osv.except_osv(_('Warning!'), _('Negative or Zero number  not allow to pass!'))
            if number_from > 0 and number_to > 0:
                if number_from > number_to:
                    raise osv.except_osv(_('Warning!'), _('Please correct the number place.\nNumber To must be greater then Number From.'))
            count, comma =  0, True
            if number_from == number_to:
                comma = False
            for r in range(number_from, number_to + 1):
                count += 1
                if count == 1: search_criterea += " AND mp.name SIMILAR TO '%("
                search_criterea += str(r)
                if comma and (r <> number_to): search_criterea += '|'
                if r == number_to: search_criterea += ")%'"
        #State Wise Bifurcation
        if data.draft or data.in_production or data.ready or data.done or data.cancel or data.confirmed or data.picking_except:
            if not search_criterea: search_criterea += ' AND mp.state in ('
            else:
                search_criterea += ' AND mp.state in ('
            j_s = ''
            if data.draft: j_s += "'draft',"
            if data.in_production: j_s += "'in_production',"
            if data.ready: j_s += "'ready',"
            if data.done: j_s += "'done',"
            if data.cancel: j_s += "'cancel',"
            if data.confirmed: j_s += "'confirmed',"
            if data.picking_except: j_s += "'picking_except',"
            search_criterea += j_s[:-1]+')'
        if search_criterea: search_criterea = ' WHERE  mpwl.production_id = mp.id ' + search_criterea
        #Merged this query criterea for execution
        cr.execute(""" SELECT mpwl.id FROM mrp_production mp, mrp_production_workcenter_line mpwl """+ search_criterea)
        return [r[0] for r in cr.fetchall()]

    def open_workorders(self, cr, uid, ids, context=None):
        """
        process
            -Open workorder analysis Report base on criaterea,
                -Datewise Filter
                -Orderwise Filter
                -Production State Filter
        return
            -Planned Time,Actual Time,Planning cost,Actual cost group by production order 
        """
        context = context or {}
        models_data = self.pool.get('ir.model.data')
        data = self.browse(cr, uid, ids[0])
        wo_ids = self._make_query_result(cr, uid, data, context=context)

        # Get workorder views
        dummy, form_view = models_data.get_object_reference(cr, uid, 'l10n_in_mrp_subcontract', 'mrp_production_workcenter_form_cost_report')
        dummy, tree_view = models_data.get_object_reference(cr, uid, 'l10n_in_mrp_subcontract', 'mrp_production_workcenter_tree_view_cost_report')

        context.update({'group_by':'production_id'})

        return {
            'domain': "[('id','in',["+','.join(map(str, wo_ids))+"])]",
            'name': _('WorkOrder Cost Analysis'),
            'view_type': 'form',
            'view_mode': 'form',
            'context':context,
            'res_model': 'mrp.production.workcenter.line',
            'views': [(tree_view or False, 'tree'), (form_view or False, 'form')],
            'type': 'ir.actions.act_window',
        }

costing_analysis_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
