function open_share_dialog(social_network) {
    var url, url_facebook, sharing_url, text_to_share, $share_dialog = $("#share_dialog_box");
    if ($("#question_name_ask").length === 0) {
        url = location.origin + location.pathname;
        url_facebook = url + '/answer';
        text_to_share = openerp._t("Just answered #odoo question " + url + " " + $("#question_name").text());
    } else {
        url = location.origin + $("#share_dialog_box").data("url");
        url_facebook = url;
        text_to_share = openerp._t($("#question_name_ask").val() + " #odoo #help " + url);
    }
    if ((social_network === 'twitter') && ($share_dialog.data('twitter') === false)) {
        sharing_url = 'https://twitter.com/intent/tweet?original_referer=' + encodeURIComponent(url) + '&amp;text=' + encodeURIComponent(text_to_share);
        $share_dialog.data("twitter", true);
        $(".twitter").hover( function() {
            $(this).removeClass("fa-twitter").addClass("fa-check");
        }, function() {
            $(this).removeClass("fa-check").addClass("fa-twitter");
        });
    } else if ((social_network === 'linked-in') && ($share_dialog.data('linked_in') === false)) {
        sharing_url = 'https://www.linkedin.com/shareArticle?mini=true&url=' + encodeURIComponent(url) + '&title=' + encodeURIComponent(text_to_share) + '&summary=Odoo Forum&source=Odoo forum';
        $share_dialog.data("linked_in", true);
        $(".linkedin").hover( function() {
            $(this).removeClass("fa-linkedin").addClass("fa-check");
        }, function () {
            $(this).removeClass("fa-check").addClass("fa-linkedin");
        });
    } else if ((social_network === 'facebook') && ($share_dialog.data('facebook') === false)) {
        sharing_url = 'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(url_facebook);
        $share_dialog.data("facebook", true);
        $(".facebook").hover( function() {
            $(this).removeClass("fa-facebook").addClass("fa-check");
        }, function() {
            $(this).removeClass("fa-check").addClass("fa-facebook");
        });
    } else {
        return false;
    }
    window.open(sharing_url, '', 'menubar=no, toolbar=no, resizable=yes, scrollbar=yes, height=600,width=600');
    return false;
}

function decode_like_post(values_serialize) {
    var i, decode_values = {};
    for (i = 0; i < values_serialize.length; i++) {
        decode_values[values_serialize[i].name] = values_serialize[i].value;
    }
    return decode_values;
}

function redirect_user($form, isQuestion) {
    var path = $form.data("target"), title, body, redirect_url, vals, Post = openerp.website.session.model('forum.post');
    openerp.jsonRpc(path,  "call", decode_like_post($form.serializeArray()))
        .then(function (result) {
            var forum_id = result.forum_id;
            if (isQuestion) {
                title = openerp._t("Thanks for posting your Question !");
                body = openerp._t("On average " + result.stat_data[forum_id].percentage + "% of the questions shared on social networks get an answer within " + result.stat_data[forum_id].average + " hours and questions shared on two social networks have " + result.stat_data[forum_id].probability + "% more chance to get an answer than not shared questions");
            } else {
                title = openerp._t('Thanks for posting your Answer !');
                body = openerp._t("By Sharing your answer, you will get " + result.karma + " additional karma points if your answer is selected as the right one.<a href='/forum/" + forum_id + "/faq'>See what you can do with karma.</a>");
            }
            redirect_url = "/forum/" + result.forum_id + "/question/" + result.question_id;
            $(".modal-title").text(title);
            $(".modal-body").prepend(body);
            $("#share_dialog_box").data({
                "twitter" : false,
                "facebook" : false,
                "linked_in" : false,
                "url" : redirect_url,
            }).on('hidden.bs.modal', function () {
                if (result.answer_id) {
                    vals = [result.answer_id]
                } else {
                    vals = [result.question_id];
                }
                vals.push({
                    'on_twitter' : $(this).data("twitter"),
                    'on_facebook' : $(this).data("facebook"),
                    'on_linked_in' : $(this).data("linked_in"),
                });
                Post.call('write', vals).then(function (data) {
                    window.location = redirect_url;
                });
            }).modal("show");
        });
}

$(document).ready(function () {

    $(".tag_text").submit(function(event) {
        event.preventDefault();
        CKEDITOR.instances['content'].destroy();
        redirect_user($(this), true);
    });

    $("#forum_post_answer").submit(function(event) {
        event.preventDefault();
        CKEDITOR.instances['content'].destroy();
        redirect_user($(this), false);
    });

    $('.karma_required').on('click', function (ev) {
        var karma = $(ev.currentTarget).data('karma');
        if (karma) {
            ev.preventDefault();
            var $warning = $('<div class="alert alert-danger alert-dismissable oe_forum_alert" id="karma_alert">'+
                '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                karma + ' karma is required to perform this action. You can earn karma by answering questions or having '+
                'your answers upvoted by the community.</div>');
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
                            'Sorry, you cannot vote for your own posts'+
                            '</div>');
                    } else if (data['error'] == 'anonymous_user'){
                        var $warning = $('<div class="alert alert-danger alert-dismissable oe_forum_alert" id="vote_alert">'+
                            '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                            'Sorry you must be logged to vote'+
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
        return true;
    });

    $('.accept_answer').not('.karma_required').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        openerp.jsonRpc($link.data('href'), 'call', {}).then(function (data) {
            if (data['error']) {
                if (data['error'] == 'anonymous_user') {
                    var $warning = $('<div class="alert alert-danger alert-dismissable" id="correct_answer_alert" style="position:absolute; margin-top: -30px; margin-left: 90px;">'+
                        '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                        'Sorry, anonymous users cannot choose correct answer.'+
                        '</div>');
                }
                correct_answer_alert = $link.parent().find("#correct_answer_alert");
                if (correct_answer_alert.length == 0) {
                    $link.parent().append($warning);
                }
            } else {
                if (data) {
                    $link.addClass("oe_answer_true").removeClass('oe_answer_false');
                } else {
                    $link.removeClass("oe_answer_true").addClass('oe_answer_false');
                }
            }
        });
        return true;
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
        return true;
    });

    $('.comment_delete').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        openerp.jsonRpc($link.data('href'), 'call', {}).then(function (data) {
            $link.parents('.comment').first().remove();
        });
        return true;
    });

    $('.notification_close').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        openerp.jsonRpc("/forum/notification_read", 'call', {
            'notification_id': $link.attr("id")})
        return true;
    });

    if($('input.load_tags').length){
        var tags = $("input.load_tags").val();
        $("input.load_tags").val("");
        set_tags(tags);
    };

    function set_tags(tags) {
        $("input.load_tags").textext({
            plugins: 'tags focus autocomplete ajax',
            tagsItems: tags.split(","),
            //Note: The following list of keyboard keys is added. All entries are default except {32 : 'whitespace!'}.
            keys: {8: 'backspace', 9: 'tab', 13: 'enter!', 27: 'escape!', 37: 'left', 38: 'up!', 39: 'right',
                40: 'down!', 46: 'delete', 108: 'numpadEnter', 32: 'whitespace!'},
            ajax: {
                url: '/forum/get_tags',
                dataType: 'json',
                cacheResults: true
            }
        });
        // Adds: create tags on space + blur
        $("input.load_tags").on('whitespaceKeyDown blur', function () {
            $(this).textext()[0].tags().addTags([ $(this).val() ]);
            $(this).val("");
        });
        $("input.load_tags").on('isTagAllowed', function(e, data) {
            if (_.indexOf($(this).textext()[0].tags()._formData, data.tag) != -1) {
                data.result = false;
            }
        });
    }

    if ($('textarea.load_editor').length) {
        var editor = CKEDITOR.instances['content'];
        editor.on('instanceReady', CKEDITORLoadComplete);
    }
});

function IsKarmaValid(eventNumber,minKarma){
    "use strict";
    if(parseInt($("#karma").val()) >= minKarma){
        CKEDITOR.tools.callFunction(eventNumber,this);
        return false;
    } else {
        alert("Sorry you need more than " + minKarma + " Karma.");
    }
}

function CKEDITORLoadComplete(){
    "use strict";
    $('.cke_button__link').attr('onclick','IsKarmaValid(33,30)');
    $('.cke_button__unlink').attr('onclick','IsKarmaValid(37,30)');
    $('.cke_button__image').attr('onclick','IsKarmaValid(41,30)');
}
