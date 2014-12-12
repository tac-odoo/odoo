/*global $, openerp, _, PDFJS */
$(document).ready(function () {
    "use strict";
    var website = openerp.website,
        _t = openerp._t;
    website.slide = website.slide || {};

    website.slide.PDFViewer_Launcher($('#PDFViewer'));
    $("timeago.timeago").each(function (index, el) {
        var datetime = $(el).attr('datetime'),
            datetime_obj = openerp.str_to_datetime(datetime),
            // if presentation 7 days, 24 hours, 60 min, 60 second, 1000 millis old(one week)
            // then return fix formate string else timeago
            display_str = "";
        if (datetime_obj && new Date().getTime() - datetime_obj.getTime() > 7 * 24 * 60 * 60 * 1000) {
            display_str = datetime_obj.toDateString();
        } else {
            display_str = $.timeago(datetime_obj);
        }
        $(el).text(display_str);
    });

    $('.slide-container').on('click', function (ev) {
        window.location = $(this).find("a").attr("href");
    });
    $('.slide-tabs').on('click', function (ev) {
        ev.preventDefault();
        window.location = $(this).attr('href');
    });

    $('.slide-like, .slide-unlike').on('click', function (ev) {
        ev.preventDefault();
        var slide_id = $(this).attr('slide-id'),
            user_id = $(this).attr('user-id'),
            $link = $(ev.currentTarget);
        if (localStorage['slide_vote_' + slide_id] !== user_id) {
            openerp.jsonRpc($link.data('href'), 'call', {}).then(function (data) {
                $($link.data('count-el')).text(data);
            });
            localStorage['slide_vote_' + slide_id] = user_id;
        } else {
            var $warning = $('<div class="alert alert-danger alert-dismissable oe_forum_alert" id="vote_alert">' +
                '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>' +
                _t('You have already voted for this slide') +
                '</div>');
            if (!$link.parent().find('#vote_alert').length) {
                $link.parent().append($warning);
            }
        }
    });
    $('.upload').on('click', function (ev) {
        var channel_id = $(this).attr('channel_id');
        new website.slide.Dialog(this, channel_id).appendTo(document.body);
    });

    $(document).keydown(function (ev) {
        if (ev.keyCode === 37) {
            website.slide.PDFViewer_inst.previous(ev);
        }
        if (ev.keyCode === 39) {
            website.slide.PDFViewer_inst.next(ev);
        }
    });

    website.slide.modifyembedcode = function (currentVal) {
        var $embed_input = $('.slide_embed_code'),
            slide_embed_code = $embed_input.val(),
            tmp_embed_code = slide_embed_code.replace(/(page=).*?([^\d]+)/, '$1' + currentVal + '$2');
        $embed_input.val(tmp_embed_code);
    };

    $('.embed-page-counter').on('change', function (e) {
        e.preventDefault();
        var currentVal = parseInt($(this).val());
        var maxval = parseInt($('#page_count').text());
        if (currentVal > 0 && currentVal <= maxval) {
            website.slide.modifyembedcode(currentVal);
        } else {
            $(this).val(1);
            website.slide.modifyembedcode(1);
        }
    });
    $('.share-toggle-option').on('click', function (ev) {
        ev.preventDefault();
        var toggleDiv = $(this).data('slide-share');
        $(toggleDiv).slideToggle();
    });


    if ($('div#statistic').length) {
        var socialgatter = function (app_url, url, callback) {
            $.ajax({
                url: app_url + url,
                dataType: 'jsonp',
                success: callback
            });
        };
        var current_url = window.location.origin + window.location.pathname;
        socialgatter('http://www.linkedin.com/countserv/count/share?url=', current_url, function (data) {
            $('#linkedin-badge').text(data.count || 0);
            $('#total-share').text(parseInt($('#total-share').text()) + parseInt($('#linkedin-badge').text()));
        });
        socialgatter('http://cdn.api.twitter.com/1/urls/count.json?url=', current_url, function (data) {
            $('#twitter-badge').text(data.count || 0);
            $('#total-share').text(parseInt($('#total-share').text()) + parseInt($('#twitter-badge').text()));
        });
        socialgatter('http://graph.facebook.com/?id=', current_url, function (data) {
            $('#facebook-badge').text(data.shares || 0);
            $('#total-share').text(parseInt($('#total-share').text()) + parseInt($('#facebook-badge').text()));
        });

        $.ajax({
            url: 'https://clients6.google.com/rpc',
            type: "POST",
            dataType: 'json',
            contentType: 'application/json',
            data: JSON.stringify([{
                "method": "pos.plusones.get",
                "id": "p",
                "params": {
                    "nolog": true,
                    "id": current_url,
                    "source": "widget",
                    "userId": "@viewer",
                    "groupId": "@self"
                },
                "jsonrpc": "2.0",
                "key": "AIzaSyCFi7q20yMDmAZ9Qxmiu-zHPnxvIX0u2zM",
                "apiVersion": "v1"
            }]),
            success: function (data) {
                $('#google-badge').text(data[0].result.metadata.globalCounts.count || 0);
                $('#total-share').text(parseInt($('#total-share').text()) + parseInt($('#google-badge').text()));
            }
        });
    }

    $('.send-share-email').on('click', function () {
        var $input = $(this).parent().prev(':input');
        if (!$input.val() || !$input[0].checkValidity()) {
            $input.closest('.form-group').addClass('has-error');
            $input.focus();
            return;
        }
        $input.closest('.form-group').removeClass('has-error');
        $(this).button('loading');
        openerp.jsonRpc('/slides/' + $(this).attr('slide-id') + '/send_share_email', 'call', {
            email: $input.val()
        }).then(function () {
            $input.closest('.form-group').html($('<div class="alert alert-info" role="alert"><strong>Thank you!</strong> Mail has been sent.</div>'));
        });
    });

});
