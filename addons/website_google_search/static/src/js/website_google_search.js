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
            var dialog = new website.google_search.ConfigDialog(this.editor);
            dialog.appendTo(document.body);
            /**
            website.prompt({
                'id': "google_search_cx",
                'window_title': _t("Google Search Configuration"),
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
            */
        },
    });

    website.add_template_file('/website_google_search/static/src/xml/website_google_search.xml');

    website.google_search = {};

    website.google_search.ConfigDialog = website.editor.Dialog.extend({
        template: 'website.google_search.dialog.configuration',
        save: function () {
            debugger;
        },
        cancel: function () {
            debugger;
        },
    });

})();
