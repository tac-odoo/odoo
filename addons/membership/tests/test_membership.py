# -*- coding: utf-8 -*-

import datetime
from dateutil.relativedelta import relativedelta

from openerp.addons.membership.tests.common import TestMembershipCommon
from openerp.exceptions import AccessError, ValidationError, Warning
from openerp.tools import mute_logger


class TestMembership(TestMembershipCommon):

    def test_00_basic_membership(self):
        """ Basic membership flow """
        print 'BEGIN'
        self.assertEqual(
            self.partner_1.membership_state, 'none',
            'membership: default membership status of partners should be None')

        # subscribes to a membership
        print '-------------'
        self.partner_1.create_membership_invoice(product_id=self.membership_1.id, datas={'amount': 75.0})
        print '-------------'

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

        print self.partner_1.membership_state
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


    #     """ Basic event management with auto confirmation """
    #     self.env['ir.values'].set_default('marketing.config.settings', 'auto_confirmation', True)

    #     # EventUser creates a new event: ok
    #     test_event = self.Event.sudo(self.user_eventmanager).create({
    #         'name': 'TestEvent',
    #         'date_begin': datetime.datetime.now() + relativedelta(days=-1),
    #         'date_end': datetime.datetime.now() + relativedelta(days=1),
    #         'seats_max': 2,
    #     })
    #     self.assertEqual(test_event.state, 'confirm', 'Event: auto_confirmation of event failed')

    #     # EventUser create registrations for this event
    #     test_reg1 = self.Registration.sudo(self.user_eventuser).create({
    #         'name': 'TestReg1',
    #         'event_id': test_event.id,
    #     })
    #     self.assertEqual(test_reg1.state, 'open', 'Event: auto_confirmation of registration failed')
    #     self.assertEqual(test_event.seats_reserved, 1, 'Event: wrong number of reserved seats after confirmed registration')
    #     test_reg2 = self.Registration.sudo(self.user_eventuser).create({
    #         'name': 'TestReg2',
    #         'event_id': test_event.id,
    #     })
    #     self.assertEqual(test_reg2.state, 'open', 'Event: auto_confirmation of registration failed')
    #     self.assertEqual(test_event.seats_reserved, 2, 'Event: wrong number of reserved seats after confirmed registration')

    #     # EventUser create registrations for this event: too much registrations
    #     with self.assertRaises(ValidationError):
    #         self.Registration.sudo(self.user_eventuser).create({
    #             'name': 'TestReg3',
    #             'event_id': test_event.id,
    #         })

    #     # EventUser validates registrations
    #     test_reg1.button_reg_close()
    #     self.assertEqual(test_reg1.state, 'done', 'Event: wrong state of attended registration')
    #     self.assertEqual(test_event.seats_used, 1, 'Event: incorrect number of attendees after closing registration')
    #     test_reg2.button_reg_close()
    #     self.assertEqual(test_reg1.state, 'done', 'Event: wrong state of attended registration')
    #     self.assertEqual(test_event.seats_used, 2, 'Event: incorrect number of attendees after closing registration')

    #     # EventUser closes the event
    #     test_event.button_done()

    #     # EventUser cancels -> not possible when having attendees
    #     with self.assertRaises(Warning):
    #         test_event.button_cancel()


    # @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    # def test_10_advanced_event_flow(self):
    #     """ Avanced event flow: no auto confirmation, manage minimum / maximum
    #     seats, ... """
    #     self.env['ir.values'].set_default('marketing.config.settings', 'auto_confirmation', False)

    #     # EventUser creates a new event: ok
    #     test_event = self.Event.sudo(self.user_eventmanager).create({
    #         'name': 'TestEvent',
    #         'date_begin': datetime.datetime.now() + relativedelta(days=-1),
    #         'date_end': datetime.datetime.now() + relativedelta(days=1),
    #         'seats_max': 10,
    #     })
    #     self.assertEqual(test_event.state, 'draft', 'Event: new event should be in draft state, no auto confirmation')
