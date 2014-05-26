
openerp.hr_timesheet_week = function(instance) {
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;

    //TODO: Add weekly navigation in proper way
    instance.hr_timesheet.WeeklyTimesheet = instance.hr_timesheet.BaseTimesheet.extend({
    //instance.hr_timesheet.WeeklyTimesheet = instance.web.form.FormWidget.extend(instance.web.form.ReinitializeWidgetMixin, {
        events: {
            "click .oe_timesheet_weekly_account a": "go_to",
            "click .oe_timesheet_weekly .prev_week": "navigatePrevWeek",
            "click .oe_timesheet_weekly .next_week": "navigateNextWeek",
        },
        init: function() {
            this._super.apply(this, arguments);
            // Original save function is overwritten in order to wait all running deferreds to be done before actually applying the save.
            this.view.original_save = _.bind(this.view.save, this.view);
            this.view.save = function(prepend_on_create){
                self.prepend_on_create = prepend_on_create;
                return $.when.apply($, self.defs).then(function(){
                    return self.view.original_save(self.prepend_on_create);
                });
            };
        },
        initialize_content: function() {
            var self = this;
            if (self.setting)
                return;
            // don't render anything until we have date_to and date_from
            if (!self.get("date_to") || !self.get("date_from"))
                return;
            this.destroy_content();

            // it's important to use those vars to avoid race conditions
            var dates;
            var accounts;
            var account_names;
            var default_get;
            return this.render_drop.add(new instance.web.Model("hr.analytic.timesheet").call("default_get", [
                ['account_id','general_account_id', 'journal_id','date','name','user_id','product_id','product_uom_id','to_invoice','amount','unit_amount'],
                new instance.web.CompoundContext({'user_id': self.get('user_id')})]).then(function(result) {
                default_get = result;
                // calculating dates
                dates = [];
                var start = self.get("date_from");
                var end = self.get("date_to");
                while (start <= end) {
                    dates.push(start);
                    start = start.clone().addDays(1);
                }
                // group by account
                accounts = _(self.get("sheets")).chain()
                .map(function(el) {
                    // much simpler to use only the id in all cases
                    if (typeof(el.account_id) === "object")
                        el.account_id = el.account_id[0];
                    return el;
                })
                .groupBy("account_id").value();

                var account_ids = _.map(_.keys(accounts), function(el) { return el === "false" ? false : Number(el) });

                return new instance.web.Model("hr.analytic.timesheet").call("multi_on_change_account_id", [[], account_ids,
                    new instance.web.CompoundContext({'user_id': self.get('user_id')})]).then(function(accounts_defaults) {
                    accounts = _(accounts).chain().map(function(lines, account_id) {
                        account_defaults = _.extend({}, default_get, (accounts_defaults[account_id] || {}).value || {});
                        // group by days
                        account_id = account_id === "false" ? false :  Number(account_id);
                        var index = _.groupBy(lines, "date");
                        var days = _.map(dates, function(date) {
                            var day = {day: date, lines: index[instance.web.date_to_str(date)] || []};
                            // add line where we will insert/remove hours
                            var to_add = _.find(day.lines, function(line) { return line.name === self.description_line });
                            if (to_add) {
                                day.lines = _.without(day.lines, to_add);
                                day.lines.unshift(to_add);
                            } else {
                                day.lines.unshift(_.extend(_.clone(account_defaults), {
                                    name: self.description_line,
                                    unit_amount: 0,
                                    date: instance.web.date_to_str(date),
                                    account_id: account_id,
                                }));
                            }
                            return day;
                        });
                        return {account: account_id, days: days, account_defaults: account_defaults};
                    }).value();

                    // we need the name_get of the analytic accounts
                    return new instance.web.Model("account.analytic.account").call("name_get", [_.pluck(accounts, "account"),
                        new instance.web.CompoundContext()]).then(function(result) {
                        account_names = {};
                        _.each(result, function(el) {
                            account_names[el[0]] = el[1];
                        });
                        accounts = _.sortBy(accounts, function(el) {
                            return account_names[el.account];
                        });
                    });;
                });
            })).then(function(result) {
                // we put all the gathered data in self, then we render
                self.dates = dates;
                if(self.dates.length){
                    self.week = self.dates[0].getWeek();
                    self.last_week = self.dates[self.dates.length-1].getWeek();
                }
                self.accounts = accounts;
                self.account_names = account_names;
                self.default_get = default_get;
                //real rendering
                self.display_data();
            });
        },
        
        display_data: function() {
            var self = this;
            self.$el.html(QWeb.render("hr_timesheet.WeeklyTimesheet", {widget: self}));
            _.each(self.accounts, function(account) {
                _.each(_.range(account.days.length), function(day_count) {
                    if (!self.get('effective_readonly')) {
                        self.get_box(account, day_count).val(self.sum_box(account, day_count, true)).change(function() {
                            var num = $(this).val();
                            if (self.is_valid_value(num)){
                                num = (num == 0)?0:Number(self.parse_client(num));
                            }
                            if (isNaN(num)) {
                                $(this).val(self.sum_box(account, day_count, true));
                            } else {
                                account.days[day_count].lines[0].unit_amount += num - self.sum_box(account, day_count);
                                var product = (account.days[day_count].lines[0].product_id instanceof Array) ? account.days[day_count].lines[0].product_id[0] : account.days[day_count].lines[0].product_id
                                var journal = (account.days[day_count].lines[0].journal_id instanceof Array) ? account.days[day_count].lines[0].journal_id[0] : account.days[day_count].lines[0].journal_id
                                self.defs.push(new instance.web.Model("hr.analytic.timesheet").call("on_change_unit_amount", [[], product, account.days[day_count].lines[0].unit_amount, false, false, journal]).then(function(res) {
                                    account.days[day_count].lines[0]['amount'] = res.value.amount || 0;
                                    self.display_totals();
                                    self.sync();
                                }));
                                if(!isNaN($(this).val())){
                                    $(this).val(self.sum_box(account, day_count, true));
                                }
                            }
                        });
                    } else {
                        self.get_box(account, day_count).html(self.sum_box(account, day_count, true));
                    }
                });
            });
            self.display_totals();
            self.$(".oe_timesheet_weekly_adding button").click(_.bind(this.init_add_account, this));
        },
        init_add_account: function() {
            var self = this;
            if (self.dfm)
                return;
            self.$(".oe_timesheet_weekly_add_row").show();
            self.dfm = new instance.web.form.DefaultFieldManager(self);
            self.dfm.extend_field_desc({
                account: {
                    relation: "account.analytic.account",
                },
            });
            self.account_m2o = new instance.web.form.FieldMany2One(self.dfm, {
                attrs: {
                    name: "account",
                    type: "many2one",
                    domain: [
                        ['type','in',['normal', 'contract']],
                        ['state', '<>', 'close'],
                        ['use_timesheets','=',1],
                        ['id', 'not in', _.pluck(self.accounts, "account")],
                    ],
                    context: {
                        default_use_timesheets: 1,
                        default_type: "contract",
                    },
                    modifiers: '{"required": true}',
                },
            });
            self.account_m2o.prependTo(self.$(".oe_timesheet_weekly_add_row td"));
            self.$(".oe_timesheet_weekly_add_row button").click(function() {
                var id = self.account_m2o.get_value();
                if (id === false) {
                    self.dfm.set({display_invalid_fields: true});
                    return;
                }
                var ops = self.generate_o2m_value();
                new instance.web.Model("hr.analytic.timesheet").call("on_change_account_id", [[], id]).then(function(res) {
                    var def = _.extend({}, self.default_get, res.value, {
                        name: self.description_line,
                        unit_amount: 0,
                        date: instance.web.date_to_str(self.dates[0]),
                        account_id: id,
                    });
                    ops.push(def);
                    self.set({"sheets": ops});
                });
            });
        },
        get_box: function(account, day_count) {
            return this.$('[data-account="' + account.account + '"][data-day-count="' + day_count + '"]');
        },
        get_total: function(account) {
            return this.$('[data-account-total="' + account.account + '"]');
        },
        get_day_total: function(day_count) {
            return this.$('[data-day-total="' + day_count + '"]');
        },
        get_super_total: function() {
            return this.$('.oe_timesheet_weekly_supertotal');
        },
        sum_box: function(account, day_count, show_value_in_hour) {
            var line_total = 0;
            _.each(account.days[day_count].lines, function(line) {
                line_total += line.unit_amount;
            });
            return (show_value_in_hour && line_total != 0)?this.format_client(line_total):line_total;
        },
        display_totals: function() {
            var self = this;
            var day_tots = _.map(_.range(self.dates.length), function() { return 0 });
            var super_tot = 0;
            _.each(self.accounts, function(account) {
                var acc_tot = 0;
                _.each(_.range(self.dates.length), function(day_count) {
                    var sum = self.sum_box(account, day_count);
                    acc_tot += sum;
                    day_tots[day_count] += sum;
                    super_tot += sum;
                });
                self.get_total(account).html(self.format_client(acc_tot));
            });
            _.each(_.range(self.dates.length), function(day_count) {
                self.get_day_total(day_count).html(self.format_client(day_tots[day_count]));
            });
            self.get_super_total().html(self.format_client(super_tot));
        },
        generate_o2m_value: function() {
            var self = this;
            var ops = [];
            
            _.each(self.accounts, function(account) {
                var auth_keys = _.extend(_.clone(account.account_defaults), {
                    name: true, amount:true, unit_amount: true, date: true, account_id:true,
                });
                _.each(account.days, function(day) {
                    _.each(day.lines, function(line) {
                        if (line.unit_amount !== 0) {
                            var tmp = _.clone(line);
                            tmp.id = undefined;
                            _.each(line, function(v, k) {
                                if (v instanceof Array) {
                                    tmp[k] = v[0];
                                }
                            });
                            // we have to remove some keys, because analytic lines are shitty
                            _.each(_.keys(tmp), function(key) {
                                if (auth_keys[key] === undefined) {
                                    tmp[key] = undefined;
                                }
                            });
                            ops.push(tmp);
                        }
                    });
                });
            });
            return ops;
        },
        navigatePrevWeek: function(){
            if(this.week != this.dates[0].getWeek())
                this.week -= 1;
            else
               this.week = this.last_week; 
            this.display_data();
        },
        navigateNextWeek: function(){
            if(this.week == this.last_week)
                this.week = this.dates[0].getWeek();
            else
                this.week += 1;
            this.display_data();
        },
    });
    instance.web.form.custom_widgets.add('weekly_timesheet', 'instance.hr_timesheet.WeeklyTimesheet');

};
