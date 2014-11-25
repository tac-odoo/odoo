from openerp import http
from openerp.http import request


class FinancialReportController(http.Controller):

    @http.route('/account/financial_report/<string:report_id>', type='http', auth='none')
    def financial_report(self, report_id, **kw):
        financial_report_id = request.env['account.financial.report'].sudo().browse(int(report_id))
        lines = financial_report_id.line.get_lines(financial_report_id)
        return request.render("account.report_financial", {'o': financial_report_id, 'lines': lines})
