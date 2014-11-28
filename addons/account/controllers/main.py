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
        update = {}
        if kw.get('date_from'):
            update['date_from'] = kw['date_from']
        if kw.get('date_to'):
            update['date_to'] = kw['date_to']
        if kw.get('target_move'):
            update['target_move'] = kw['target_move']
        if kw.get('chart_account_id'):
            update['chart_account_id'] = kw['chart_account_id']
        context_id.write(update)
        financial_report_id = request.env['account.financial.report'].sudo(uid).browse(report_id)
        lines = financial_report_id.line.get_lines_with_context(context_id)
        rcontext = {
            'context': context_id,
            'o': financial_report_id,
            'lines': lines,
        }
        return request.render("account.report_financial", rcontext)
