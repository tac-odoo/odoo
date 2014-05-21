import base64
import psycopg2
import werkzeug

import openerp
from openerp import SUPERUSER_ID
from openerp import http
from openerp.http import request
from openerp.addons.web.controllers.main import content_disposition
import mimetypes


class MailController(http.Controller):
    _cp_path = '/mail'

    @http.route('/mail/download_attachment', type='http', auth='user')
    def download_attachment(self, model, id, method, attachment_id, **kw):
        # FIXME use /web/binary/saveas directly
        Model = request.registry.get(model)
        res = getattr(Model, method)(request.cr, request.uid, int(id), int(attachment_id))
        if res:
            filecontent = base64.b64decode(res.get('base64'))
            filename = res.get('filename')
            content_type = mimetypes.guess_type(filename)
            if filecontent and filename:
                return request.make_response(
                    filecontent,
                    headers=[('Content-Type', content_type[0] or 'application/octet-stream'),
                             ('Content-Disposition', content_disposition(filename))])
        return request.not_found()

    @http.route('/mail/receive', type='json', auth='none')
    def receive(self, req):
        """ End-point to receive mail from an external SMTP server. """
        dbs = req.jsonrequest.get('databases')
        for db in dbs:
            message = dbs[db].decode('base64')
            try:
                registry = openerp.registry(db)
                with registry.cursor() as cr:
                    mail_thread = registry['mail.thread']
                    mail_thread.message_process(cr, SUPERUSER_ID, None, message)
            except psycopg2.Error:
                pass
        return True

    @http.route('/mail_action/<model>/<int:id>', type='http', auth='user')
    def mail_action(self, model, id, action_name=None, action_type=None, action_id=None):
        if not request.session.uid:
            return login_redirect()
        redirect_url = "/web?db=%s#id=%s&model=%s" %(request.db, id, model)
        object_pool = request.registry.get(model)
        if action_type in ['workflow','object']:
            action = getattr(object_pool,action_name)
            action(request.cr, request.uid, [id], context=request.context)
            redirect_url += "&view_type=form"
        if action_type == 'action':
            redirect_url += "&action=%s" % action_id
        return werkzeug.utils.redirect(redirect_url)
