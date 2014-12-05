(function () {
    'use strict';

    $(document).ready(function() {
        openerp.footnote = {};
        var _t = openerp._t;


        openerp.reportWidgets = openerp.Widget.extend({
            events: {
                'click .annotable': 'addFootNote',
                'click .foldable': 'fold',
                'click .unfoldable': 'unfold',
                'click .saveFootNote': 'saveFootNote',
                'click .account_id': 'displayMoveLines',
                'click .aml': 'displayMoveLine',
            },
            start: function() {
                this.footNoteSeqNum = 1;
                openerp.qweb.add_template("/account/static/src/xml/account_report_financial_line.xml")
                return this._super();
            },
            addFootNote: function(e) {
                e.preventDefault();
                if ($(e.target).find("sup").length == 0) {
                    $(e.target).append(openerp.qweb.render("supFootNoteSeqNum", {footNoteSeqNum: this.footNoteSeqNum}));
                    this.$("table").after(openerp.qweb.render("footNoteTextarea", {footNoteSeqNum: this.footNoteSeqNum}));
                    this.footNoteSeqNum++;
                }
            },
            fold: function(e) {
                e.preventDefault();
                var context_id = window.$("div.page").attr("class").split(/\s+/)[2];
                var level = $(e.target).next().html().length;
                var el;
                var $el;
                var $nextEls = $(e.target).parent().parent().nextAll();
                for (el in $nextEls) {
                    $el = $($nextEls[el]).find("td span.level");
                    if ($el.html() == undefined)
                        break;
                    if ($el.html().length > level){
                        $el.parent().parent().hide();
                    }
                    else {
                        break;
                    }
                }
                var active_id = $(e.target).attr("class").split(/\s+/)[1];
                $(e.target).replaceWith(openerp.qweb.render("unfoldable", {lineId: active_id}));
                var model = new openerp.Model('account.financial.report.context');
                model.call('remove_line', [[parseInt(context_id)], parseInt(active_id)]);
            },
            unfold: function(e) {
                e.preventDefault();
                var context_id = window.$("div.page").attr("class").split(/\s+/)[2];
                var active_id = $(e.target).attr("class").split(/\s+/)[1];
                var contextObj = new openerp.Model('account.financial.report.context');
                contextObj.call('add_line', [[parseInt(context_id)], parseInt(active_id)]).then(function (result) {
                    var level = $(e.target).next().html().length;
                    var el;
                    var $el;
                    var $nextEls = $(e.target).parent().parent().nextAll();
                    var isLoaded = false;
                    for (el in $nextEls) {
                        $el = $($nextEls[el]).find("td span.level");
                        if ($el.html() == undefined)
                            break;
                        if ($el.html().length > level){
                            $el.parent().parent().show();
                            isLoaded = true;
                        }
                        else {
                            break;
                        }
                    }
                    if (!isLoaded) {
                        var $cursor = $(e.target).parent().parent();
                        var reportObj = new openerp.Model('account.financial.report');
                        var reportLineObj = new openerp.Model('account.financial.report.line');
                        contextObj.query(['financial_report_id', 'comparison'])
                        .filter([['id', '=', context_id]]).first().then(function (context) {
                            reportObj.query(['debit_credit', 'balance'])
                            .filter([['id', '=', context.financial_report_id[0]]]).first().then(function (report) {
                                reportLineObj.call('get_lines_with_context', [[parseInt(active_id)], parseInt(context_id), level/2])
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
                    $(e.target).replaceWith(openerp.qweb.render("foldable", {lineId: active_id}));
                });
            },
            saveFootNote: function(e) {
                e.preventDefault();
                var num = $(e.target).parent().find("label").text();
                var note = $(e.target).parent().find("textarea").val();
                $(e.target).parent().replaceWith(openerp.qweb.render("savedFootNote", {num: num, note: note}));
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
        });
        var reportWidgets = new openerp.reportWidgets();
        reportWidgets.setElement($('.oe_account_report_widgets'));
        reportWidgets.start();
    });

})();
