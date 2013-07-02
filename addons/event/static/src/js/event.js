
openerp.event = function(instance) {
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;

/*
# Values: (0, 0,  { fields })    create
#         (1, ID, { fields })    update
#         (2, ID)                remove (delete)
#         (3, ID)                unlink one (target id or target of relation)
#         (4, ID)                link
#         (5)                    unlink all (only valid for one2many)
*/
var commands = {
    // (0, _, {values})
    CREATE: 0,
    'create': function (values) {
        return [commands.CREATE, false, values];
    },
    // (1, id, {values})
    UPDATE: 1,
    'update': function (id, values) {
        return [commands.UPDATE, id, values];
    },
    // (2, id[, _])
    DELETE: 2,
    'delete': function (id) {
        return [commands.DELETE, id, false];
    },
    // (3, id[, _]) removes relation, but not linked record itself
    FORGET: 3,
    'forget': function (id) {
        return [commands.FORGET, id, false];
    },
    // (4, id[, _])
    LINK_TO: 4,
    'link_to': function (id) {
        return [commands.LINK_TO, id, false];
    },
    // (5[, _[, _]])
    DELETE_ALL: 5,
    'delete_all': function () {
        return [5, false, false];
    },
    // (6, _, ids) replaces all linked records with provided ids
    REPLACE_WITH: 6,
    'replace_with': function (ids) {
        return [6, false, ids];
    }
};

    instance.event.EventPreplanning = instance.web.form.FormWidget.extend(instance.web.form.ReinitializeWidgetMixin, {
        init: function() {
            this._super.apply(this, arguments);
            this.set({
                events: null,
                event_id: null,
                date_begin: false,
                date_end: false,
            });
            this.setting = false;
            this.updating = false;
            this.querying = false;
            this.preplaninfo = {defaults: {}}
            this.field_manager.on("field_changed:children_ids", this, this.query_events);
            this.field_manager.on("field_changed:event_id", this, function() {
                this.set({"event_id": this.field_manager.get_field_value("event_id")});
            });
            this.field_manager.on('field_changed:date_begin', this, function() {
                this.set({"date_begin": instance.web.str_to_datetime(this.field_manager.get_field_value("date_begin"))});
            });
            this.field_manager.on('field_changed:date_end', this, function() {
                this.set({"date_end": instance.web.str_to_datetime(this.field_manager.get_field_value("date_end"))});
            });
            this.res_o2m_drop = new instance.web.DropMisordered();
            this.render_drop = new instance.web.DropMisordered();
        },
        query_events: function() {
            var self = this;
            if (self.updating)
                return;
            var commands = this.field_manager.get_field_value("children_ids");
            var res_o2m_fields = ['date_begin', 'duration', 'content_id', 'group_id', 'state'];
            this.res_o2m_drop.add(new instance.web.Model(this.view.model).call("resolve_2many_commands", ["children_ids", commands, res_o2m_fields, 
                    new instance.web.CompoundContext({'filter_event_id': self.get('event_id')})]))
                .done(function(result) {
                self.querying = true;
                self.set({events: result});
                self.querying = false;
            });
        },
        initialize_field: function() {
            instance.web.form.ReinitializeWidgetMixin.initialize_field.call(this);
            var self = this;
            self.on('change:events', self, self.initialize_content);
            self.on('change:date_begin', self, self.initialize_content);
            self.on('change:date_end', self, self.initialize_content);
            self.on('change:event_id', self, self.initialize_content);
        },
        initialize_content: function() {
            var self = this;
            if (self.setting) {
                console.log('initialize content skiped because still in settings...');
                return;
            }
            // don't render anything until we have date_begin, date_end and event_id
            console.log('initialize_content', self.get('date_begin'), self.get('date_end'), self.get('event_id'));
            if (!self.get("date_begin") || !self.get("date_end") || !self.get('event_id') || self.get('events') === null)
                return;
            this.destroy_content();
            // TODO
            var weeks;
            var contents;
            var events;
            return this.render_drop.add(new instance.web.Model('event.event.preplanning').call('get_info',
                [self.get('event_id'),
                 instance.web.datetime_to_str(self.get('date_begin')),
                 instance.web.datetime_to_str(self.get('date_end'))],
                {context: new instance.web.CompoundContext(instance.session.user_context)}).then(function (result) {
                    return result;
                })

            ).then(function(result) {
                // we put all the gathered data in self, then we render
                // console.log('initialize_content, final result', result);
                self.weeks = result.weeks || [];
                _.each(self.weeks, function (w, i) {
                    self.weeks[i].start = instance.web.str_to_datetime(self.weeks[i].start);
                    self.weeks[i].stop = instance.web.str_to_datetime(self.weeks[i].stop);
                });
                self.weeks_map = {};
                _.each(self.weeks, function(week) {
                    self.weeks_map[week.id] = week;
                })
                self.contents = result.contents || [];
                self.contents_map = {};
                _.each(self.contents, function(content) {
                    self.contents_map[content.id] = content;
                })
                self.events = self.get('events') || [];
                self.preplaninfo.defaults = result.defaults || {};

                self.matrix = self.generate_matrix(self.contents, self.weeks, self.events);

                // Display data if events are ready
                self.display_data();
            });
        },
        generate_matrix: function(contents, weeks, events) {
            var self = this;
            console.log('content links', this.content_links);
            var m = {};
            // Initialize matrix
            for (var i=0; i < contents.length; i++)
                contents[i].slot_used = 0;
            for (var i=0; i < weeks.length; i++)
                weeks[i].slot_uesd = 0;
            for (var i=0; i < contents.length; i++) {
                var c = contents[i];
                var cgroups = !_.isEmpty(c.groups) ? c.groups : [false];
                m[c.id] = {};
                for (var j=0; j < weeks.length; j++) {
                    var w = weeks[j];
                    var g = {};
                    _.each(cgroups, function(gid) {
                        g[gid] = [];
                    });
                    m[c.id][w.id] = {'value': 0, 'ids': [], 'groups': g};
                }
            }
            var event_id = self.get('event_id');
            var content_ids = _.pluck(contents, 'id');
            _.each(events, function(event) {
                var event_startdate = instance.web.str_to_datetime(event.date_begin);
                var ev_content_id = event.content_id.length ? event.content_id[0] : false;
                var ev_group_id = event.group_id.length ? event.group_id[0] : false;
                var week = _.find(self.weeks, function(w) { return event_startdate >= w.start && event_startdate <= w.stop});
                var content = self.contents_map[ev_content_id];
                if (!week || !content) {
                    return;
                }

                var cell = m[content.id][week.id];
                try {
                    cell.ids.push({'id': event.id});
                    cell.groups[ev_group_id].push(event.id);
                } catch (err) {
                    debugger;
                }
                var cell_newvalue = _.chain(!_.isEmpty(content.groups) ? content.groups : [false])
                                     .map(function(gid) { return cell.groups[gid].length})
                                     .max().value();
                var cell_delta = cell_newvalue - cell.value
                cell.value = cell_newvalue;
                content.slot_used = content.slot_used + cell_delta;
                week.slot_used = week.slot_used + cell_delta;
            });
            return m
        },
        destroy_content: function() {
            // TODO
            if (!this.get('effective_readonly')) {
                this.$el.find('.oe_preplanning_cell').editable('destroy');
            }
            // TODO: how to destroy fixedTable ?
        },
        display_data: function() {
            // TODO
            var self = this;

            self.$el.html(QWeb.render("event.EventPreplanning", {widget: self}));
            // self.$el.find('#preplanning-data').fixedTable({
            //     'height': 400,
            //     'fixedColumns': 2,
            // })

            if (!self.get('effective_readonly')) {
                self.$el.find('.oe_preplanning_cell').editable(function(value, settings) {
                        var $this = $(this);
                        var content_id = $(this).data('content');
                        var content = self.contents_map[content_id];
                        var week_id = $(this).data('week');
                        var week = self.weeks_map[week_id];
                        var old_value = self.matrix[content_id][week_id]['value'];
                        try {
                            var new_value = parseInt(value.replace(/\W/g, ''));
                        } catch (err) {
                            var new_value = old_value;
                        };
                        var delta = new_value - old_value;
                        // Discard change if new value is not in allowed range
                        // NOTE: we handle a special case allowing user to lower value if there is currently
                        //       more used slot than it should (ex: events manually created)
                        if (_.isNaN(new_value)
                            || new_value === old_value
                            || new_value < 0
                            || (delta < 0 ? (content.slot_used + delta < 0) : (content.slot_used + delta > content.slot_count))
                            || (delta < 0 ? (week.slot_used + delta < 0) : (week.slot_used + delta > week.slot_count))) {
                            return old_value;
                        }
                        value = new_value.toString();
                        content.slot_used = content.slot_used + delta;
                        week.slot_used = week.slot_used + delta;
                        self.matrix[content_id][week_id]['value'] = new_value;
                        // update values
                        self.sync(content, week);
                        return value;
                    }, {
                        'onblur': 'submit',
                        'cssclass': 'inherit',
                        'select': true,
                });
            }
            // TOOD: bind week and content to "open calendar on this week / content"
            // self.$(".oe_timesheet_weekly_adding button").click(_.bind(this.init_add_account, this));
        },
        sync: function(content, week) {
            // TODO
            console.log('syncing sync_preplanning widget');
            var self = this;
            var value = this.matrix[content.id][week.id];

            self.setting = true;
            this.$el.find('td[data-content='+content.id+'].oe_preplanning_content_count').html(_.str.sprintf('%d/%d', content.slot_used, content.slot_count));
            this.$el.find('th[data-week='+week.id+'].oe_preplanning_week_count').html(_.str.sprintf('%d/%d', week.slot_used, week.slot_count));
            var o2m_value = self.generate_o2m_value();
            self.updating = true;
            self.field_manager.set_values({children_ids: o2m_value}).done(function() {
                self.updating = false;
            });
            self.setting = false;
        },
        generate_o2m_value: function() {
            // TODO
            var self = this;
            var ops = [];

            _.each(self.matrix, function(week_values, content_id) {
                var content = self.contents_map[content_id];
                _.each(week_values, function(cell_value, week_id) {
                    var week = self.weeks_map[week_id];
                    var eventcount = cell_value.value;

                    _.each(cell_value.groups, function(ids, group_id) {
                        var delta = eventcount - ids.length;
                        // Adapt ids list (remove excedent, pushing false for new item)
                        if (delta < 0) {
                            _.each(ids.slice(ids.length + delta), function (eventid) {
                                if (eventid !== false) {
                                    ops.push(commands.delete(eventid));
                                }
                            });
                            cell_value.groups[group_id].ids = ids = ids.slice(0, ids.length + delta);
                        }
                        if (delta > 0) {
                            _.each(_.range(delta), function() { ids.push(false)});
                        }
                        // Generate Commands
                        _.each(ids, function(eventid) {
                            if (eventid === false) {
                                ops.push(commands.create(self.get_values_for_new_events(content, week, group_id)));
                            } else {
                                ops.push(commands.link_to(eventid));
                            }
                        });
                    })
                })
            })
            return ops;
        },
        get_values_for_new_events: function(content, week, group_id) {
            var self = this;
            var date_begin = week.start.clone().set({'hour': 8, 'second': 0});
            var date_end = date_begin.clone().add(content.slot_duration).hours();
            var values = _.extend({}, self.preplaninfo.defaults, {
                name: content.name,
                type_id: content.type_id,
                date_begin: instance.web.datetime_to_str(date_begin),
                duration: content.slot_duration,
                content_id: content.id,
                group_id: group_id != 'false' ? parseInt(group_id): false,
            });
            return values;
        },
    });

    instance.web.form.custom_widgets.add('event_preplanning', 'instance.event.EventPreplanning');
};
