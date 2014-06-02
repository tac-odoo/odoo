(function () {
    'use strict';

    var website = openerp.website;
    var _t = openerp._t;

    website.snippet.options.contact_snippet = website.snippet.Option.extend({
        on_prompt: function () {
            var self = this;
            return website.prompt({
                id: "editor_new_contact_snippet",
                window_title: _t("Add a Contact Snippet"),
                select: _t("Sales Team"),
                init: function (field) {
                    return website.session.model('crm.case.section')
                            .call('name_search', ['', []], { context: website.get_context() });
                },
            }).then(function (sales_team_id) {
                self.$target.find('.js_contact_section_id').attr("value", sales_team_id);
            });
        },
        start : function () {
            var self = this;
            this.$el.find(".js_contact_sales_team").on("click", _.bind(this.on_prompt, this));
            this._super();
        },
    });
})();


