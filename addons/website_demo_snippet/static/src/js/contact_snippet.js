(function () {
    'use strict';

    var website = openerp.website;

    website.snippet.animationRegistry.contact_snippet = website.snippet.Animation.extend({
        selector: ".js_contact",
        start: function (editable_mode) {
            var self = this;
            if (!editable_mode) {
                this.$target.find('.js_contact_btn').on('click', function (event) {
                    event.preventDefault();
                    self.on_click(event);
                });
            }
            return this._super.apply(this, arguments);
        },
        on_click: function (event) {
            var self = this;
            var section_id = this.$(".js_contact_section_id").val();
            var email = this.$(".js_contact_email").val();
            var question = this.$(".js_contact_question").val();
            if (!email.length || ! email.match(/.+@.+/)) {
                this.$target.addClass('has-error');
                return false;
            }
            if (!question.length) {
                this.$target.addClass('has-error');
                return false;
            }
            this.$target.removeClass('has-error');
            return openerp.jsonRpc('/crm/contact_short', 'call', {
                'section_id': +section_id,
                'email': email,
                'question': question,
            }).then(function (result) {
                if (result) {
                    self.$('.js_contact_thanks').removeClass('hidden');
                    self.$('.js_contact_form').addClass('hidden');
                }
            });
        },
    });

})();
