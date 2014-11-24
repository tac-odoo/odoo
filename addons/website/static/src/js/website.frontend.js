(function () {
    'use strict';

    var _t = openerp._t,
    website = openerp.website;
    website.add_template_file('/website/static/src/xml/website.frontend.xml');

    website.social_share = openerp.Widget.extend({
        /*
            element:Element to bind popover
            social_list: List of social media avialable
            config: To config social plugin (width, height)
        */
        // template: 'website.social_share',
        init: function(template, element, social_list, options){
            //Initialization
            this._super.apply(this, arguments);
            var self = this;
            this.template = template || 'website.social_share';
            this.element = element;
            this.social_list = social_list;
            this.options = options
            this.renderElement();
            this.bind_events();
        },
        // set_value: function(type, description, title, url, image){   
        //     console.log("call set_value");
        // },
        bind_events: function() {
            var self = this;
            $('.facebook').on('click', $.proxy(self.renderSocial, self, 'facebook'));
            $('.twitter').on('click', $.proxy(self.renderSocial, self, 'twitter'));
            $('.linkedin').on('click', $.proxy(self.renderSocial, self, 'linkedin'));
            $('.google-plus').on('click', $.proxy(self.renderSocial, self, 'google-plus'));
        },
        renderElement: function() {
            var self = this;
            if (this.template == 'website.social_share_dialog'){
                openerp.qweb.render(this.template, {medias: this.social_list})
            }
            else{
                this.$el.append(openerp.qweb.render(this.template, {medias: this.social_list}));
                // this.$el.append(openerp.qweb.render(this.template, {medias: this.social_list, id: this.target}));
                console.log("calll renderElement",this.element, this.$el);

                self.element.popover({
                    'content': self.$el.html(),
                    'placement': 'bottom',
                    'container': 'body',
                    'html': true,
                    'trigger': 'manual',
                    'animation': false,
                }).popover("show")
                .on("mouseleave", function () {
                    var _this = this;
                    setTimeout(function () {
                        if (!$(".popover:hover").length) {
                            $(_this).popover("hide")
                        }
                    }, 100);
                });
                $('.popover').on("mouseleave", function () {
                    $(this).hide();
                });
                // openerp.qweb.add_template('website.opengraph_tags');
                openerp.qweb.render('website.set_meta_tags', {});
            }
        },
        renderSocial: function(social){
            var url = this.element.data('url') || window.location.href.split(/[?#]/)[0]; // get current url without query string if not pass 
            var text_to_share = this.element.data('share_content');
            console.log("url", url, text_to_share, social);
            var social_network = {
                'facebook':'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(url),
                'twitter': 'https://twitter.com/intent/tweet?original_referer=' + encodeURIComponent(url) + '&amp;text=' + encodeURIComponent(text_to_share + ' - ' + url),
                'linkedin': 'https://www.linkedin.com/shareArticle?mini=true&url=' + encodeURIComponent(url) + '&title=' + encodeURIComponent(text_to_share) + '&summary=' + encodeURIComponent(this.element.data('description')),
                'google-plus': 'https://plus.google.com/share?url=' + encodeURIComponent(url)
            };
            if (_.contains(_.keys(social_network), social)){
                var window_height = 500, window_width = 500, left = (screen.width/2)-(window_width/2), top = (screen.height/2)-(window_height/2);
                window.open(social_network[social], '', 'menubar=no, toolbar=no, resizable=yes, scrollbar=yes, height=' + window_height + ',width=' + window_width + ', top=' + top + ', left=' + left);
            }
        },
    });

    website.ready().done(function() {
        $(document.body).on('hover', 'a.social_share', function() {
            var self = $(this);
            var default_social_list = ['facebook','twitter', 'linkedin', 'google-plus']
            var social_list = _.intersection(eval($(this).data('social')) || default_social_list, default_social_list);
            var default_config = {'default_social': {'width':500, 'height':500}}
            var config = _.defaults(default_config, {'default_social': { 'height':100}});

            console.log(config);
            new website.social_share(
                        'website.social_share',
                        $(this),
                        social_list,
                        {'facebook': {'width':100, 'height':100}}
                    );
            // social_share_obj.set_value('type', 'description', 'title', 'url', 'image');
        });
        $(document.body).on('hover', '.social_share_call', function() {
            var self = $(this);
            var default_social_list = ['facebook','twitter', 'linkedin', 'google-plus']
            var social_list = _.intersection(eval($(this).data('social')) || default_social_list, default_social_list);

            // var url = self.data('url') || window.location.href.split(/[?#]/)[0];
            // var text_to_share = self.data('share_content');
            // var description =  self.data('description');
            var dataObject = {};
            dataObject_func('social_list', social_list);
            dataObject_func('url', self.data('url'));
            dataObject_func('share_content', self.data('share_content'));
            dataObject_func('description', self.data('description'));
            function dataObject_func(propertyName, propertyValue)
            {
                if(propertyValue) dataObject[propertyName] = propertyValue;
            };
            console.log("call social_share_call ", localStorage.getItem('social_share'));

            // Put the object into storage
            localStorage.setItem('social_share', JSON.stringify(dataObject));

        });
    });
    $(document).ready(function() {
        if(localStorage.getItem('social_share')){
            // Retrieve the object from storage
            var dataObject = JSON.parse(localStorage.getItem('social_share'));
            new website.social_share(
                        'website.social_share_dialog',
                        $(this),
                        dataObject['social_list'],
                        {'facebook': {'width':100, 'height':100}}
                    );
            localStorage.removeItem('social_share');
            // console.log('retrievedObject: ', JSON.parse(dataObject));
        }
    });
})();