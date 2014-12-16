from openerp import http
from openerp.http import request


class FinancialReportController(http.Controller):

    def get_report_obj_from_name(self, name):
        if name == 'financial_report':
            return request.env['account.financial.report']

    @http.route('/account/<string:report_obj>/<string:report_id>', type='http', auth='none')
    def financial_report(self, report_name, report_id, **kw):
        uid = request.session.uid
        report_obj = self.get_report_obj_from_name(report_name)
        domain = [('report_name', '=', report_name), ('create_uid', '=', uid)]
        if report_name == 'financial_report':
            report_id = int(report_id)
            domain.append(('report_id', '=', report_id))
            report_obj = report_obj.sudo(uid).browse(report_id).line
        context_id = request.env['account.financial.report.context'].sudo(uid).search(domain, limit=1)
        if not context_id:
            create_vals = {'report_name': report_name}
            if report_name == 'financial_report':
                create_vals['financial_report_id'] = report_id
            context_id = request.env['account.financial.report.context'].sudo(uid).create(create_vals)
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
        lines = report_obj.get_lines_with_context(context_id)
        rcontext = {
            'context': context_id,
            'o': report_obj,
            'lines': lines,
        }
        return request.render("account.report_financial", rcontext)
