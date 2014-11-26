from openerp import http
from openerp.http import request
from openerp.report import report_sxw


class FinancialReportController(http.Controller):

    @http.route('/account/financial_report/<string:report_id>', type='http', auth='none')
    def financial_report(self, report_id, **kw):
        financial_report_id = request.env['account.financial.report'].sudo().browse(int(report_id))
        lines = financial_report_id.line.get_lines(financial_report_id)
        rcontext = {
            'o': financial_report_id,
            'lines': lines,
            'formatLang': report_sxw.rml_parse(request.env.cr, request.env.uid, 'financial_report', context=request.env.context).formatLang,
        }
        return request.render("account.report_financial", rcontext)
