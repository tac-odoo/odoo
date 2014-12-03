(function() {
    'use strict';
    var website = openerp.website,
        qweb = openerp.qweb;

    if (!website.snippet) website.snippet = {};
    website.snippet.animationRegistry.banner = website.snippet.Animation.extend({
        selector: ".banner_popup",
        start: function (editable_mode) {
            var self = this;
            self.redirect_url = false;
            var popupcontent = self.$target.find(".popup_content").empty();

            openerp.jsonRpc('/website_popup/get_content', 'call', {
                list_id: self.$target.data('list-id'),
            }).then(function (data) {
                $(data.content).appendTo(popupcontent)
                self.redirect_url = data.redirect_url
            });

            if (!editable_mode) {
                if (!self.$target[0].isContentEditable) {
                    $(document).on('mouseleave', _.bind(self.show_banner, self));
                } else { $(document).off('mouseleave'); }

                self.$target.find('.popup_subscribe_btn').on('click', function (event) {
                    event.preventDefault();
                    self.on_click_subscribe();
                });
            }
        },
        on_click_subscribe: function () {
            var self = this;
            var $email = self.$target.find(".popup_subscribe_email:visible");

            if ($email.length && !$email.val().match(/.+@.+/)) {
                self.$target.addClass('has-error');
                return false;
            }
            self.$target.removeClass('has-error');

            openerp.jsonRpc('/website_mass_mailing/subscribe', 'call', {
                'list_id': self.$target.data('list-id'),
                'email': $email.length ? $email.val() : false
            }).then(function (subscribe) {
                self.$target.find('#banner_popup').modal('hide');
                if (self.redirect_url) window.location.href = self.redirect_url
            });
        },
        show_banner: function() {
            var self = this;
            if (!openerp.get_cookie("popup-banner-"+ self.$target.data('list-id')) && self.$target) {
                self.$target.find('#banner_popup').modal('show');
                document.cookie = "popup-banner-"+ self.$target.data('list-id') +"=" + true + ";path=/"
            }
        }
    });

})();

