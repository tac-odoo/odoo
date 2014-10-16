$(document).ready(function () {
    if ($('.website_forum').length){
        if( $("#karmagraph").length) {
            var data = [
                          {
                              key: "Cumulative Return",
                              values: [
                                          {
                                              "label" : "2014-04-01" ,
                                              "value" : 29
                                          } ,
                                          {
                                              "label" : "2014-05-01" ,
                                              "value" : 0
                                          } ,
                                          {
                                              "label" : "2014-06-01" ,
                                              "value" : 32
                                          } ,
                                          {
                                              "label" : "2014-06-15" ,
                                              "value" : 31
                                          } ,
                                          {
                                              "label" : "2014-07-01" ,
                                              "value" : 3
                                          } ,
                                          {
                                              "label" : "2014-08-01" ,
                                              "value" : 18
                                          } ,
                                          {
                                              "label" : "2014-08-15" ,
                                              "value" : 13
                                          } ,
                                          {
                                              "label" : "2014-09-01" ,
                                              "value" : 5
                                          },
                                          {
                                              "label" : "2014-10-01" ,
                                              "value" : 20
                                          },
                                          {
                                              "label" : "2014-10-02" ,
                                              "value" : 15
                                          },
                                          {
                                              "label" : "2014-10-03" ,
                                              "value" : 5
                                          },
                                          {
                                              "label" : "2014-10-04" ,
                                              "value" : 7
                                          },
                                          {
                                              "label" : "2014-10-05" ,
                                              "value" : 12
                                          },
                                          {
                                              "label" : "2014-10-06" ,
                                              "value" : 3
                                          },
                                          {
                                              "label" : "2014-10-07" ,
                                              "value" : 20
                                          },
                                          {
                                              "label" : "2014-10-08" ,
                                              "value" : 14
                                          },
                                          {
                                              "label" : "2014-10-09" ,
                                              "value" : 12
                                          },
                                          {
                                              "label" : "2014-10-10" ,
                                              "value" : 5
                                          },
                                          {
                                              "label" : "2014-10-11" ,
                                              "value" : 26
                                          },
                                          {
                                              "label" : "2014-10-12" ,
                                              "value" : 12
                                          },
                                          {
                                              "label" : "2014-10-13" ,
                                              "value" : 10
                                          },
                                  ]
                              }
                          ]
            var chart = nv.models.discreteBarChart()
                .x(function(d) { return d.label })
                .y(function(d) { return d.value })
                .staggerLabels(false)
                .tooltips(true)
                .showYAxis(false)
                .showXAxis(false)
                .color([$(".btn-primary").css('background-color')])
                .tooltipContent(function (key, date, e, graph) {
                    var value = graph.value;
                    return "<div class='popover-title'>" + date + "</br>K : " + value + "+</div>";
                });
            d3.select('#karmagraph svg')
                .datum(data)
                .transition().duration(500)
                .call(chart)
            nv.utils.windowResize(chart.update);
        }
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

        $('.js_close_intro').on('click', function (ev) {
            ev.preventDefault();
            document.cookie = "no_introduction_message = false";
            return true;
        });

        $('.link_url').on('change', function (ev) {
            ev.preventDefault();
            var $link = $(ev.currentTarget);
            if ($link.attr("value").search("^http(s?)://.*")) {
                var $warning = $('<div class="alert alert-danger alert-dismissable" style="position:absolute; margin-top: -180px; margin-left: 90px;">'+
                    '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                    'Please enter valid URl.'+
                    '</div>');
                $link.parent().append($warning);
                $link.parent().find("button#btn_post_your_article")[0].disabled = true;
                $link.parent().find("input[name='content']")[0].value = '';
            } else {
                openerp.jsonRpc("/forum/get_url_title", 'call', {'url': $link.attr("value")}).then(function (data) {
                    $link.parent().find("input[name='content']")[0].value = data;
                    $('button').prop('disabled', false);
                    $('input').prop('readonly', false);
                });
            }
        });

        if($('input.load_tags').length){
            var tags = $("input.load_tags").val();
            $("input.load_tags").val("");
            set_tags(tags);
        };

        function set_tags(tags) {
            $("input.load_tags").textext({
                plugins: 'tags focus autocomplete ajax',
                ext: {
                    autocomplete: {
                        onSetSuggestions : function(e, data) {
                            var self        = this,
                                val         = self.val(),
                                suggestions = self._suggestions = data.result;
                            if(data.showHideDropdown !== false)
                                self.trigger(suggestions === null || suggestions.length === 0 && val.length === 0 ? "hideDropdown" : "showDropdown");
                        },
                        renderSuggestions: function(suggestions) {
                            var self = this,
                                val  = self.val();
                            self.clearItems();
                            $.each(suggestions || [], function(index, item) {
                                self.addSuggestion(item);
                            });
                            var lowerCasesuggestions = $.map(suggestions, function(n,i){return n.toLowerCase();});
                            if(jQuery.inArray(val.toLowerCase(), lowerCasesuggestions) ==-1) {
                                self.addSuggestion("Create '" + val + "'");
                            }
                        },
                    },
                    tags: {
                        onEnterKeyPress: function(e) {
                            var self = this,
                                val  = self.val(),
                                tag  = self.itemManager().stringToItem(val);

                            if(self.isTagAllowed(tag)) {
                                tag = tag.replace(/Create\ '|\'|'/g,'');
                                self.addTags([ tag ]);
                                // refocus the textarea just in case it lost the focus
                                self.core().focusInput();
                            }
                        },
                    }
                },
                tagsItems: tags.split(","),
                //Note: The following list of keyboard keys is added. All entries are default except {32 : 'whitespace!'}.
                keys: {8: 'backspace', 9: 'tab', 13: 'enter!', 27: 'escape!', 37: 'left', 38: 'up!', 39: 'right',
                    40: 'down!', 46: 'delete', 108: 'numpadEnter', 32: 'whitespace'},
                ajax: {
                    url: '/forum/get_tags',
                    dataType: 'json',
                    cacheResults: true
                }
            });

            $("input.load_tags").on('isTagAllowed', function(e, data) {
                if (_.indexOf($(this).textext()[0].tags()._formData, data.tag) != -1) {
                    data.result = false;
                }
            });
        }

        if ($('textarea.load_editor').length) {
            $('textarea.load_editor').each(function () {
                if (this['id']) {
                    CKEDITOR.replace(this['id']).on('instanceReady', CKEDITORLoadComplete);
                }
            });
        }
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
