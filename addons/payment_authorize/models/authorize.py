# -*- coding: utf-'8' "-*-"

import time
import hmac
import hashlib
import logging
import urlparse

from openerp.osv import osv, fields
from openerp.addons.payment.models.payment_acquirer import ValidationError
from openerp.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)


class PaymentAcquirerAuthorize(osv.Model):
    _inherit = 'payment.acquirer'

    def _get_authorize_urls(self, cr, uid, environment, context=None):
        """ Authorize URLs """
        if environment == 'prod':
            return { 'authorize_form_url': 'https://secure.authorize.net/gateway/transact.dll' }
        else:
            return { 'authorize_form_url': 'https://test.authorize.net/gateway/transact.dll' }

    def _get_providers(self, cr, uid, context=None):
        providers = super(PaymentAcquirerAuthorize, self)._get_providers(cr, uid, context=context)
        providers.append(['authorize', 'Authorize'])
        return providers

    _columns = {
        'authorize_login': fields.char('API Login Id', required_if_provider='authorize'),
        'authorize_transaction_key': fields.char('API Transaction Key', required_if_provider='authorize'),
    }

    def _authorize_generate_hashing(self, values):
        data = '^'.join([values['x_login'],
               values['x_fp_sequence'],
               values['x_fp_timestamp'],
               values['x_amount'],
               values['currency_code']
               ])
        return hmac.new(str(values['x_trans_key']), data, hashlib.md5).hexdigest()

    def authorize_form_generate_values(self, cr, uid, id, partner_values, tx_values, context=None):
        base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')
        acquirer = self.browse(cr, uid, id, context=context)
        authorize_tx_values = dict(tx_values)
        temp_authorize_tx_values = {
            'x_login': acquirer.authorize_login,
            'x_trans_key': acquirer.authorize_transaction_key,
            'x_amount': str(tx_values['amount']),
            'x_show_form': 'PAYMENT_FORM',
            'x_type': 'AUTH_CAPTURE',
            'x_method': 'CC',
            'x_fp_sequence': '%s%s' % (acquirer.id, int(time.time())),
            'x_version': '3.1',
            'x_relay_response': 'TRUE',
            'x_fp_timestamp': str(int(time.time())),
            'x_relay_url': '%s' % urlparse.urljoin(base_url, '/payment/authorize/return/'),
            'currency_code': tx_values['currency'] and tx_values['currency'].name or '',
            'address': partner_values['address'],
            'city': partner_values['city'],
            'country': partner_values['country'] and partner_values['country'].name or '',
            'email': partner_values['email'],
            'zip': partner_values['zip'],
            'first_name': partner_values['first_name'],
            'last_name': partner_values['last_name'],
            'phone': partner_values['phone'],
        }
        temp_authorize_tx_values['x_fp_hash'] = self._authorize_generate_hashing(temp_authorize_tx_values)
        authorize_tx_values.update(temp_authorize_tx_values)
        return partner_values, authorize_tx_values

    def authorize_get_form_action_url(self, cr, uid, id, context=None):
        acquirer = self.browse(cr, uid, id, context=context)
        return self._get_authorize_urls(cr, uid, acquirer.environment, context=context)['authorize_form_url']

class TxAuthorize(osv.Model):
    _inherit = 'payment.transaction'

    _columns = {
         'authorize_txnid': fields.char('Transaction ID'),
    }
    
    _authorize_valid_tx_status = [1]
    _authorize_pending_tx_status = [4]
    _authorize_cancel_tx_status =[2]

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    def _authorize_form_get_tx_from_data(self, cr, uid, data, context=None):
        """ Given a data dict coming from authorize, verify it and find the related
        transaction record. """
        reference, trans_id, fingerprint = data.get('x_invoice_num'), data.get('x_trans_id'), data.get('x_MD5_Hash')
        if not reference or not trans_id or not fingerprint:
            error_msg = 'Authorize: received data with missing reference (%s) or trans_id (%s) or fingerprint (%s)' % (reference, trans_id, fingerprint)
            _logger.error(error_msg)
            raise ValidationError(error_msg)

        tx_ids = self.search(cr, uid, [('reference', '=', reference)], context=context)
        if not tx_ids or len(tx_ids) > 1:
            error_msg = 'Authorize: received data for reference %s' % (reference)
            if not tx_ids:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        tx = self.pool['payment.transaction'].browse(cr, uid, tx_ids[0], context=context)
        return tx

    def _authorize_form_get_invalid_parameters(self, cr, uid, tx, data, context=None):
        invalid_parameters = []

        if tx.acquirer_reference and data.get('x_trans_id') != tx.acquirer_reference:
            invalid_parameters.append(('Transaction Id', data.get('x_trans_id'), tx.acquirer_reference))
        # check what is buyed
        if float_compare(float(data.get('x_amount', '0.0')), tx.amount, 2) != 0:
            invalid_parameters.append(('Amount', data.get('x_amount'), '%.2f' % tx.amount))

        return invalid_parameters

    def _get_country(self, cr , uid , country, context=None):
        country_obj = self.pool['res.country']
        country_ids = country_obj.search(cr, uid, [('name' ,'=', country)],context=context)
        if not country_ids:
            return country_obj.create(cr, uid, {'name': country}, context)
        return country_ids[0]

    def _authorize_form_validate(self, cr, uid, tx, data, context=None):
        if tx.state == 'done':
            _logger.warning('Authorize: trying to validate an already validated tx (ref %s)' % tx.reference)
            return True
        # Need to update shipping and billing addresses
        # as authorize allow to edit address on authorize hosted form
        partner_obj = self.pool.get('res.partner')
        billing_values = {
            'name': "%s %s" % (data.get('x_first_name'), data.get('x_last_name')),
            'street': data.get('x_address'),
            'city': data.get('x_city'),
            'state': data.get('x_state'),
            'zip': data.get('x_zip'),
            'phone': data.get('x_phone'),
            'country_id': self._get_country(cr, uid, data.get('x_country'), context),
            'emaill' : data.get('x_email'),
        }
        partner_obj.write(cr, uid, tx.sale_order_id.partner_invoice_id.id, billing_values, context=context)
        if tx.sale_order_id.partner_shipping_id:
            shipping_values = {
                'name': "%s %s" % (data.get('x_ship_to_first_name'), data.get('x_ship_to_last_name')),
                'street': data.get('x_ship_to_address'),
                'city': data.get('x_ship_to_city'),
                'state': data.get('x_ship_to_state'),
                'zip': data.get('x_ship_to_zip'),
                'phone': data.get('x_phone'),
                'country_id': self._get_country(cr, uid, data.get('x_country'), context),
            }
            partner_obj.write(cr, uid, tx.sale_order_id.partner_shipping_id.id, shipping_values, context=context)

        status_code = int(data.get('x_response_code','0'))
        if status_code in self._authorize_valid_tx_status:
            tx.write({
                'state': 'done',
                'authorize_txnid': data.get('x_trans_id'),
                'acquirer_reference': data['x_invoice_num'],
            })
            return True
        elif status_code in self._authorize_pending_tx_status:
            tx.write({
                'state': 'pending',
                'authorize_txnid': data.get('x_trans_id'),
                'acquirer_reference': data['x_invoice_num'],
            })
            return True
        elif status_code in self._authorize_cancel_tx_status:
            tx.write({
                'state': 'cancel',
                'authorize_txnid': data.get('x_trans_id'),
                'acquirer_reference': data['x_invoice_num'],
            })
            return True
        else:
            error = data.get('x_response_reason_text')
            _logger.info(error)
            tx.write({
                'state': 'error',
                'state_message': error,
                'authorize_txnid': data.get('x_trans_id'),
                'acquirer_reference': data['x_invoice_num'],
            })
            return False
