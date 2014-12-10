# -*- coding: utf-8 -*-

import datetime
from dateutil.relativedelta import relativedelta

from openerp.addons.membership.tests.common import TestMembershipCommon
from openerp.exceptions import AccessError, ValidationError, Warning
from openerp.tools import mute_logger


class TestMembership(TestMembershipCommon):

    def test_00_basic_membership(self):
        """ Basic membership flow """
        self.assertEqual(
            self.partner_1.membership_state, 'none',
            'membership: default membership status of partners should be None')

        # subscribes to a membership
        self.partner_1.create_membership_invoice(product_id=self.membership_1.id, datas={'amount': 75.0})

        # checks for invoices
        invoices = self.env['account.invoice'].search([('partner_id', '=', self.partner_1.id)], limit=1)
        self.assertEqual(
            invoices[0].state, 'draft',
            'membership: new subscription should create a draft invoice')
        self.assertEqual(
            invoices[0].invoice_line[0].product_id, self.membership_1,
            'membership: new subscription should create a line with the membership as product')
        self.assertEqual(
            invoices[0].invoice_line[0].price_unit, 75.0,
            'membership: new subscription should create a line with the given price instead of product price')

        self.assertEqual(
            self.partner_1.membership_state, 'waiting',
            'membership: new membership should be in waiting state')

        # the invoice is open -> custome goes to paid status
        invoices[0].signal_workflow('invoice_open')
        self.assertEqual(
            self.partner_1.membership_state, 'invoiced',
            'membership: after opening the invoice, customer should be in paid status')

        # check second partner then associate them
        self.assertEqual(
            self.partner_2.membership_state, 'free',
            'membership: free member customer should be in free state')
        self.partner_2.write({'free_member': False, 'associate_member': self.partner_1.id})
        self.assertEqual(
            self.partner_2.membership_state, 'invoiced',
            'membership: associated customer should be in paid state')
