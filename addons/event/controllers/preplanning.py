# -*- coding: utf-8 ⁻*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2013-TODAY OpenERP S.A. (<http://openerp.com>).
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

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import time
import xlwt
import simplejson
import operator
import openerp
from openerp.addons.web.controllers.main import content_disposition


class EventExportPreplanning(openerp.addons.web.http.Controller):
    _cp_path = '/event/export/preplanning'

    @property
    def content_type(self):
        return 'application/vnd.ms-excel'

    def filename(self, base):
        return base + '.xls'

    def preplanning_data(self, eventinfo, weeks, contents, matrix):
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Sheet 1')

        header_left = xlwt.easyxf('font: bold on; align: horiz left')
        header_center = xlwt.easyxf('font: bold on; align: horiz center')
        header_rotated = xlwt.easyxf('font: bold on; align: rotation 90, horiz center')
        cell_center = xlwt.easyxf('align: horiz center')

        for i, week in enumerate(weeks, 2):
            worksheet.write(0, i, week['name'], header_rotated)
            worksheet.write(1, i, '%d / %d' % (week['slot_used'], week['slot_count']), header_center)
            worksheet.col(i).width = 2000

        worksheet.col(0).width = 10000
        worksheet.write(1, 1, 'Total', header_left)

        for j, content in enumerate(contents, 2):
            content_id = str(content['id'])
            worksheet.write(j, 0, content['name'], header_left)
            worksheet.write(j, 1, '%d / %d' % (content['slot_used'], content['slot_count']), header_center)
            row = matrix[content_id]
            for i, week in enumerate(weeks, 2):
                value = row[week['id']]['value']
                worksheet.write(j, i, value, cell_center)

        fp = StringIO()
        workbook.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()
        return data

    @openerp.addons.web.http.httprequest
    def index(self, req, data, token):
        event_id, weeks, contents, matrix = \
            operator.itemgetter('event_id', 'weeks', 'contents', 'matrix')(
                simplejson.loads(data))
        Event = req.session.model('event.event')
        eventinfo = Event.read([event_id], ['name', 'date_begin', 'date_end'])[0]

        fnbase = u'Preplanning_%s_%s' % (eventinfo['name'], time.strftime('%Y%m%d_%H%M%S'))

        return req.make_response(self.preplanning_data(eventinfo, weeks, contents, matrix),
            headers=[('Content-Disposition',
                            content_disposition(self.filename(fnbase), req)),
                     ('Content-Type', self.content_type)],
            cookies={'fileToken': token})
