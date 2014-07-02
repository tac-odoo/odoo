(function () {
    'use strict';

    var website = openerp.website;
    var _t = openerp._t;

    website.snippet.options['google-search'] = website.snippet.Option.extend({
        onFocus: function () {
            this._super();
            this.$overlay.find('.oe_snippet_clone').addClass('hidden');
        },
        on_remove: function () {
            var self = this;
            var context = website.get_context();
            openerp.jsonRpc('/web/dataset/call_kw', 'call', {
                model: 'website',
                method: 'write',
                args: [context.website_id, {
                    'google_search_published': false,
                    'google_search_cx': '',
                }],
                kwargs: {
                    context: context
                },
            });
            return this._super.apply(this, arguments);
        },
        drop_and_build_snippet: function () {
            var self = this;
            var context = website.get_context();
            website.prompt({
                'id': "google_search_cx",
                'window_title': _t("Google Search Information"),
                'input': _t("Google Search cx"),
            }).then(function (val, field, $dialog) {
                openerp.jsonRpc('/web/dataset/call_kw', 'call', {
                    model: 'website',
                    method: 'write',
                    args: [context.website_id, {
                        'google_search_cx': val,
                        'google_search_published': true,
                    }],
                    kwargs: {
                        context: context
                    },
                });
            }, function () {
                openerp.jsonRpc('/web/dataset/call_kw', 'call', {
                    model: 'website',
                    method: 'write',
                    args: [context.website_id, {
                        'google_search_published': true,
                    }],
                    kwargs: {
                        context: context
                    },
                });
            });
        },
    });

})();
