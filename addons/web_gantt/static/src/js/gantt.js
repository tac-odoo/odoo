/*---------------------------------------------------------
 * OpenERP web_gantt
 *---------------------------------------------------------*/
openerp.web_gantt = function (instance) {
var _t = instance.web._t,
   _lt = instance.web._lt;
var QWeb = instance.web.qweb;
instance.web.views.add('gantt', 'instance.web_gantt.GanttView');

instance.web_gantt.GanttView = instance.web.View.extend({
    display_name: _lt('Gantt'),
    template: "GanttView",
    view_type: "gantt",
    init: function() {
        var self = this;
        this._super.apply(this, arguments);
        this.has_been_loaded = $.Deferred();
        this.chart_id = _.uniqueId();
    },
    view_loading: function(r) {
        return this.load_gantt(r);
    },
    load_gantt: function(fields_view_get, fields_get) {
        var self = this;
        this.fields_view = fields_view_get;
        this.$el.addClass(this.fields_view.arch.attrs['class']);
        return self.alive(new instance.web.Model(this.dataset.model)
            .call('fields_get')).then(function (fields) {
                self.fields = fields;
                self.has_been_loaded.resolve();
            });
    },
    do_search: function (domains, contexts, group_bys) {
        var self = this;
        self.last_domains = domains;
        self.last_contexts = contexts;
        self.last_group_bys = group_bys;
        // select the group by
        var n_group_bys = [];
        if (this.fields_view.arch.attrs.default_group_by) {
            n_group_bys = this.fields_view.arch.attrs.default_group_by.split(',');
        }
        if (group_bys.length) {
            n_group_bys = group_bys;
        }
        // gather the fields to get
        var fields = _.compact(_.map(["date_start", "date_delay", "date_stop", "progress"], function(key) {
            return self.fields_view.arch.attrs[key] || '';
        }));
        fields = _.uniq(fields.concat(n_group_bys));
        
        return $.when(this.has_been_loaded).then(function() {
            return self.dataset.read_slice(fields, {
                domain: domains,
                context: contexts
            }).then(function(data) {
                return self.on_data_loaded(data, n_group_bys);
            });
        });
    },
    reload: function() {
        if (this.last_domains !== undefined)
            return this.do_search(this.last_domains, this.last_contexts, this.last_group_bys);
    },
    on_data_loaded: function(tasks, group_bys) {
        var self = this;
        var ids = _.pluck(tasks, "id");
        return this.dataset.name_get(ids).then(function(names) {
            var ntasks = _.map(tasks, function(task) {
                return _.extend({__name: _.detect(names, function(name) { return name[0] == task.id; })[1]}, task); 
            });
            return self.on_data_loaded_2(ntasks, group_bys);
        });
    },
    on_data_loaded_2: function(tasks, group_bys) {
        var self = this;
        var default_name = "Gantt View";
        $(".oe_gantt", this.$el).html("");
        
        gantt.config.scale_unit = "month";
    	gantt.config.step = 1;
    	gantt.config.date_scale = "%F, %Y";
    	gantt.config.min_column_width = 20;
    	gantt.config.subscales = [{unit:"day", step:1, date:"%d" }];
        gantt.config.autosize = "y";
        gantt.config.order_branch = true;
        gantt.config.fit_tasks = false;
        gantt.config.grid_width = 200;
        gantt.config.row_height = 25;
        gantt.templates.tooltip_text = function(start,end,task){
            return "<b><u>"+task.text+"</u></b><br/><b>Start date:</b> "+start.format('Y-m-d')+"<br/><b>End date:</b> "+end.format('Y-m-d')+"<br/><b>Duration:</b> " + task.duration + " Hours";
        };
        gantt.config.columns=[{name:"text", label:"Task name", tree:true, width:'*' }];
        gantt.init(this.chart_id);
        gantt.clearAll();
        
        //prevent more that 1 group by
        if (group_bys.length > 0) {
            group_bys = [group_bys[0]];
        }
        // if there is no group by, simulate it
        if (group_bys.length == 0) {
            group_bys = ["_pseudo_group_by"];
            _.each(tasks, function(el) {
                el._pseudo_group_by = default_name;
            });
            this.fields._pseudo_group_by = {type: "string"};
        }
        
        // get the groups
        var split_groups = function(tasks, group_bys) {
            if (group_bys.length === 0)
                return tasks;
            var groups = [];
            _.each(tasks, function(task) {
                var group_name = task[_.first(group_bys)];
                var group = _.find(groups, function(group) { return _.isEqual(group.name, group_name); });
                if (group === undefined) {
                    group = {name:group_name, tasks: [], __is_group: true};
                    groups.push(group);
                }
                group.tasks.push(task);
            });
            _.each(groups, function(group) {
                group.tasks = split_groups(group.tasks, _.rest(group_bys));
            });
            return groups;
        }
        
        var groups = split_groups(tasks, group_bys);
        var tasks = [];
        _.each(groups, function(grp) {
            var percent = 100;
        	var task_start = instance.web.auto_str_to_date(_.reduce(_.pluck(grp.tasks, "date_start"), function(date, memo) {
	    		return memo === undefined || date < memo ? date : memo;
			}, undefined));
        	_.each(grp.tasks, function(task) {
                var task_start = instance.web.auto_str_to_date(task[self.fields_view.arch.attrs.date_start]);
                if (!task_start)
                    return;
                var task_stop;
                if (self.fields_view.arch.attrs.date_stop) {
                    task_stop = instance.web.auto_str_to_date(task[self.fields_view.arch.attrs.date_stop]);
                    if (!task_stop)
                        task_stop = task_start;
                } else {
                    var tmp = instance.web.format_value(task[self.fields_view.arch.attrs.date_delay],
                        self.fields[self.fields_view.arch.attrs.date_delay]);
                    if (!tmp)
                        return;
                    task_stop = task_start.clone().addMilliseconds(tmp * 60 * 60 * 1000);
                }
                if (_.isNumber(task[self.fields_view.arch.attrs.progress]))
                    percent = task[self.fields_view.arch.attrs.progress] || 0;
                var duration = (task_stop.getTime() - task_start.getTime()) / (1000 * 60 * 60);
                duration = parseInt(((duration / 24) * 8) || 1);
                task['date_stop'] = gantt.date.convert_to_utc(task_stop).format("Y-m-d h:i:s");
                tasks.push({
                	id : "t" + task.id,
                	text : task.__name,
                	start_date : task_start.format('d-m-Y'),
                	duration : duration,
                	progress : percent,
                	parent : "p" + grp.name[0]
                });
        	});
        	var task_stop = instance.web.auto_str_to_date(_.reduce(_.pluck(grp.tasks, "date_stop"), function(date, memo) {
        		return memo === undefined || date > memo ? date : memo;
            }, undefined));
        	var duration = (task_stop.getTime() - task_start.getTime()) / (1000 * 60 * 60);
        	gantt.addTask({
            	id : "p" + grp.name[0],
            	text : grp.name == default_name ? default_name : grp.name[1],
            	start_date : task_start.format('d-m-Y'),
            	duration : parseInt(((duration / 24) * 8)) || 1,
            	open : true,
            	progress : percent,
            	parent : "p" + grp.name[0]
            });
        });
        _.each(tasks, function(task) {
        	gantt.addTask(task);
        });
        gantt.render();
        gantt.attachEvent("onAfterTaskDrag", function(id, mode, e){
        	self.on_task_changed(gantt.getTask(id), mode);
        });
    },
    on_task_changed: function(task, mode) {
        var self = this;
        var start = task.start_date;
        var duration = (task.duration / 8) * 24;
        var end = start.clone().addMilliseconds(duration * 60 * 60 * 1000);
        var data = {};
        data[self.fields_view.arch.attrs.date_start] = instance.web.auto_date_to_str(start, self.fields[self.fields_view.arch.attrs.date_start].type);
        if (self.fields_view.arch.attrs.date_stop)
            data[self.fields_view.arch.attrs.date_stop] = instance.web.auto_date_to_str(end, self.fields[self.fields_view.arch.attrs.date_stop].type);
        else
            data[self.fields_view.arch.attrs.date_delay] = duration;
        this.dataset.write(parseInt(task.id.substring(1)), data);
    },
});
};
