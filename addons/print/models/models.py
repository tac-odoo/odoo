# -*- coding: utf-8 -*-
import base64
import re
import time

from openerp import api, fields, models
from openerp.tools.translate import _
from itertools import groupby

class print_provider(models.Model):
    """ Print Provider Base Model. Each specific provider can extend the model by adding
        its own fields, using the provider_name (provider field) as a prefix for the new
        fields and method.
    """

    _name = 'print.provider'
    _rec_name = 'name'
    _description = 'Postal Provider'


    @api.model
    def _get_providers(self):
        return []

    # --------------------------------------------------
    # MODEL FIELDS
    # --------------------------------------------------
    name = fields.Char("Name", required=True)
    environment = fields.Selection([('test', 'Test'),('production', 'Production')], "Environment", default='test')
    provider = fields.Selection(selection='_get_providers', string='Provider', required=True)
    balance = fields.Float("Credit", digits=(16,2))


    # --------------------------------------------------
    # METHOD to be redefined in the provider implemenation
    # --------------------------------------------------
    @api.one
    def update_account_data(self):
        """ Update the provider account data. Requires a fetch to the provider server. """
        if hasattr(self, '%s_update_account_data' % self.provider):
            return getattr(self, '%s_update_account_data' % self.provider)()

    @api.one
    def check_configuration(self):
        """ Check if the credentials of the current provider are filled. If not, raise a warning. """
        if hasattr(self, '%s_check_configuration' % self.provider):
            return getattr(self, '%s_check_configuration' % self.provider)()


class print_order(models.Model):
    """ Print Order Model. Each specific provider can extend the model by adding
        its own fields, using the same convertion of the print.provider model.
    """

    _name = 'print.order'
    _rec_name = 'id'
    _description = 'Postal Order'
    _order = 'send_date desc'

    @api.model
    def _default_currency(self):
        return self.env.user.company_id.currency_id

    @api.model
    def _default_print_provider(self):
        return self.env['ir.values'].get_default('print.order', 'provider_id')

    # --------------------------------------------------
    # MODEL FIELDS
    # --------------------------------------------------
    create_date = fields.Datetime('Creation Date', readonly=True)
    send_date = fields.Datetime('Sending Date', default=False, readonly=True)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, default=_default_currency, readonly=True, states={'draft':[('readonly',False)]})
    user_id = fields.Many2one('res.users', 'Author', default=lambda self: self.env.user, readonly=True)
    provider_id = fields.Many2one('print.provider', 'Print Provider', required=True, default=_default_print_provider, readonly=True, states={'draft':[('readonly',False)]})

    ink = fields.Selection([('BW', 'Black & White'),('CL', 'Colour')], "Ink", default='BW', states={'sent':[('readonly',True)]})
    paper = fields.Integer("Paper Weight", default=80, readonly=True)
    res_id = fields.Integer('Object ID')
    res_model = fields.Char('Model Name')

    attachment_id = fields.Many2one('ir.attachment', 'PDF', states={'sent':[('readonly',True)]}, domain=[('mimetype', '=', 'application/pdf')])
    nbr_pages = fields.Integer("Number of Pages", readonly=True, default=0)
    price = fields.Float("Cost to Deliver", digits=(16,2), readonly=True, default=0.0)

    error_message = fields.Text('Error Message', readonly=True)

    state = fields.Selection([
            ('draft', 'Draft'),
            ('ready_to_send', 'Ready'),
            ('sent', 'Sent'),
            ('error', 'Failed'),
        ], string='Status', default='draft', readonly=True, required=True)

    # duplicate partner infos to keep trace of where the documents was sent
    partner_id = fields.Many2one('res.partner', 'Recipient partner', states={'sent':[('readonly',True)]})
    partner_name = fields.Char('Name', required=True, states={'sent':[('readonly',True)]})
    partner_street = fields.Char('Street', required=True, states={'sent':[('readonly',True)]})
    partner_street2 = fields.Char('Street2', states={'sent':[('readonly',True)]})
    partner_state_id = fields.Many2one("res.country.state", 'State', states={'sent':[('readonly',True)]})
    partner_zip = fields.Char('Zip', required=True, states={'sent':[('readonly',True)]})
    partner_city = fields.Char('City', required=True, states={'sent':[('readonly',True)]})
    partner_country_id = fields.Many2one('res.country', 'Country', required=True, states={'sent':[('readonly',True)]})


    # --------------------------------------------------
    # Methods
    # --------------------------------------------------
    @api.model
    def _count_pages_pdf(self, bin_pdf):
        """ Count the number of pages of the given pdf file.
            :param bin_pdf : binary content of the pdf file
        """
        pages = 0
        for match in re.compile(r"/Count\s+(\d+)").finditer(bin_pdf):
            pages = int(match.group(1))
        return pages

    @api.multi
    def _generate_attachment(self):
        """ For the given recordset, compute the number of page in the attachment.
            If no attachment, one will be generated with the res_model/res_id
        """
        Attachment = self.env['ir.attachment']
        ReportXml = self.env['ir.actions.report.xml']
        Report = self.pool['report'] # old api, see below
        pages = {}
        for record in self:
            if not record.attachment_id:
                if record.res_model and record.res_id:
                    # check if a report exists for current res_model
                    report = ReportXml.search([('model', '=', record.res_model)], limit=1)
                    if report:
                        object_to_print = self.env[record.res_model].browse(record.res_id)

                        # get the binary pdf content
                        # Call the v7 version without context (!important) to avoid "'update' not supported on frozendict".
                        # TODO : when report.py in v8, change this call (and test it !)
                        bin_pdf = Report.get_pdf(self._cr, self._uid, [record.res_id], report.report_name)

                        # compute the name of the new attachment
                        filename = False
                        if report.attachment:
                            filename = eval(report.attachment, {'object': object_to_print, 'time': time})
                        if not filename:
                            filename = '%s-%s' % (record.res_model.replace(".", "_"),record.res_id)

                        # create the new ir_attachment
                        attachment_value = {
                            'name': filename,
                            'res_name': filename,
                            'res_model': record.res_model,
                            'res_id': record.res_id,
                            'datas': base64.b64encode(bin_pdf),
                            'datas_fname': filename+'.pdf',
                        }
                        new_attachment = Attachment.create(attachment_value)

                        # add the new attachment to the print order
                        record.write({
                            'nbr_pages' : self._count_pages_pdf(bin_pdf),
                            'attachment_id' : new_attachment.id
                        })
                    else:
                        # no ir.actions.report.xml found for res_model
                        record.write({
                            'state' : 'error',
                            'error_message' : _('The document you want to print and send is not printable. There is no report action (ir.actions.report.xml) for the model %s.') % (record.res_model,)
                        })
                else:
                    # error : not attachament can be generate, no attach_id or no res_model/res_id
                    record.write({
                        'state' : 'error',
                        'error_message' : _('The document has no associated PDF : you have to give select an Attachment file, or set up the Object ID and Model Name fields.')
                    })
            else:
                # avoid to recompute the number of page each time for the attachment
                nbr_pages = pages.get(record.attachment_id.id)
                if not nbr_pages:
                    nbr_pages = self._count_pages_pdf(record.attachment_id.datas.decode('base64'))
                    pages[record.attachment_id.id] = nbr_pages
                record.write({
                    'nbr_pages' : nbr_pages
                })


    @api.multi
    def _prepare_printing(self):
        """ Prepare the orders for delivery. It executes the operations to put
            them into the 'ready' state (or 'error' if something wrong happens).
            /!\ Self must be print.order having the same provider, to stay the optimized.
            To allow optimizations in the provider implementation, the orders
            are grouped by provider.
        """
        # generate PDF for the recordset
        self._generate_attachment()

        # call provider implementation
        provider_name = self[0].provider_id.provider
        if hasattr(self, '_%s_prepare_printing' % provider_name):
                getattr(self, '_%s_prepare_printing' % provider_name)()

    @api.multi
    def _deliver_printing(self):
        """ Send the orders for delivery to the Provider. It executes the operations to put
            them into the 'sent' state (or 'error' if something wrong happens).
            /!\ Self must be print.order having the same provider, to stay the optimized.
        """
        # call provider implementation
        provider_name = self[0].provider_id.provider
        if hasattr(self, '_%s_deliver_printing' % provider_name):
            getattr(self, '_%s_deliver_printing' % provider_name)()

    @api.multi
    def _validate_printing(self):
        """ For the given recordset, apply the action on the printable objects when the sending
            is correctly done. This call the 'print_validate_sending' method of the printable object.
            This method group the PO by res_model to optimize the browse.
        """
        # group the PO by res_model
        group_by_res_model = dict((k, list(g)) for k, g in groupby(self, lambda record : record.res_model))
        for model in group_by_res_model.keys():
            if model: # res_model is optional field
                if hasattr(self.env[model], 'print_validate_sending'):
                    # take only the correctly sent
                    objects = self.env[model].browse([rec.res_id for rec in group_by_res_model[model] if rec.state == 'sent'])
                    objects.print_validate_sending()

    @api.model
    def process_order_queue(self, order_ids=None):
        """ Immediately send the queue, or the list of given order_ids.
            If the sending failed, it send a mail_message to the author of the print order, and the PO state
            is set to 'error'. If sending is successful, the state will be 'sent'.
            This method is called by the sendnow wizard, but also by the ir_cron.
            :param order_ids : optinal list of order ids
        """
        # find ids if not given, and only keep the not sent orders
        if not order_ids:
            orders = self.search([('state', 'not in', ['sent'])])
        else:
            orders = self.browse(order_ids)
            orders.filtered(lambda r: not r.state in ['sent'])

        # Treat the Print Orders, grouped by provider
        group_by_provider = dict((k, list(g)) for k, g in groupby(orders, lambda record : record.provider_id.id))
        for provider_id in group_by_provider.keys():
            current_orders = self.browse([rec.id for rec in group_by_provider[provider_id]])
            current_orders._prepare_printing()
            current_orders._deliver_printing()

        # Validate the sending, on all the treated Print Orders
        orders._validate_printing()

        # error controll : built the list of user to notify
        # create a dict 'user_to_notify' where
        #   key = user_id
        #   value = list of tuple (order_id, error_message) for all order not sent correctly
        user_to_notify = {}
        for record in orders:
            if record.state == 'error':
                if not record.user_id.id in user_to_notify:
                    user_to_notify[record.user_id.id] = []
                user_to_notify[record.user_id.id].append((record.id, record.error_message))

        # send a message to the author of the failed print orders
        Mail_message = self.env['mail.message']
        for user in self.env['res.users'].browse(user_to_notify.keys()):
            errors = ["   %s      |  %s" % (code, msg) for code, msg in  user_to_notify[user.id]]
            body = _("Dear %s,<br/> \
                    Some print orders was not sent during the last processing. Please, check \
                    the following errors, and correct them. You can find them in Settings > Print Orders. <br/><br/> \
                     Print Order ID  |      Error Message <br/>\
                    ----------------------------------------- <br/>\
                     %s") % (user.partner_id.name, "<br/>".join(errors))
            Mail_message.sudo().create({
                'body' : body,
                'subject' : _("Print Orders Failed"),
                'partner_ids': [(4, user.partner_id.id)]
            })


    # --------------------------------------------------
    # Actions
    # --------------------------------------------------
    @api.multi
    def action_reset_draft(self):
        self.write({
            'state' : 'draft',
            'error_message' : False
        })

    @api.multi
    def action_send_now(self):
        self.process_order_queue(self.ids)

    @api.multi
    def action_compute_price(self):
        """ Compute the price of the delivery. """
        group_by_provider_id = dict((k, list(g)) for k, g in groupby(self, lambda record : record.provider_id.id))
        for provider_id in group_by_provider_id.keys():
            current_orders = self.browse(r.id for r in group_by_provider_id[provider_id])
            current_orders._prepare_printing()
            # call the provider implementation
            if hasattr(current_orders, '_%s_action_compute_price' % current_orders[0].provider_id.provider):
                getattr(current_orders, '_%s_action_compute_price' % current_orders[0].provider_id.provider)()

