openerp.hr_timesheet_sheet = function(instance) {
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;
    instance.hr_timesheet_sheet.WeeklyTimesheet = instance.web.form.FormWidget.extend(instance.web.form.ReinitializeWidgetMixin, {
        events: {
            "click .oe_timesheet_weekly_account a": "go_to",
            "click .oe_nav, .oe_header": "navigateAll",
            "click .oe_timesheet_edit_description" : "addDescription",
            "click .oe_copy_accounts a": "copy_accounts",
            "click .oe_timesheet_goto a": "go_to",
            "click .oe_timesheet_daily_adding a": "init_add_accountd", 
            "click .oe_timer": "timer",
            "click .oe_timesheet_nav_day": "switcher",
            "click .oe_timesheet_nav_week": "switcher"
        },
        ignore_fields: function() {
            return ['line_id'];
        },
        init: function() {
            this._super.apply(this, arguments);
            var self = this;
            this.set({
                sheets: [],
                date_to: false,
                date_from: false,
            });
            this.updating = false;
            this.account_id = [];
            this.count = 0;
            this.defs = [];
            this.field_manager.on("field_changed:timesheet_ids", this, this.query_sheets);
            this.field_manager.on("field_changed:date_from", this, function() {
                this.set({"date_from": instance.web.str_to_date(this.field_manager.get_field_value("date_from"))});
            });
            this.field_manager.on("field_changed:date_to", this, function() {
                this.set({"date_to": instance.web.str_to_date(this.field_manager.get_field_value("date_to"))});
            });
            this.field_manager.on("field_changed:user_id", this, function() {
                this.set({"user_id": this.field_manager.get_field_value("user_id")});
            });
            this.on("change:sheets", this, this.update_sheets);
            this.res_o2m_drop = new instance.web.DropMisordered();
            this.render_drop = new instance.web.DropMisordered();
            this.description_line = _t("/");
            this.flag = 1;
            this.start_interval();
        },
        switcher: function(e){
            if($(e.currentTarget).hasClass("oe_timesheet_nav_day")) {
                this.flag = 1;
                this.initialize_contentd();
            } else {
                this.flag = 2;
                this.initialize_content();
            }
        },
        go_to: function(event) {
            var id = JSON.parse($(event.target).data("id"));
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: "account.analytic.account",
                res_id: id,
                views: [[false, 'form']],
                target: 'current'
            });
        },
        query_sheets: function() {
            var self = this;
            if (self.updating)
                return;
            var commands = this.field_manager.get_field_value("timesheet_ids");
            this.res_o2m_drop.add(new instance.web.Model(this.view.model).call("resolve_2many_commands", ["timesheet_ids", commands, [], 
                    new instance.web.CompoundContext()]))
                .done(function(result) {
                self.querying = true;
                self.set({sheets: result});
                self.querying = false;
            });
        },
        update_sheets: function() {
            var self = this;
            if (self.querying)
                return;
            self.updating = true;
            self.field_manager.set_values({timesheet_ids: self.get("sheets")}).done(function() {
                self.updating = false;
            });
        },
        initialize_field: function() {
            instance.web.form.ReinitializeWidgetMixin.initialize_field.call(this);
            var self = this;
            var field = self.initialize_content;
            if(this.flag == 1)
                field = self.initialize_contentd;
            else
                field = self.initialize_content;
            self.on("change:sheets", self, field);
            self.on("change:date_to", self, field);
            self.on("change:date_from", self, field);
            self.on("change:user_id", self, field);
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
                    self.week = _.first(self.dates).getWeek();
                    self.last_week = _.last(self.dates).getWeek();
                }
                self.accounts = accounts;
                self.account_names = account_names;
                self.default_get = default_get;
                //real rendering
                self.display_data();
            });
        },
        destroy_content: function() {
            if (this.dfm) {
                this.dfm.destroy();
                this.dfm = undefined;
            }
        },
        is_valid_value:function(value){
            var split_value = value.split(":");
            var valid_value = true;
            if (split_value.length > 2)
                return false;
            _.detect(split_value,function(num){
                if(isNaN(num)){
                    valid_value = false;
                }
            });
            return valid_value;
        },
        display_data: function() {
            var self = this;
            self.$el.html(QWeb.render("hr_timesheet_sheet.WeeklyTimesheet", {widget: self}));
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
            self.$(".oe_timesheet_weekly_adding a").click(_.bind(this.init_add_account, this));
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
            self.$(".oe_timesheet_weekly_add_row a").click(function() {
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
        sync: function() {
            var self = this;
            self.setting = true;
            if(this.flag == 1)
                self.set({sheets: this.generate_o2m_valued()});
            else
                self.set({sheets: this.generate_o2m_value()});
            self.setting = false;
        },
        //converts hour value to float
        parse_client: function(value) {
            return instance.web.parse_value(value, { type:"float_time" });
        },
        //converts float value to hour
        format_client:function(value){
            return instance.web.format_value(value, { type:"float_time" });
        },
        generate_o2m_value: function() {
            var self = this;
            var ops = [];
            var ignored_fields = self.ignore_fields();
            _.each(self.accounts, function(account) {
                var auth_keys = _.extend(_.clone(account.account_defaults), {
                    name: true, amount:true, unit_amount: true, date: true, account_id:true, date_start: true,
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
                            tmp = _.omit(tmp, ignored_fields);
                            ops.push(tmp);
                        }
                    });
                });
            });
            return ops;
        },
        
        
        
        
        
        
        //--------------------------------------------------Day----------------------------------------
        initialize_contentd: function() {
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
                                return _.sortBy(day.account_group, function(el) {
                                    return new_account_names[el.account_id];
                                });
                            });
                        });
                    });
            })).then(function(result) {
                self.new_dates = dates;
                self.account_names = new_account_names;
                self.days = days;
                if(self.days.length) {
                    self.week = _.first(self.days).week;
                    self.last_week = _.last(self.days).week;
                }
                self.default_get = default_get;
                //real rendering
                self.display_datad();
            });
        },
        generate_o2m_valued: function() {
            var self = this;
            var ops = [];
            var ignored_fields = self.ignore_fields();
                _.each(self.days, function(day) {
                    var auth_keys = _.extend(_.clone(day.account_defaults), {
                        name: true, amount:true, unit_amount: true, date: true, account_id:true, date_start: true,
                    });
                    _.each(day.account_group, function(account) {
                        _.each(account,function(line){
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
                            tmp = _.omit(tmp, ignored_fields);
                            ops.push(tmp);
                        });
                    });
                });
            return ops;
        },
        display_datad: function() {
            var self = this;
            if(self.days.length)
                self.week = self.days[self.count].week;
            this.$el.html(QWeb.render("hr_timesheet_sheet.DailyTimesheet", {widget: self}));
            if (self.days.length) {
                var day_count = self.count;
                 _.each(self.days[self.count].account_group, function(account){
                    if (!self.get('effective_readonly')){
                        self.get_boxd(account).val(self.sum_boxd(account, true)).change(function() {
                            var num = $(this).val();
                            if(self.is_valid_value(num)){
                                    num = (num == 0)?0:Number(self.parse_client(num));
                            }
                            if (isNaN(num)) {
                                $(this).val(self.sum_boxd(account, true));
                            } else {
                                account[0].unit_amount += num - self.sum_boxd(account);
                                var product = (account[0].product_id instanceof Array) ? account[0].product_id[0] : account[0].product_id
                                var journal = (account[0].journal_id instanceof Array) ? account[0].journal_id[0] : account[0].journal_id
                                self.defs.push(new instance.web.Model("hr.analytic.timesheet").call("on_change_unit_amount", [[], product, account[0].unit_amount, false, false, journal]).then(function(res) {
                                    account[0].amount = res.value.amount || 0;
                                    self.display_totalsd();
                                    self.sync();
                                }));
                                if(!isNaN($(this).val())){
                                    $(this).val(self.sum_boxd(account, true));
                                }
                            }
                        });
                    } else {
                        self.get_boxd(account).html(self.sum_boxd(account, true));
                    }
                });
                self.display_totalsd();
                self.toggle_active(self.count);
            }
        },
        init_add_accountd: function() {
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
            self.$(".oe_timesheet_daily_add_row a").click(function() {
                var id = self.account_m2o.get_value();
                if (id === false) {
                    self.dfm.set({display_invalid_fields: true});
                    return;
                }
                var ops = self.generate_o2m_valued();
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
        renderElement: function(){
            this._super.apply(this, arguments);
            this.reset();
        },
        reset: function(){
            this.count = 0;
        },
        copy_accounts: function(e) {
            var self = this;
            var index = this.count;
            _.each(this.days[index],function(){
                if(_.isEmpty(self.days[index].account_group)){
                    if(index == 0){
                        var max_id = 0, dt;
                        new instance.web.DataSet(self, "hr.analytic.timesheet", self.view.dataset.get_context()).read_slice(["id", "date"]).done(function(res){
                            for(var i = 0; i < res.length; i++)
                                if(res[i].id > max_id){
                                    max_id = res[i].id;
                                    dt = res[i].date;
                                }
                            new instance.web.DataSetSearch(self, 'hr.analytic.timesheet', self.view.dataset.get_context(),
                                [['date','=',dt]]).read_slice([],{}).done(function(res){
                                    self.copy_data(_.groupBy(res, "account_id"));
                                });
                        });
                        return;
                    }
                    else
                        index -= 1;
                }
            });
            self.copy_data(JSON.parse(JSON.stringify(this.days[index].account_group)));
        },
        copy_data: function(data) {
            var self = this;
            self.days[self.count].account_group = data;
            _.each(self.days[self.count].account_group,function(account) {
                var d = self.days[self.count].day.toString("yyyy-MM-dd")
                _.each(account,function(account) {
                    account.date = d;
                    account.name = self.description_line;
                    account.date_start = false;
                    account.date_diff_hour = account.date_diff_minute = 0;
                });
            });
            this.sync();
            this.initialize_contentd();
        },
        addDescription: function(e) {
            var self=this;
            var index = this.$(e.target).attr("data-day-count") || this.$(e.srcElement).attr("data-day-count"); 
            var input = this.$(".oe_edit_input")[index];
            var act_id = this.$(e.target).attr("data-account");
            var account = this.days[this.count].account_group[act_id];
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
        start_interval : function(){
            var self = this;
            setInterval(function(){
                self.$el.find("i.start_clock").each(function(){
                    var el_hour = $(this).parent().parent().find("span.hour");
                    var el_minute = $(this).parent().parent().find("span.minute");
                    var minute = parseInt(el_minute.text()) + 1;
                    if(minute > 60) {
                        el_hour.text(parseInt(el_hour.text()) + 1);
                        minute = 0;
                    }
                    el_minute.text(minute);
                });
            }, 60000);
        },
        get_current_UTCDate: function() {
            var d = new Date();
            return d.getUTCFullYear() +"-"+ (d.getUTCMonth()+1) +"-"+d.getUTCDate()+" "+d.getUTCHours()+":"+d.getUTCMinutes()+":"+d.getUTCSeconds();//+"."+d.getUTCMilliseconds();
        },
        get_date_diff: function(new_date, old_date){
            var difference = Date.parse(new_date).getTime() - Date.parse(old_date).getTime();
            return Math.floor(difference / 3600000 % 60) + ":" + Math.floor(difference / 60000 % 60);
        },
        timer: function(e) {
            var self = this;
            var index = this.$(e.currentTarget).attr("data-day-count") || this.$(e.srcElement).attr("data-day-count"); 
            var input = this.$(".oe_timer")[index];
            var act_id = this.$(e.currentTarget).attr("data-account");
            var account = this.days[this.count].account_group[act_id];
            var el_clock = $(input).find(".clock");
            var el_cog = $(input).find(".cog");
            if(!el_clock.hasClass("start_clock")){
                 new instance.web.DataSetSearch(this, 'hr.analytic.timesheet', this.view.dataset.get_context(),
                    [['user_id','=',self.get('user_id')],['date_start', '!=', false]])
                    .read_slice(['id', 'date_start', 'unit_amount'], {}).done(function(res){
                        _.each(res, function(i){
                            i.unit_amount += self.parse_client(self.get_date_diff(self.get_current_UTCDate(), i.date_start));
                            new instance.web.Model("hr.analytic.timesheet").call('write',[[i.id], {'date_start' : false, 'unit_amount' : i.unit_amount}]);
                        });
                    }).done(function(){
                        for(var i = 0; i < self.days.length; i++){
                            $.each(self.days[i].account_group, function(j) {
                                var data = self.days[i].account_group[j][0];
                                if(data.date_start){
                                    data.unit_amount += self.parse_client(self.get_date_diff(self.get_current_UTCDate(), data.date_start));
                                    data.date_start = false;
                                    data.date_diff_hour = data.date_diff_minute = 0;
                                }
                            });
                        }
                        account[0].date_start = self.get_current_UTCDate();
                        self.sync();
                        account[0].date_diff_hour = account[0].date_diff_minute = 0;
                        self.view.save();
                        self.display_datad();
                    });
            } else {
                account[0].unit_amount += self.parse_client(self.get_date_diff(self.get_current_UTCDate(), account[0].date_start));
                account[0].date_start = false;
                self.sync();
                account[0].date_diff_hour = account[0].date_diff_minute = 0;
                self.view.save();
                self.display_datad();
            }
        },
        toggle_active: function(day_count) {
            this.$el.find(".oe_day_button[data-day-counter|="+day_count+"]").addClass("oe_active_day").siblings().removeClass("oe_active_day")
            this.$el.find(".oe_day_button[data-day-counter|="+day_count+"] span").removeClass("oe_display_day_total").siblings().addClass("oe_display_day_total");
            if(this.count == 0)
                this.$el.find(".to_day").removeClass("oe_day_button").addClass("oe_fday_button");
        },
        navigateAll: function(e){
            var self = this;
            if(this.dfm)
                this.destroy_content();
            if($(e.target).hasClass("prev_day"))
                this.navigatePrev();
            if($(e.target).hasClass("next_day"))
                this.navigateNext();
            if($(e.target).hasClass("to_day")) {
                self.count = 0;
                for(var i = 0; i < this.days.length; i++)
                    if(this.days[i].day.toString("yyyy/M/d") == new Date().toString("yyyy/M/d"))
                        self.count = i;
            }
            if($(e.target).hasClass("oe_header") || $(e.target).hasClass("oe_display_day_total"))
                this.navigateDays(e);
            this.week = this.days[this.count].week;
            this.display_datad();
        },
        navigateNext: function() {
            if(this.count == this.days.length-1)
                this.count = 0;
            else 
                this.count+=1;
        },
        navigatePrev: function() {
            if (this.count==0)
                this.count = this.days.length-1;
            else
                this.count -= 1;
        },
        navigateDays: function(e){
            this.count = parseInt($(e.target).attr("data-day-counter"), 10);
        },
        get_desc: function(account,day_count){
            var input_box = this.$('.oe_edit_input')[day_count];
            return $(input_box).val(account[0].name);
        },
        get_boxd: function(account) {
            return this.$('.oe_timesheet_daily_box[data-account="' + account[0].account_id + '"]');
        },
        set_day_total: function(day_count, total) {
            return this.$el.find('[data-day-total = "' + day_count + '"]').html(this.format_client(total));;
        },
        get_super_totald: function() {
            return this.$('.oe_header_total');
        },
        sum_boxd: function(account, show_value_in_hour) {
            var line_total = 0;
            _.each(account, function(line){
                line_total += line.unit_amount;
            });
            return (show_value_in_hour && line_total != 0)?this.format_client(line_total):line_total;
        },
        display_totalsd: function() {
            var self = this;
            var day_tots = _.map(_.range(self.days.length), function() { return 0 });
            var super_tot = 0;
            var acc_tot = 0;
            _.each(self.days, function(days,day_count) {
                _.each(days.account_group,function(account){
                    if(account[0].date_start){
                        var difference = self.get_date_diff(self.get_current_UTCDate(), account[0].date_start).split(":");
                        account[0]["date_diff_hour"] = difference[0];
                        account[0]["date_diff_minute"] = difference[1];
                    }
                    var sum = self.sum_boxd(account);
                    acc_tot = acc_tot +  sum;
                    day_tots[day_count] += sum;
                    super_tot += sum;
                });
            });
            _.each(_.range(self.days.length), function(day_count) {
                self.set_day_total(day_count, day_tots[day_count]);
            });
            self.get_super_totald().html("Total : <br/><small>" + (self.format_client(super_tot)) + "</small>");
        },
    });
    instance.web.form.custom_widgets.add('weekly_timesheet', 'instance.hr_timesheet_sheet.WeeklyTimesheet');
};
