from openerp import http
from openerp.http import request


class FinancialReportController(http.Controller):

    @http.route('/account/financial_report/<string:report_id>', type='http', auth='none')
    def financial_report(self, report_id, **kw):
        uid = request.session.uid
        report_id = int(report_id)
        context_id = request.env['account.financial.report.context'].sudo(uid).search(
            [('financial_report_id', '=', report_id), ('create_uid', '=', uid)],
            limit=1)
        if not context_id:
            context_id = request.env['account.financial.report.context'].sudo(uid).create({'financial_report_id': report_id})
        if 'print' in kw:
            response = request.make_response(None,
                headers=[('Content-Type', 'application/vnd.ms-excel'),
                         ('Content-Disposition', 'attachment; filename=table.xls;')])
            context_id.get_csv(response)
            return response
        if kw:
            update = {}
            for field in context_id._fields:
                if kw.get(field):
                    update[field] = kw[field]
                elif field in ['cash_basis', 'comparison']:
                    update[field] = False
            context_id.write(update)
        financial_report_id = request.env['account.financial.report'].sudo(uid).browse(report_id)
        lines = financial_report_id.line.get_lines_with_context(context_id)
        rcontext = {
            'context': context_id,
            'o': financial_report_id,
            'lines': lines,
        }
        return request.render("account.report_financial", rcontext)
