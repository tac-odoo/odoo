openerp.hr_timesheet_day = function(instance) {
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;

    instance.hr_timesheet.DailyTimesheet = instance.hr_timesheet.BaseTimesheet.extend({
         events: {
            "click .oe_timesheet_daily .next_day": "navigateNext",
            "click .oe_timesheet_daily .prev_day": "navigatePrev",
            "click .oe_timesheet_daily .first_day": "navigateFirstDay",
            "click .oe_header" : "navigateDays",
            "click .oe_timesheet_edit_description" : "addDescription",
            "click .oe_copy_accounts a": "copy_accounts",
            "click .oe_timesheet_goto a": "go_to"
        },
        init: function() {
            this._super.apply(this, arguments);
            this.account_id = [];
            this.count = 0;
            this.week = 0;
            this.flag = 0;
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
            var days;
            var new_account_names;
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
                //groupby date
                new_days = _(self.get("sheets")).chain()
                .map(function(line) {
                    if (typeof(line.account_id) === "object")
                        line.account_id = line.account_id[0];
                    return line;
                })
                .groupBy("date").value();
                var new_account_ids = _(new_days).chain()
                .map(function(el) {
                    new_accs = _.map(el, function(entry) {
                        return entry.account_id === "false" ? false : (typeof(entry.account_id) === "object" ? Number(entry.account_id[0]) : Number(entry.account_id))
                    });
                    return new_accs;
                })
                .flatten(true)
                .union().value();

                //TODO: Process on account_groups instead of day.lines
                return new instance.web.Model("hr.analytic.timesheet").call("multi_on_change_account_id", [[], new_account_ids,
                    new instance.web.CompoundContext({'user_id': self.get('user_id')})]).then(function(accounts_defaults) {
                    account_defaults = _.extend({}, default_get, (accounts_defaults[new_account_ids] || {}).value || {});
                    days = _.map(dates, function(date) {
                        var week = date.getWeek();
                        var account_group = _.groupBy(new_days[instance.web.date_to_str(date)], "account_id");
                        var day = {day: date,account_defaults: account_defaults, account_group: account_group,week: week};
                        return day;
                    });
                    return new instance.web.Model("account.analytic.account").call("name_get", [new_account_ids,
                        new instance.web.CompoundContext()]).then(function(result) {
                            new_account_names = {};
                            _.each(result, function(el) {
                                new_account_names[el[0]] = el[1];
                            });
                            //Sorting days accounts based on account_id
                            days = _.each(days, function(day) {
                                return _.sortBy(day.accoutn_group, function(el) {
                                    return new_account_names[el.account_id];
                                });
                            });
                        });
                    });
            })).then(function(result) {
                self.new_dates = dates;
                self.account_names = new_account_names;
                self.days = days;
                //TODO: Need to improve this logic of week(developed by NJA)
                if(self.days.length) {
                    self.week = self.days[0].week;
                    self.last_week = self.days[self.days.length-1].week;
                }
                self.default_get = default_get;
                //real rendering
                self.display_data();
                self.toggle_active(self.count);
            });
        },
        display_data: function() {
            var self = this;
            this.$el.html(QWeb.render("hr_timesheet_day.DailyTimesheet", {widget: self}));
            if (self.days.length) {
                var day_count = self.count;
                 _.each(self.days[self.count].account_group, function(account){
                    if (!self.get('effective_readonly')){
                        self.get_box(account).val(self.sum_box(account, true)).change(function() {
                            var num = $(this).val();
                            if(!self.is_valid_value(num)){
                                    num = (num == 0)?0:Number(self.parse_client(num));
                            }
                            if (isNaN(num)) {
                                $(this).val(self.sum_box(account, true));
                            } else {
                                account[0].unit_amount += num - self.sum_box(account);
                                var product = (account[0].product_id instanceof Array) ? account[0].product_id[0] : account[0].product_id
                                var journal = (account[0].journal_id instanceof Array) ? account[0].journal_id[0] : account[0].journal_id
                                self.defs.push(new instance.web.Model("hr.analytic.timesheet").call("on_change_unit_amount", [[], product, account[0].unit_amount, false, false, journal]).then(function(res) {
                                    account[0].amount = res.value.amount || 0;
                                    self.display_totals();
                                    self.sync();
                                }));
                                if(!isNaN($(this).val())){
                                    $(this).val(self.sum_box(account, true));
                                }
                            }
                        });
                    } else {
                        self.get_box(account).html(self.sum_box(account, true));
                    }
                });
                self.display_totals();
                self.$(".oe_timesheet_daily_adding button").click(_.bind(this.init_add_account, this));
            }
        },
        get_desc: function(account,day_count){
            var input_box = this.$('.oe_edit_input')[day_count];
            return $(input_box).val(account[0].name);
        },
        get_box: function(account) {
            return this.$('.oe_timesheet_daily_box[data-account="' + account[0].account_id + '"]');
        },
        get_total: function(account) {
            return this.$('[data-account-total = "' + account + '"]');
        },
        set_day_total: function(day_count, total) {
            return this.$el.find('.oe_daily_header .oe_display_day_total[data-day-total = "' + day_count + '"]').html(this.format_client(total));;
        },
        get_super_total: function() {
            return this.$('.oe_header_total');
        },
        sum_box: function(account, show_value_in_hour) {
            var line_total = 0;
            _.each(account, function(line){
                line_total += line.unit_amount;
            });
            return (show_value_in_hour && line_total != 0)?this.format_client(line_total):line_total;
        },
        display_totals: function() {
            var self = this;
            var day_tots = _.map(_.range(self.days.length), function() { return 0 });
            var super_tot = 0;
            var acc_tot = 0;
            _.each(self.days, function(days,day_count) {
                _.each(days.account_group,function(account){
                    var sum = self.sum_box(account);
                    acc_tot = acc_tot +  sum;
                    day_tots[day_count] += sum;
                    super_tot += sum;
                });
            });
            _.each(_.range(self.days.length), function(day_count) {
                self.set_day_total(day_count, day_tots[day_count]);
            });
            self.get_super_total().html("Total: " + (self.format_client(super_tot)));
        },
        generate_o2m_value: function() {
            var self = this;
            var ops = [];
                _.each(self.days, function(day) {
                    var auth_keys = _.extend(_.clone(day.account_defaults), {
                    name: true, amount:true, unit_amount: true, date: true, account_id:true,
                    });
                    _.each(day.account_group, function(account) {
                        _.each(account,function(line){
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
        init_add_account: function() {
            var self = this;
            if (self.dfm)
                return;
            self.$(".oe_copy_accounts").hide();
            self.$(".oe_timesheet_daily_add_row").show();
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
                        ['id', 'not in', _.keys(self.days[self.count].account_group)],
                    ],
                    context: {
                        default_use_timesheets: 1,
                        default_type: "contract",
                    },
                    modifiers: '{"required": true}',
                },
            });
            self.account_m2o.prependTo(self.$(".oe_timesheet_daily_add_row"));
            self.$(".oe_timesheet_daily_add_row button").click(function() {
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
                        date: instance.web.date_to_str(self.days[self.count].day),
                        account_id: id,
                    });
                    ops.push(def);
                    self.set({"sheets": ops});
                });
            });
        },
        copy_accounts: function(e) {
            var self = this;
            var index = this.count;
            _.each(this.days[index],function(){
                if(_.isEmpty(self.days[index].account_group)){
                    if(index == 0)
                        return;
                    else
                        index -= 1;
                }
            });
            this.days[this.count].account_group = JSON.parse(JSON.stringify(this.days[index].account_group));
            _.each(this.days[this.count].account_group,function(account) {
                var d = self.days[self.count].day.toString("yyyy-MM-dd")
                _.each(account,function(account) {
                    account.date = d;
                    account.unit_amount = 0;
                    account.name = self.description_line;
                });
            });
            this.sync();
            this.display_data();
        },
        addDescription: function(e) {
            var self=this;
            var index = this.$(e.target).attr("data-day-count") || this.$(e.srcElement).attr("data-day-count"); 
            var input = this.$(".oe_edit_input")[index];
            var act_id = this.$(e.target).attr("data-account");
            var account = this.days[self.count].account_group[act_id];
            this.$(".oe_edit_input").hide(); 
            if(this.$(input).attr("data-account")==act_id)
                this.$(input).show();
            this.get_desc(account,index)
            .change(function(){
                var text = $(this).val();
                account[0].name = text;
                self.sync();
            });
        },
        toggle_active: function(day_count) {
            this.$el.find(".oe_day_button[data-day-counter|="+day_count+"]").addClass("oe_active_day").siblings().removeClass("oe_active_day")
            this.$el.find(".oe_day_button[data-day-counter|="+day_count+"] span").removeClass("oe_display_day_total").siblings().addClass("oe_display_day_total");
            if(this.count == 0)
                this.$el.find(".first_day").removeClass("oe_day_button").addClass("oe_fday_button");
        },
        navigateNext: function() {
            if(this.count == this.days.length-1){
                this.week = this.days[0].week;
                this.count = 0;
            } else {
                this.count+=1;
                this.week = this.days[this.count].week;
            }
            this.display_data();
            this.toggle_active(this.count);
        },
        navigatePrev: function(e) {
            if (this.count==0)
                this.count = self.days.length-1;
            else
                this.count -= 1;
            this.week = self.days[self.count].week;
            this.display_data();
            this.toggle_active(this.count);
        },
        navigateFirstDay: function() {
            this.count = 0;
            this.display_data();
            this.toggle_active(this.count);
        },
        navigateDays: function(e){
            this.count = parseInt($(e.target).attr("data-day-counter"), 10);
            this.display_data();
            this.toggle_active(this.count);
        },
    });
    instance.web.form.custom_widgets.add('daily_timesheet', 'instance.hr_timesheet.DailyTimesheet');
};