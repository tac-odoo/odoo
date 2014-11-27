from openerp import http
from openerp.http import request


class FinancialReportController(http.Controller):

    @http.route('/account/financial_report/<string:report_id>', type='http', auth='none')
    def financial_report(self, report_id, **kw):
        financial_report_id = request.env['account.financial.report'].sudo().browse(int(report_id))
        lines = financial_report_id.line.get_lines(financial_report_id)
        rcontext = {
            'o': financial_report_id,
            'lines': lines,
        }
        return request.render("account.report_financial", rcontext)

    @http.route('/account/financial_report/context/<string:context_id>', type='http', auth='none')
    def financial_report_context(self, context_id, **kw):
        financial_report_context_id = request.env['account.financial.report.context'].sudo().browse(int(context_id))
        financial_report_id = financial_report_context_id.financial_report_id
        lines = financial_report_id.line.with_context(
            date_from=financial_report_context_id.date_from,
            date_to=financial_report_context_id.date_to,
            target_move=financial_report_context_id.target_move,
            chart_account_id=financial_report_context_id.chart_account_id
        ).get_lines(financial_report_id)
        rcontext = {
            'context': financial_report_context_id,
            'o': financial_report_id,
            'lines': lines,
        }
        return request.render("account.report_financial", rcontext)
