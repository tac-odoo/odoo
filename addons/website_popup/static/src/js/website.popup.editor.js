(function () {
    'use strict';
    var website = openerp.website;
    var _t = openerp._t;

    website.snippet.options.banner_popup = website.snippet.Option.extend({
        select_mailing_list: function (type, value) {
            var self = this;
            if (type !== "click") return;
            return website.prompt({
                id: "editor_new_mailing_list_subscribe_popup",
                window_title: _t("Add a Newsletter Subscribe Popup"),
                select: _t("Newsletter"),
                init: function (field) {
                    return website.session.model('mail.mass_mailing.list')
                            .call('name_search', ['', []]);
                },
            }).then(function (mailing_list_id) {
                self.$target.attr("data-list-id", mailing_list_id);
            });
        },
        drop_and_build_snippet: function() {
            var self = this;
            this._super();
            this.select_mailing_list('click').fail(function () {
                self.editor.on_remove();
            });
        },
    });

    website.EditorBar.include({
            edit: function () {
                var self = this;
                this._super();
                $('body').on('click','#edit_dialog',_.bind(this.edit_dialog, self.rte.editor));
            },
            edit_dialog : function() {
                var target = $('#wrapwrap').find('.banner_popup').data('list-id')
                if (target) window.location.href = '/web?#id=' + target + '&view_type=form&model=mail.mass_mailing.list'
            },
        });
})();
