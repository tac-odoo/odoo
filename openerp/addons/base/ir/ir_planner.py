##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014 OpenERP SA (<http://www.openerp.com>)
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
from openerp.osv import osv, fields


class ir_application_planner(osv.Model):
    _name = 'ir.aplication.planner'
    _columns = {
        'application_id': fields.many2one('ir.ui.menu'),
        'name': fields.char('Name'),
        # 'progress': fields.function(type='integer', compute based on the waiteged),
        'page_ids': fields.one2many('ir.application.planner.page','planner_id'),
        'company_id': fields.many2one('res.company')
    }


class ir_application_planner_page_category(osv.Model):
    _name = 'ir.application.planner.page.category'
    _order = 'sequence'
    _columns = {
        'name': fields.char('Name'),
        'icon': fields.char('Icon'),
        'sequence': fields.integer('Sequence')
    }


class ir_application_planner_page(osv.Model):
    _name = 'ir.application.planner.page'
    _order = 'sequence'
    _columns = {
        'category_id': fields.many2one('ir.application.planner.page.category'),
        'planner_id': fields.many2one('ir.aplication.planner'),
        'name': fields.char('Title'),
        'description': fields.html('Description'),
        'sequence': fields.integer('Sequence'),
        'completed': fields.boolean('State')
    }
