(function () {
    'use strict';

    $(document).ready(function() {
        openerp.footnote = {};
        var _t = openerp._t;

        var footNoteSeqNum = 1

        var dialog, popupform,
        allFields = $([]).add($("#note"))

        function saveFootNote() {
            $("table").after(openerp.qweb.render("savedFootNote", {num: footNoteSeqNum, note: $("#note").val()}));
            footNoteSeqNum++;
        }

        dialog = $("#footnote-form").dialog({
                dialogClass: "form-group",
                autoOpen: false,
                height: 150,
                width: 400,
                modal: true,
                buttons: [
                    {
                        text: "Add footnote",
                        class: "btn btn-default btn-sm",
                        click: saveFootNote,
                    },
                    {
                        text: "Cancel",
                        class: "btn btn-default btn-sm",
                        click: function() {
                            $(this).dialog("close");
                        },
                    },
                ],
                close: function() {
                    popupform[0].reset();
                    allFields.removeClass("ui-state-error");
                    $("sup:contains('" + footNoteSeqNum + "')").remove()
                }
            });

        popupform = dialog.find("form").on("submit", function(e) {
            e.preventDefault();
            saveFootNote();
        });

        openerp.reportWidgets = openerp.Widget.extend({
            events: {
                'click .fa-plus-square': 'addFootNote',
                'click .foldable': 'fold',
                'click .unfoldable': 'unfold',
                'click .saveFootNote': 'saveFootNote',
                'click .account_id': 'displayMoveLines',
                'click .aml': 'displayMoveLine',
                'mouseenter .annotable': 'addPlus',
                'mouseleave .annotable': 'rmPlus',
                'mouseenter .footnote': 'addTrash',
                'mouseleave .footnote': 'rmTrash',
                'click .fa-trash-o': 'rmFootNote',
                "change *[name='date_filter']": 'onChangeDateFilter',
                "change *[name='date_filter_cmp']": 'onChangeCmpDateFilter',
            },
            start: function() {
                openerp.qweb.add_template("/account/static/src/xml/account_report_financial_line.xml");
                var res = this._super();
                this.onChangeCmpDateFilter();
                return res;
            },
            onChangeDateFilter: function(e) {
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
                    else if (date_filter.search("month") > -1 || no_date_range) {
                        dtTo.setDate(0);
                        if (!no_date_range) {
                            dtFrom.setMonth(dtFrom.getMonth() - 1);
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
                }
            },
            addFootNote: function(e) {
                e.preventDefault();
                if ($(e.target).parent().find("sup").length == 0) {
                    $(e.target).parent().append(' <sup>' + footNoteSeqNum + '</sup>');
                    this.$("#footnote-form label").text(footNoteSeqNum);
                    dialog.dialog("option", "position", {my: "top", at: "bottom", of: $(e.target)});
                    dialog.dialog("open");
                }
            },
            rmFootNote: function(e) {
                e.preventDefault();
                var num = $(e.target).parent().text().split('.')[0];
                $(e.target).parent().remove();
                this.$("sup:contains('" + num + "')").remove()
            },
            fold: function(e) {
                e.preventDefault();
                var context_id = window.$("div.page").attr("class").split(/\s+/)[2];
                var el;
                var $el;
                var $nextEls = $(e.target).parent().parent().parent().nextAll();
                for (el in $nextEls) {
                    $el = $($nextEls[el]).find("td span[style='font-style: italic; margin-left: 150px']");
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
                        $el = $($nextEls[el]).find("td span[style='font-style: italic; margin-left: 150px']");
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
                        contextObj.query(['financial_report_id', 'comparison'])
                        .filter([['id', '=', context_id]]).first().then(function (context) {
                            reportObj.query(['debit_credit'])
                            .filter([['id', '=', context.financial_report_id[0]]]).first().then(function (report) {
                                reportLineObj.call('get_lines_with_context', [[parseInt(active_id)], parseInt(context_id)])
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
                var active_id = $(e.target).attr("class").split(/\s+/)[1];
                var model = new openerp.Model('ir.model.data');
                model.call('get_object_reference', ['account', 'action_move_line_select']).then(function (result) {
                    window.open("/web?#page=0&limit=80&view_type=list&model=account.move.line&action=" + result[1] + "&active_id=" + active_id, "_self");
                });
            },
            displayMoveLine: function(e) {
                var active_id = $(e.target).attr("class").split(/\s+/)[1];
                window.open("/web?#id=" + active_id + "&view_type=form&model=account.move.line", "_self");
            },
            addPlus: function(e) {
                e.preventDefault();
                if ($(e.target).parent().find("sup").length == 0) {
                    $(e.target).prepend(openerp.qweb.render("plusIcon"));
                }
            },
            rmPlus: function(e) {
                e.preventDefault();
                this.$("i.fa-plus-square").remove();
            },
            addTrash: function(e) {
                e.preventDefault();
                debugger;
                $(e.target).append(openerp.qweb.render("trashIcon"));
            },
            rmTrash: function(e) {
                e.preventDefault();
                this.$("i.fa-trash-o").remove();
            },
        });
        var reportWidgets = new openerp.reportWidgets();
        reportWidgets.setElement($('.oe_account_report_widgets'));
        reportWidgets.start();
    });

})();
