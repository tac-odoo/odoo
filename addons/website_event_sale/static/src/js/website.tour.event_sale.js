(function () {
    'use strict';

    var website = openerp.website;

    website.Tour.register({
        id:   'event_buy_tickets',
        name: "Try to buy tickets for event",
        path: '/event',
        mode: 'test',
        steps: [
            {
                title:     "select event",
                element:   'a[href*="/event"]:contains("Conference on Business Applications"):first',
            },
            {
                waitNot:   'a[href*="/event"]:contains("Conference on Business Applications")',
                title:     "select 1 Standard ticket",
                element:   'select:eq(0)',
                sampleText: '1',
            },
            {
                title:     "select 1 VIP ticket",
                waitFor:   'select:eq(0) option:contains(1):selected',
                element:   'select:eq(1)',
                sampleText: '1',
            },
            {
                title:     "Select Attendees and Order",
                waitFor:   'select:eq(1) option:contains(1):selected',
                element:   '.btn-primary:contains("Select Attendees and Order")',
            },
            {
                title:     "Fill attendees details",
                waitFor:   '#top_menu .my_cart_quantity:contains(2)',
                element:   'form[action="/event/cart/update?event_id=3"] .btn:contains("Order Now")',
                autoComplete: function (tour) {
                    if ($("input[name='attendee-name-4-1']").val() === "")
                        $("input[name='attendee-name-4-1']").val("StandardAttendee1");
                    if ($("input[name='attendee-email-4-1']").val() === "")
                        $("input[name='attendee-email-4-1']").val("standardattende1@eventoptenerp.com");
                    if ($("input[name='attendee-name-5-1']").val() === "")
                        $("input[name='attendee-name-5-1']").val("VIPAttendee1");
                    if ($("input[name='attendee-email-5-1']").val() === "")
                        $("input[name='attendee-email-5-1']").val("vipattende1@eventoptenerp.com");
                },
            },
            {
                title:     "Complete checkout",
                element:   'form[action="/shop/confirm_order"] .btn:contains("Confirm")',
                autoComplete: function (tour) {
                    if ($("input[name='name']").val() === "")
                        $("input[name='name']").val("website_sale-test-shoptest");
                    if ($("input[name='email']").val() === "")
                        $("input[name='email']").val("website_event_sale_test_shoptest@websiteeventsaletest.optenerp.com");
                    $("input[name='phone']").val("123");
                    $("input[name='street']").val("123");
                    $("input[name='city']").val("123");
                    $("input[name='zip']").val("123");
                    $("select[name='country_id']").val("21");
                },
            },
            {
                title:     "select payment",
                element:   '#payment_method label:has(img[title="Wire Transfer"]) input',
            },
            {
                title:     "Pay Now",
                waitFor:   '#payment_method label:has(input:checked):has(img[title="Wire Transfer"])',
                element:   '.oe_sale_acquirer_button .btn[name="submit"]:visible',
            },
            {
                title:     "finish",
                waitFor:   '.oe_website_sale:contains("Thank you for your order")',
            }
        ]
    });

}());
