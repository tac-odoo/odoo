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


class FitSheetWrapper(object):
    """Try to fit columns to max size of any entry.
    To use, wrap this around a worksheet returned from the
    workbook's add_sheet method, like follows:

        sheet = FitSheetWrapper(book.add_sheet(sheet_name))

    The worksheet interface remains the same: this is a drop-in wrapper
    for auto-sizing columns.
    """
    def __init__(self, sheet):
        self.sheet = sheet
        self.widths = dict()

    def write(self, r, c, label='', *args, **kwargs):
        self.sheet.write(r, c, label, *args, **kwargs)
        label_len = len(unicode(label))
        if label_len < 2:
            label_len = 2
        width = 366 * label_len
        if width > self.widths.get(c, 0):
            self.widths[c] = width
            self.sheet.col(c).width = int(width)

    def __getattr__(self, attr):
        return getattr(self.sheet, attr)

class EventExportPreplanning(openerp.addons.web.http.Controller):
    _cp_path = '/event/export/preplanning'

    @property
    def content_type(self):
        return 'application/vnd.ms-excel'

    def filename(self, base):
        return base + '.xls'

    def preplanning_data(self, eventinfo, weeks, contents, matrix):
        workbook = xlwt.Workbook()
        worksheet = FitSheetWrapper(workbook.add_sheet('Sheet 1'))
        worksheet.panes_frozen = True
        worksheet.vert_split_pos = 5
        worksheet.horz_split_pos = 2

        std_font = 'font: name Verdana, height 240;'


        header_left = xlwt.easyxf(std_font+'font: bold on; align: horiz left; pattern: pattern solid, fore-color grey25')
        header_center = xlwt.easyxf(std_font+'font: bold on; align: horiz center; pattern: pattern solid, fore-color grey25')
        header_rotated = xlwt.easyxf(std_font+'font: bold on; align: rotation 45, horiz left; pattern: pattern solid, fore-color grey25')
        cell_center = xlwt.easyxf(std_font+'align: horiz center')
        cell_center_hl = xlwt.easyxf(std_font+'align: horiz center; pattern: pattern solid, fore-color gray25')
        cell_no_week_slot = xlwt.easyxf(std_font+'align: horiz center; pattern: pattern solid, fore-color purple_ega')
        cell_value_hl = xlwt.easyxf(std_font+'font: bold on; align: horiz center; pattern: pattern solid, fore-color yellow')

        worksheet.write_merge(0, 0, 0, 4, '', header_left)
        worksheet.row(0).height = 1100
        colwidths = {}
        for i, week in enumerate(weeks, 5):
            worksheet.write(0, i, week['name'], header_rotated)
            worksheet.write(1, i, '%d/%d' % (week['slot_used'], week['slot_count']), header_center)
            worksheet.col(i).width = 366 * 5 + 400

        worksheet.row(1).height = 332
        worksheet.write(1, 0, 'Module', header_left)
        worksheet.write(1, 1, 'Subject', header_left)
        worksheet.write(1, 2, 'Content', header_left)
        worksheet.write(1, 3, 'Lang', header_left)
        worksheet.write(1, 4, 'Total', header_left)

        for j, content in enumerate(contents, 2):
            content_id = str(content['id'])
            worksheet.row(j).height = 332
            worksheet.write(j, 0, content['module_name'], header_left)
            worksheet.write(j, 1, content['subject_name'], header_left),
            worksheet.write(j, 2, content['name'], header_left),
            worksheet.write(j, 3, content['lang'], header_left)
            worksheet.write(j, 4, '%d / %d' % (content['slot_used'], content['slot_count']), header_center)
            row = matrix[content_id]
            row_style = cell_center
            if ((j - 2) % 2 == 1):
                row_style = cell_center_hl
            for i, week in enumerate(weeks, 5):
                cell_style = row_style
                value = row[week['id']]['value']
                if week['slot_count'] == 0:
                    cell_style = cell_no_week_slot
                elif value > 0:
                    cell_style = cell_value_hl
                worksheet.write(j, i, value, cell_style)

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
