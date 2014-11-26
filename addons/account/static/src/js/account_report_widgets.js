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
                'click .move_lines': 'displayMoveLines',
                'click .unreconciled': 'displayUnreconciled',
                'click .move': 'displayMove',
            },
            start: function() {
                this.footNoteSeqNum = 1;
                openerp.qweb.add_template("/account/static/src/xml/account_report_financial_line.xml")
                return this._super();
            },
            addFootNote: function(e) {
                e.preventDefault();
                if ($(e.target).find("sup").length == 0) {
                    $(e.target).append(' <sup>' + this.footNoteSeqNum + '</sup>');
                    this.$("table").after('<div class="row mt32 mb32"><label for="footnote' + 
                        this.footNoteSeqNum + '">' + this.footNoteSeqNum + '</label><textarea name="footnote' + this.footNoteSeqNum + 
                        '" rows=4 class="form-control">Insert foot note here</textarea><button class="btn btn-primary saveFootNote">Save</button></div>');
                    this.footNoteSeqNum++;
                }
            },
            fold: function(e) {
                e.preventDefault();
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
                $(e.target).replaceWith(openerp.qweb.render("unfoldable"));
                var active_id = $(e.target).attr("class").split(/\s+/)[1];
                var model = new openerp.Model('account.financial.report.line');
                model.call('write', [[parseInt(active_id)], {'unfolded': false}]);
            },
            unfold: function(e) {
                e.preventDefault();
                console.log('a');
                var active_id = $(e.target).attr("class").split(/\s+/)[1];
                var reportLineObj = new openerp.Model('account.financial.report.line');
                reportLineObj.call('write', [[parseInt(active_id)], {'unfolded': true}]).then(function (result) {
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
                        var report_id = window.$("div.page").attr("class").split(/\s+/)[2];
                        var $cursor = $(e.target).parent().parent();
                        var reportObj = new openerp.Model('account.financial.report');
                        reportObj.query(['debit_credit', 'balance'])
                        .filter([['id', '=', report_id]]).first().then(function (report) {
                            reportLineObj.call('get_lines', [[parseInt(active_id)], parseInt(report_id)])
                            .then(function (lines) {
                                var line;
                                lines.shift();
                                for (line in lines) {
                                    $cursor.after(openerp.qweb.render("report_financial_line", {a: lines[line], o: report}));
                                    $cursor = $cursor.next();
                                }
                            });
                        });
                    }
                    $(e.target).replaceWith('<span class="foldable">&gt;</span>');
                });
            },
            saveFootNote: function(e) {
                e.preventDefault();
                var num = $(e.target).parent().find("label").text();
                var note = $(e.target).parent().find("textarea").val();
                $(e.target).parent().replaceWith('<div class="row mt32 mb32">' + num + '. ' + note + '</div>');
            },
            displayMoveLines: function(e) {
                var active_id = $(e.target).attr("class").split(/\s+/)[1];
                var model = new openerp.Model('ir.model.data');
                model.call('get_object_reference', ['account', 'action_move_line_select']).then(function (result) {
                    window.open("/web?#page=0&limit=80&view_type=list&model=account.move.line&action=" + result[1] + "&active_id=" + active_id, "_self");
                });
            },
            displayUnreconciled: function(e) {
                var active_id = $(e.target).attr("class").split(/\s+/)[1];
                var model = new openerp.Model('ir.model.data');
                model.call('get_object_reference', ['account', 'act_account_acount_move_line_open_unreconciled']).then(function (result) {
                    window.open("/web?#page=0&limit=80&view_type=list&model=account.move.line&action=" + result[1] + "&active_id=" + active_id, "_self");
                });
            },
            displayMove: function(e) {
                var active_id = $(e.target).attr("class").split(/\s+/)[1];
                window.open("/web?#id=" + active_id + "&view_type=form&model=account.move", "_self");
            },
        });
        var reportWidgets = new openerp.reportWidgets();
        reportWidgets.setElement($('.oe_account_report_widgets'));
        reportWidgets.start();
    });

})();
