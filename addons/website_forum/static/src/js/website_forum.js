
    openerp.website.if_dom_contains('.website_forum', function () {
        var _t = openerp._t;
        $("[data-toggle='popover']").popover();
        $('.karma_required').on('click', function (ev) {
            var karma = $(ev.currentTarget).data('karma');
            if (karma) {
                ev.preventDefault();
                var $warning = $('<div class="alert alert-danger alert-dismissable oe_forum_alert" id="karma_alert">'+
                    '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                    karma + _t(' karma is required to perform this action. You can earn karma by having '+
                            'your answers upvoted by the community.')+
                            '</div>');
                var vote_alert = $(ev.currentTarget).parent().find("#vote_alert");
                if (vote_alert.length == 0) {
                    $(ev.currentTarget).parent().append($warning);
                }
            }
        });

        $('.vote_up,.vote_down').not('.karma_required').on('click', function (ev) {
            ev.preventDefault();
            var $link = $(ev.currentTarget);
            openerp.jsonRpc($link.data('href'), 'call', {})
                .then(function (data) {
                    if (data['error']){
                        if (data['error'] == 'own_post'){
                            var $warning = $('<div class="alert alert-danger alert-dismissable oe_forum_alert" id="vote_alert">'+
                                '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                                _t('Sorry, you cannot vote for your own posts')+
                                '</div>');
                        } else if (data['error'] == 'anonymous_user'){
                            var $warning = $('<div class="alert alert-danger alert-dismissable oe_forum_alert" id="vote_alert">'+
                                '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                                _t('Sorry you must be logged to vote')+
                                '</div>');
                        }
                        vote_alert = $link.parent().find("#vote_alert");
                        if (vote_alert.length == 0) {
                            $link.parent().append($warning);
                        }
                    } else {
                        $link.parent().find("#vote_count").html(data['vote_count']);
                        if (data['user_vote'] == 0) {
                            $link.parent().find(".text-success").removeClass("text-success");
                            $link.parent().find(".text-warning").removeClass("text-warning");
                        } else {
                            if (data['user_vote'] == 1) {
                                $link.addClass("text-success");
                            } else {
                                $link.addClass("text-warning");
                            }
                        }
                    }
                });
        });

        $('.accept_answer').not('.karma_required').on('click', function (ev) {
            ev.preventDefault();
            var $link = $(ev.currentTarget);
            openerp.jsonRpc($link.data('href'), 'call', {}).then(function (data) {
                if (data['error']) {
                    if (data['error'] == 'anonymous_user') {
                        var $warning = $('<div class="alert alert-danger alert-dismissable" id="correct_answer_alert" style="position:absolute; margin-top: -30px; margin-left: 90px;">'+
                            '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                            _t('Sorry, anonymous users cannot choose correct answer.')+
                            '</div>');
                    }
                    correct_answer_alert = $link.parent().find("#correct_answer_alert");
                    if (correct_answer_alert.length == 0) {
                        $link.parent().append($warning);
                    }
                } else {
                    if (data) {
                        $(".oe_answer_true").addClass('oe_answer_false').removeClass("oe_answer_true");
                        $link.addClass("oe_answer_true").removeClass('oe_answer_false');
                    } else {
                        $link.removeClass("oe_answer_true").addClass('oe_answer_false');
                    }
                }
            });
        });

        $('.favourite_question').on('click', function (ev) {
            ev.preventDefault();
            var $link = $(ev.currentTarget);
            openerp.jsonRpc($link.data('href'), 'call', {}).then(function (data) {
                if (data) {
                    $link.addClass("forum_favourite_question")
                } else {
                    $link.removeClass("forum_favourite_question")
                }
            });
        });

        $('.comment_delete').on('click', function (ev) {
            ev.preventDefault();
            var $link = $(ev.currentTarget);
            openerp.jsonRpc($link.data('href'), 'call', {}).then(function (data) {
                $link.parents('.comment').first().remove();
            });
        });

        $('.notification_close').on('click', function (ev) {
            ev.preventDefault();
            var $link = $(ev.currentTarget);
            openerp.jsonRpc("/forum/notification_read", 'call', {
                'notification_id': $link.attr("id")});
        });

        $('.send_validation_email').on('click', function (ev) {
            ev.preventDefault();
            var $link = $(ev.currentTarget);
            openerp.jsonRpc("/forum/send_validation_email", 'call', {
                'forum_id': $link.attr('forum-id'),
            }).then(function (data) {
                if (data) {
                    $('button.validation_email_close').click();
                }
            });
        });

        $('.validated_email_close').on('click', function (ev) {
            openerp.jsonRpc("/forum/validate_email/close", 'call', {});
        });
        var forum_login = _.string.sprintf('%s/web?redirect=%s',
            window.location.origin, escape(window.location.href));
        $('.forum_register_url').attr('href',forum_login);


        $('.js_close_intro').on('click', function (ev) {
            ev.preventDefault();
            document.cookie = "no_introduction_message = false";
            $('.forum_intro').slideUp();
            return true;
        });

        $('.link_url').on('change', function (ev) {
            ev.preventDefault();
            var $link = $(ev.currentTarget);
            var $form = $('form.post_link');
            var url = $link.attr("value");
            $form.find("button#btn_post_your_article").prop('disabled',true);
            if ($link.attr("value").search("^http(s?)://.*")) {
                url = 'http://'+url;
            } 
            openerp.jsonRpc("/forum/get_url_title", 'call', {'url': url}).then(function (data) {
                if(data){
                    $form.find("input[name='post_name']").val(data);
                    $form.find("button#btn_post_your_article").prop('disabled',false);
                    $link.attr("value",url);
                    $('.invalid_url_warning').remove();
                }else{
                    var $warning = $('<div class="alert alert-danger alert-dismissable invalid_url_warning" style="position:absolute; margin-top: -180px; margin-left: 90px;">'+
                        '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                        _t('Please enter valid URl.')+
                        '</div>');
                    if($('.invalid_url_warning').length == 0){
                        $link.parent().append($warning);
                    }
                }
            });
        });

        $('input.js_select2').select2({
            tags: true,
            tokenSeparators: [",", " ", "_"],
            maximumInputLength: 35,
            minimumInputLength: 2,
            maximumSelectionSize: 5,
            lastsearch: [],
            createSearchChoice: function (term) {
                if ($(lastsearch).filter(function () { return this.text.localeCompare(term) === 0;}).length === 0) {
                    //check Karma
                    if (parseInt($("#karma").val()) >= parseInt($("#karma_retag").val())) {
                        return {
                            id: "_" + $.trim(term),
                            text: $.trim(term) + ' *',
                            isNew: true,
                        };
                    }
                }
            },
            formatResult: function(term) {
                if (term.isNew) {
                    return '<span class="label label-primary">New</span> ' + _.escape(term.text);
                }
                else {
                    return _.escape(term.text);
                }
            },
            ajax: {
                url: '/forum/get_tags',
                dataType: 'json',
                data: function(term, page) {
                    return {
                        q: term,
                        l: 50
                    };
                },
                results: function(data, page) {
                    var ret = [];
                    _.each(data, function(x) {
                        ret.push({ id: x.id, text: x.name, isNew: false });
                    });
                    lastsearch = ret;
                    return { results: ret };
                }
            },

            // Take default tags from the input value
            initSelection: function (element, callback) {
                var data = [];
                _.each(element.data('init-value'), function(x) {
                    data.push({ id: x.id, text: x.name, isNew: false });
                });
                element.val('');
                callback(data);
            },
        });

        if ($('textarea.load_editor').length) {
            $('textarea.load_editor').each(function () {
                if (this['id']) {
                    CKEDITOR.replace(this['id']).on('instanceReady', CKEDITORLoadComplete);
                }
            });
        }
        
        function CKEDITORLoadComplete(){
            "use strict";
            $('.cke_button__link').attr('onclick','website_forum_IsKarmaValid(33,30)');
            $('.cke_button__unlink').attr('onclick','website_forum_IsKarmaValid(37,30)');
            $('.cke_button__image').attr('onclick','website_forum_IsKarmaValid(41,30)');
        }
    });

   function website_forum_IsKarmaValid(eventNumber, minKarma){
        "use strict";
        if(parseInt($("#karma").val()) >= minKarma){
            CKEDITOR.tools.callFunction(eventNumber, this);
            return false;
        } else {
            alert("Sorry you need more than " + minKarma + " Karma.");
        }
    }
