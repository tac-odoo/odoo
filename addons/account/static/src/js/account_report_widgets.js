(function () {
    'use strict';

    $(document).ready(function() {
        openerp.footnote = {};
        var _t = openerp._t;

        var footNoteSeqNum = 1;

        openerp.reportWidgets = openerp.Widget.extend({
            events: {
                'click .fa-pencil-square': 'clickPencil',
                'click .foldable': 'fold',
                'click .unfoldable': 'unfold',
                'click .saveFootNote': 'saveFootNote',
                'click .account_id': 'displayMoveLines',
                'click .aml': 'displayMoveLine',
                'mouseenter .annotable': 'addPencil',
                'mouseleave .annotable': 'rmPencil',
                'mouseenter .line': 'addPencil',
                'mouseleave .line': 'rmPencil',
                'mouseenter .account_id': 'addPencil',
                'mouseleave .account_id': 'rmPencil',
                'mouseenter .footnote': 'addTrashAndPencil',
                'mouseleave .footnote': 'rmTrashAndPencil',
                'click .fa-trash-o': 'rmContent',
                "change *[name='date_filter']": 'onChangeDateFilter',
                "change *[name='date_filter_cmp']": 'onChangeCmpDateFilter',
                "change *[name='comparison']": 'onChangeComparison',
                "click input[name='summary']": 'onClickSummary',
                "click button.saveSummary": 'saveSummary',
                'mouseenter .savedSummary': 'addTrashAndPencil',
                'mouseleave .savedSummary': 'rmTrashAndPencil',
                'click button.saveContent': 'saveContent',
                'click button#saveFootNote': 'saveFootNote',
            },
            saveFootNote: function() {
                this.$("div.page").append(openerp.qweb.render("savedFootNote", {num: footNoteSeqNum, note: $("#note").val()}));
                footNoteSeqNum++;
                this.$('#footnoteModal').modal('hide');
                this.$('#footnoteModal').find('form')[0].reset();
            },
            start: function() {
                openerp.qweb.add_template("/account/static/src/xml/account_report_financial_line.xml");
                var res = this._super();
                this.onChangeCmpDateFilter();
                return res;
            },
            addTrashAndPencil: function(e) {
                e.stopPropagation();
                e.preventDefault();
                if ($(e.target).children("textarea").length == 0 && $(e.target).siblings("textarea").length == 0) {
                    $(e.target).append(openerp.qweb.render("trashAndPencilIcon"));
                }
            },
            rmTrashAndPencil: function(e) {
                e.stopPropagation();
                e.preventDefault();
                this.$("i.fa-trash-o").remove();
                this.$("i.fa-pencil-square").remove();
            },
            onClickSummary: function(e) {
                e.stopPropagation();
                this.$("div.summary").html(openerp.qweb.render("editSummary"));
            },
            saveSummary: function(e) {
                e.stopPropagation();
                var summary = this.$("textarea[name='summary']").val();
                this.$("div.summary").html(openerp.qweb.render("savedSummary", {summary : summary}));
            },
            onChangeComparison: function(e) {
                e.stopPropagation();
                var checkbox = $(e.target).is(":checked")
                if (checkbox) {
                    this.$("label[for='date_filter_cmp']").parent().attr('style', '')
                    this.$("label[for='date_to_cmp']").parent().parent().attr('style', '');
                }
                else {
                    this.$("label[for='date_filter_cmp']").parent().attr('style', 'visibility: hidden');
                    this.$("label[for='date_to_cmp']").parent().parent().attr('style', 'visibility: hidden');
                }
            },
            onChangeDateFilter: function(e) {
                e.stopPropagation();
                e.preventDefault();
                var filter = $(e.target).val();
                var no_date_range = this.$("input[name='date_from']").length == 0;
                switch(filter) {
                    case 'today':
                        var dt = new Date();
                        this.$("input[name='date_to']").val(dt.toISOString().substr(0, 10));
                        break;
                    case 'last_month':
                        var dt = new Date();
                        dt.setDate(0);
                        this.$("input[name='date_to']").val(dt.toISOString().substr(0, 10)); 
                        if (!no_date_range) {
                            dt.setDate(1);
                            this.$("input[name='date_from']").val(dt.toISOString().substr(0, 10)); 
                        }
                        break;
                    case 'last_quarter':
                        var dt = new Date();
                        dt.setMonth((Math.floor((dt.getMonth())/3)) * 3);
                        dt.setDate(0);
                        this.$("input[name='date_to']").val(dt.toISOString().substr(0, 10));
                        if (!no_date_range) {
                            dt.setDate(1);
                            dt.setMonth(dt.getMonth() - 2);
                            this.$("input[name='date_from']").val(dt.toISOString().substr(0, 10)); 
                        }
                        break;
                    case 'last_year':
                        var dt = new Date();
                        dt.setMonth(0);
                        dt.setDate(0);
                        this.$("input[name='date_to']").val(dt.toISOString().substr(0, 10));
                        if (!no_date_range) {
                            dt.setDate(1);
                            dt.setMonth(0);
                            this.$("input[name='date_from']").val(dt.toISOString().substr(0, 10)); 
                        }
                        break;
                    case 'this_month':
                        var dt = new Date();
                        dt.setDate(1);
                        this.$("input[name='date_from']").val(dt.toISOString().substr(0, 10)); 
                        dt.setMonth(dt.getMonth() + 1);
                        dt.setDate(0);
                        this.$("input[name='date_to']").val(dt.toISOString().substr(0, 10)); 
                        break;
                    case 'this_year':
                        var dt = new Date();
                        dt.setDate(1);
                        dt.setMonth(0);
                        this.$("input[name='date_from']").val(dt.toISOString().substr(0, 10)); 
                        dt.setDate(31);
                        dt.setMonth(11);
                        this.$("input[name='date_to']").val(dt.toISOString().substr(0, 10)); 
                        break;
                }
                if (filter == 'custom') {
                    this.$("label[for='date_to']").parent().attr('style', '')
                }
                else {
                    this.$("label[for='date_to']").parent().attr('style', 'visibility: hidden');
                }
                onChangeCmpDateFilter();
            },
            onChangeCmpDateFilter: function() {
                var date_filter = this.$("select[name='date_filter']").val();
                var cmp_filter = this.$("select[name='date_filter_cmp']").val();
                var no_date_range = this.$("input[name='date_from']").length == 0;
                if (cmp_filter == 'custom') {
                    this.$("label[for='date_to_cmp']").parent().attr('style', '');
                    // this.$("input[name='periods_number']").parent().attr('style', 'visibility: hidden');
                }
                else {
                    var dtTo = this.$("input[name='date_to']").val(); 
                    dtTo = new Date(dtTo.substr(0, 4), dtTo.substr(5, 2) - 1, dtTo.substr(8, 2), 12, 0, 0, 0);
                    if (!no_date_range) {
                        var dtFrom = this.$("input[name='date_from']").val();
                        dtFrom = new Date(dtFrom.substr(0, 4), dtFrom.substr(5, 2) - 1, dtFrom.substr(8, 2), 12, 0, 0, 0);
                    }    
                    if (date_filter.search("quarter") > -1) {
                        dtTo.setMonth(dtTo.getMonth() - 2);
                        dtTo.setDate(0);
                        if (!no_date_range) {
                            dtFrom.setMonth(dtFrom.getMonth() - 3);
                        }
                    }
                    else if (date_filter.search("year") > -1) {
                        dtTo.setFullYear(dtTo.getFullYear() - 1);
                        if (!no_date_range) {
                            dtFrom.setFullYear(dtFrom.getFullYear() - 1);
                        }
                    }
                    else if (date_filter.search("month") > -1) {
                        dtTo.setDate(0);
                        if (!no_date_range) {
                            dtFrom.setMonth(dtFrom.getMonth() - 1);
                        }
                    }
                    else if (no_date_range) {
                        var month = dtTo.getMonth()
                        dtTo.setMonth(month - 1);
                        if (dtTo.getMonth() == month) {
                            dtTo.setDate(0);
                        }
                    }
                    else {
                        var diff = dtTo.getTime() - dtFrom.getTime();
                        dtTo = dtFrom;
                        dtTo.setDate(dtFrom.getDate() - 1);
                        dtFrom = new Date(dtTo.getTime() - diff);
                    }
                    if (!no_date_range) {
                        this.$("input[name='date_from_cmp']").val(dtFrom.toISOString().substr(0, 10)); 
                    }
                    this.$("input[name='date_to_cmp']").val(dtTo.toISOString().substr(0, 10)); 
                    this.$("label[for='date_to_cmp']").parent().attr('style', 'visibility: hidden');
                    // this.$("input[name='periods_number']").parent().attr('style', '');
                }
            },
            clickPencil: function(e) {
                e.stopPropagation();
                e.preventDefault();
                if ($(e.target).parents("div.summary, p.footnote").length > 0) {
                    var $el = $(e.target).parent().parent();
                    this.rmTrashAndPencil(e);
                    var text = $el.text();
                    var num = 0;
                    if ($el.attr('class').search('footnote') > -1) {
                        text = text.split('.');
                        var num = text[0];
                        text = text[1];
                    }
                    $el.html(openerp.qweb.render("editContent", {num: num, text: text}));
                }
                else if ($(e.target).parent().parent().find("sup").length == 0) {
                    $(e.target).parent().parent().append(openerp.qweb.render("supFootNoteSeqNum", {footNoteSeqNum: footNoteSeqNum}));
                    $("#footnoteModal label").text(footNoteSeqNum);
                    $('#footnoteModal').on('hidden.bs.modal', function (e) {
                        $(this).find('form')[0].reset();
                        $("sup:contains('" + footNoteSeqNum + "')").remove();
                    });
                    $('#footnoteModal').modal('show');
                }
            },
            saveContent: function(e) {
                e.stopPropagation();
                e.preventDefault();
                var text = $(e.target).siblings('textarea').val();
                $(e.target).siblings('textarea').replaceWith(text);
                $(e.target).remove();
            },
            rmContent: function(e) {
                e.stopPropagation();
                e.preventDefault();
                if ($(e.target).parents("div.summary").length > 0) {
                    $(e.target).parent().parent().replaceWith(openerp.qweb.render("addSummary"));
                }
                else {
                    var num = $(e.target).parent().parent().text().split('.')[0];
                    this.$("sup:contains('" + num + "')").remove();
                    $(e.target).parent().parent().remove();
                }
            },
            fold: function(e) {
                e.stopPropagation();
                e.preventDefault();
                var context_id = window.$("div.page").attr("class").split(/\s+/)[2];
                var el;
                var $el;
                var $nextEls = $(e.target).parent().parent().parent().nextAll();
                for (el in $nextEls) {
                    $el = $($nextEls[el]).find("td span[style='font-style: italic; margin-left: 70px']");
                    if ($el.length == 0)
                        break;
                    else {
                        $($el[0]).parents("tr").hide();
                    }
                }
                var active_id = $(e.target).parent().attr("class").split(/\s+/)[1];
                $(e.target).parent().replaceWith(openerp.qweb.render("unfoldable", {lineId: active_id}));
                var model = new openerp.Model('account.financial.report.context');
                model.call('remove_line', [[parseInt(context_id)], parseInt(active_id)]);
            },
            unfold: function(e) {
                e.stopPropagation();
                e.preventDefault();
                var context_id = window.$("div.page").attr("class").split(/\s+/)[2];
                var active_id = $(e.target).parent().attr("class").split(/\s+/)[1];
                var contextObj = new openerp.Model('account.financial.report.context');
                contextObj.call('add_line', [[parseInt(context_id)], parseInt(active_id)]).then(function (result) {
                    var el;
                    var $el;
                    var $nextEls = $(e.target).parent().parent().parent().nextAll();
                    var isLoaded = false;
                    for (el in $nextEls) {
                        $el = $($nextEls[el]).find("td span[style='font-style: italic; margin-left: 100px']");
                        if ($el.length == 0)
                            break;
                        else{
                            $($el[0]).parents("tr").show();
                            isLoaded = true;
                        }
                    }
                    if (!isLoaded) {
                        var $cursor = $(e.target).parent().parent().parent();
                        var reportObj = new openerp.Model('account.financial.report');
                        var reportLineObj = new openerp.Model('account.financial.report.line');
                        contextObj.query(['report_id', 'comparison'])
                        .filter([['id', '=', context_id]]).first().then(function (context) {
                            reportObj.query(['debit_credit'])
                            .filter([['id', '=', context.report_id[0]]]).first().then(function (report) {
                                reportObj.call('get_lines', [[parseInt(context.report_id[0])], parseInt(context_id), parseInt(active_id)])
                                .then(function (lines) {
                                    var line;
                                    lines.shift();
                                    for (line in lines) {
                                        $cursor.after(openerp.qweb.render("report_financial_line", {l: lines[line], o: report, c: context}));
                                        $cursor = $cursor.next();
                                    }
                                });
                            });
                        });
                    }
                    $(e.target).parent().replaceWith(openerp.qweb.render("foldable", {lineId: active_id}));
                });
            },
            displayMoveLines: function(e) {
                e.stopPropagation();
                var active_id = $(e.target).attr("class").split(/\s+/)[1];
                var model = new openerp.Model('ir.model.data');
                model.call('get_object_reference', ['account', 'action_move_line_select']).then(function (result) {
                    window.open("/web?#page=0&limit=80&view_type=list&model=account.move.line&action=" + result[1] + "&active_id=" + active_id, "_self");
                });
            },
            displayMoveLine: function(e) {
                e.stopPropagation();
                var active_id = $(e.target).attr("class").split(/\s+/)[1];
                window.open("/web?#id=" + active_id + "&view_type=form&model=account.move.line", "_self");
            },
            addPencil: function(e) {
                e.stopPropagation();
                e.preventDefault();
                if ($(e.target).parent().find("sup").length == 0 && $(e.target).parents("sup").length == 0) {
                    $(e.target).append(openerp.qweb.render("pencilIcon"));
                }
            },
            rmPencil: function(e) {
                e.stopPropagation();
                e.preventDefault();
                this.$("i.fa-pencil-square").parent().remove();
            },
        });
        var reportWidgets = new openerp.reportWidgets();
        reportWidgets.setElement($('.oe_account_report_widgets'));
        reportWidgets.start();
    });

})();
