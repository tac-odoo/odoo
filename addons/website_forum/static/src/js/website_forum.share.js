(function () {
    'use strict';

    var _t = openerp._t;
    var website = openerp.website;
    var qweb = openerp.qweb;
    website.add_template_file('/website_forum/static/src/xml/website_forum.share_templates.xml');

    website.forum_share = website.social_share.extend({
        init: function(template, element, social_list, hashtag_list){

            //Initialization
            this.template='website.'+template;
            this._super(element,social_list,hashtag_list);
        },

        renderElement: function() {
            // we now have multiple templates to choose from
            if (this.template == 'website.social_alert') {
                $('.row .question').before(qweb.render(this.template, {medias: this.social_list}));
            } else if (this.template == 'website.social_hover') {
                this.$el.append(qweb.render(this.template, {medias: this.social_list, id: this.target}));
                //we need to re-render the element on each hover; popover has the nasty habit of not hiding but completely removing its code from the page
                //so the binding is lost if we simply trigger on hover.
                this.element.popover({
                    'content': this.$el.html(),
                    'placement': 'bottom',
                    'container': this.element,
                    'html': true,
                    'trigger': 'manual',
                    'animation': false,
                }).popover("show")
                .on("mouseleave", function () {
                    var self = this;
                    setTimeout(function () {
                        if (!$(".popover:hover").length) {
                            $(self).popover("destroy")
                        }
                    }, 200);
                });
            } else {
                $('body').append(qweb.render(this.template, {medias: this.social_list}));
                $('#social_share_modal').modal('show');
            }
        },

    });

    // Display modal after new question/answer
    $(document.body).on('click', '.social_share_call', function() {
        var default_social_list = ['facebook','twitter', 'linkedin', 'google-plus']
        var hashtag_list = eval($(this).data('hashtag-list'));
        var social_list = _.intersection(eval($(this).data('social')) || default_social_list, default_social_list);
        var social_template = eval($(this).data('social-template'));

        var dataObject = {};
        dataObject_func('social_list', social_list);
        dataObject_func('hashtag_list', hashtag_list);
        dataObject_func('social_template', social_template);
        function dataObject_func(propertyName, propertyValue)
        {
            if(propertyValue) dataObject[propertyName] = propertyValue;
        };
        // Put the object into storage
        sessionStorage.setItem('social_share', JSON.stringify(dataObject));
    });

    // Retreive on sessionStorage when new content was submitted
    website.ready().done(function() {
        if(sessionStorage.getItem('social_share')){
            var dataObject = JSON.parse(sessionStorage.getItem('social_share'));
            new website.forum_share(
                'social_'+dataObject['social_template'],
                $(this),
                dataObject['social_list'],
                dataObject['hashtag_list']
            );
            sessionStorage.removeItem('social_share');
        }
    });

    website.ready().done(function() {
        if ($('.question').data('type')=="question") {
        var diff_date = Date.now()-Date.parse($('.question').data('last-update').split(' ')[0]);
        }
        var is_answered = !!$('.forum_answer').length;
        //If the question is older than 864*10e5 seconds (=10 days) and does'nt have an answer
        if (diff_date && diff_date > 864*10e5 && !is_answered) {
            var hashtag_list = ['question'];
            var social_list = ['facebook','twitter', 'linkedin', 'google-plus'];
            new website.forum_share('social_alert',$(this), social_list, hashtag_list);
            $('.share').on('click', $.proxy(updateDateWrite));
        }
        function updateDateWrite() {
            openerp.jsonRpc(window.location.pathname+'/bump', 'call', {});
        };
    });})();
