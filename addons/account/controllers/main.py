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
        fields = ['date_from', 'date_to', 'target_move', 'chart_account_id', 'comparison',
                  'date_from_cmp', 'date_to_cmp', 'cash_basis']
        if kw:
            for field in fields:
                if kw.get(field):
                    update[field] = kw[field]
                else:
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
