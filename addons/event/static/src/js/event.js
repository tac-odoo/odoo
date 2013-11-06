
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

    PreplanningCellValidator = function (value, callback) {
        callback(/^-?\d*\.?\d*$/.test(value) && value >= 0);
    };

    HeaderCellRenderer = function (instance, TD, row, col, prop, value, cellProperties) {
        Handsontable.TextCell.renderer.apply(this, arguments);
        instance.view.wt.wtDom.addClass(TD, 'htHeaderCell');
    };

    SlotCountHeaderCellRenderer = function (instance, TD, row, col, prop, value, cellProperties) {
        Handsontable.TextCell.renderer.apply(this, arguments);
        instance.view.wt.wtDom.addClass(TD, 'htSlotCountHeaderCell');
        var is_cell_valid = cellProperties.is_cell_valid;
        if (cellProperties.is_cell_valid && !cellProperties.is_cell_valid(row, col)) {
            if (typeof value == 'number' ? value > 0 : true) {
                instance.view.wt.wtDom.addClass(TD, 'htInvalid');
            }
        }
    };

    PreplanningCellRendered = function (instance, TD, row, col, prop, value, cellProperties) {
        Handsontable.NumericCell.renderer.apply(this, arguments);
        instance.view.wt.wtDom.addClass(TD, 'htPreplanningCell');
        var is_cell_valid = cellProperties.is_cell_valid;
        if (cellProperties.is_cell_valid && !cellProperties.is_cell_valid(row, col)
                && typeof value == 'number' && value > 0) {
            instance.view.wt.wtDom.addClass(TD, 'htInvalid');
        } else {
            instance.view.wt.wtDom.removeClass(TD, 'htInvalid');
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
            this.COLUMN_HEADERS = 5;
        },
        query_events: function() {
            var self = this;
            if (self.updating)
                return;
            var commands = this.field_manager.get_field_value("children_ids");
            var res_o2m_fields = ['date_begin', 'duration', 'planned_week_date', 'content_id', 'group_id', 'state'];
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
        resize_content: function() {
            var $preplanning = this.$el.find('#preplanning-table');
            if (!!$preplanning) {
                var sizes = this.preplanning_recompute_size();
                $preplanning.width(sizes[0]);
                $preplanning.height(sizes[1]);
                $preplanning.handsontable('render');
            }
        },
        destroy_content: function() {
            instance.web.bus.off('resize', this, this.resize_content);
            this._super.apply(this, arguments);
        },
        initialize_content: function() {
            var self = this;
            if (self.setting) {
                return;
            }
            instance.web.bus.on('resize', this, this.resize_content);
            // don't render anything until we have date_begin, date_end and event_id
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
                self.weeks = result.weeks || [];
                _.each(self.weeks, function (w, i) {
                    self.weeks[i].start = instance.web.str_to_datetime(self.weeks[i].start).clearTime();
                    self.weeks[i].stop = instance.web.str_to_datetime(self.weeks[i].stop).clearTime();
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

                self.resize_content();
            });
        },
        generate_matrix: function(contents, weeks, events) {
            var self = this;
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
                var event_startdate = event.date_begin ? instance.web.str_to_datetime(event.date_begin).clearTime()
                                                       : instance.web.str_to_date(event.planned_week_date);
                var ev_content_id = event.content_id.length ? event.content_id[0] : false;
                var ev_group_id = event.group_id.length ? event.group_id[0] : false;
                var week = _.find(self.weeks, function(w) { return event_startdate >= w.start && event_startdate < w.stop;});
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
            this.$el.find('#preplanning-table').handsontable('destroy');
        },
        preplanning_recompute_size: function() {
            var $window = $(window),
                $preplanning = this.$el.find('#preplanning-table'),
                offset = $preplanning.offset();

            availableWidth = $window.width() - offset.left + $window.scrollLeft();
            availableHeight = $window.height() - offset.top + $window.scrollTop();
            return [availableWidth - 16, availableHeight - 26];
        },
        preplanning_is_cell_valid: function(row, col) {
            var content, week, matrix_cell, value;
            // Handle Headers
                if (row === 0 && col >= this.COLUMN_HEADERS) {
                    week = this.weeks[col - this.COLUMN_HEADERS];
                    if (week.slot_used < 0 || week.slot_used > week.slot_count) {
                        return false;
                    }
                    return true;
                }
                if (row >= 1 && col == this.COLUMN_HEADERS - 1) {
                    content = this.contents[row - 1];
                    if (content.slot_used < 0 || content.slot_used > content.slot_count) {
                        return false;
                    }
                    return true;
                }
            if (row > 0 && col > this.COLUMN_HEADERS) {
                // Handle standard cells
                    content = this.contents[row - 1];
                    week = this.weeks[col - this.COLUMN_HEADERS];
                    matrix_cell = this.matrix[content.id][week.id];
                    value = matrix_cell['value'];
                if (content.slot_used < 0
                    || content.slot_used > content.slot_count
                    || week.slot_used < 0
                    || week.slot_used > week.slot_count) {
                    return false;
                }
                return true;
            }
            return true;
        },
        display_data: function() {
            // TODO
            var self = this;

            self.$el.html(QWeb.render("event.EventPreplanning", {widget: self}));

            var data = [
                [_t('Module'), _t('Subject'), _t('Content'), _t('Lang'), _t('Total')],
            ];

            var columnHeads = ['', '', '', '', ''];
            var columnSizes = [120, 120, 120, 40];
            _.each(self.weeks, function(week) {
                columnHeads.push(week.name);
                columnSizes.push(40);
                data[0].push(_.str.sprintf('%d/%d', week.slot_used, week.slot_count));
            });
            // var rowHeads = [_t('Content')];
            var rowCounts = [''];
            _.each(self.contents, function(content, i) {
                // rowHeads.push(content.name);

                var row_count = _.str.sprintf('%d/%d', content.slot_used, content.slot_count);
                var row = [content.module_name, content.subject_name, content.name, content.lang, row_count];
                _.each(self.weeks, function(week) {
                    row.push(self.matrix[content.id][week.id]['value']);
                });
                data.push(row);
            });

            update_value = function(row, col, old_value, new_value) {
                var content = self.contents[row - 1],
                    week = self.weeks[col - self.COLUMN_HEADERS],
                    matrix_cell = self.matrix[content.id][week.id],
                    delta = new_value - matrix_cell['value'];
                if (delta === 0) {
                    // nothing changed
                    return false;
                }
                week.slot_used += delta;
                content.slot_used += delta;
                matrix_cell['value'] = new_value;

                var ht = self.$el.find('#preplanning-table').handsontable('getInstance');
                ht.setDataAtCell(0, col, _.str.sprintf('%d/%d', week.slot_used, week.slot_count));
                ht.setDataAtCell(row, self.COLUMN_HEADERS - 1, _.str.sprintf('%d/%d', content.slot_used, content.slot_count));
                return true;
            };

            var is_cell_valid = _.bind(self.preplanning_is_cell_valid, self);

            self.$el.find('#preplanning-table').handsontable({
                data: data,
                colHeaders: columnHeads,
                // rowHeaders: rowHeads,
                colWidths: columnSizes,
                contextMenu: false,
                fixedRowsTop: 1,
                fixedColumnsLeft: self.COLUMN_HEADERS,
                autoWrapRow: 1,
                currentRowClassName: 'currentRow',
                currentColClassName: 'currentCol',
                cells: function(row, col, prop) {
                    var cellprops = {};
                    if (row === 0 || col < self.COLUMN_HEADERS) {
                        cellprops.readOnly = true;
                        cellprops.renderer = HeaderCellRenderer;
                        if (row === 0 && col >= self.COLUMN_HEADERS - 1) {
                            cellprops.renderer = SlotCountHeaderCellRenderer;
                            cellprops.is_cell_valid = is_cell_valid;
                        }
                        if (row >= 1 && col == self.COLUMN_HEADERS - 1) {
                            cellprops.renderer = SlotCountHeaderCellRenderer;
                            cellprops.is_cell_valid = is_cell_valid;
                        }
                    } else {
                        cellprops.readOnly = self.get('effective_readonly');
                        cellprops.type = 'numeric';
                        cellprops.allowInvalid = true;
                        cellprops.validator = PreplanningCellValidator;
                        cellprops.is_cell_valid = is_cell_valid;
                        cellprops.renderer = PreplanningCellRendered;
                    }
                    return cellprops;
                },
                afterChange: function(changes, source) {
                    var cell;
                    var hot_instance = this;
                    var need_resync = false;
                    if (changes === null)
                        return;
                    _.each(changes, function(change) {
                        cell = hot_instance.getCellMeta(change[0], change[1]);
                        if (change[0] >= 1 && change[1] >= self.COLUMN_HEADERS && typeof change[3] === 'number') {
                            if (update_value.apply(self, change)) {
                                need_resync = true;
                            }
                        }
                    });
                    if (need_resync) {
                        self.setting = true;
                        var o2m_value = self.generate_o2m_value();
                        self.updating = true;
                        self.field_manager.set_values({children_ids: o2m_value}).done(function() {
                            self.updating = false;
                        });
                        self.setting = false;
                    }
                },
                afterValidate: function(isValid, value, row, col, source) {
                    var cell = this.getCellMeta(row, col);
                    if (!isValid || value === '') {
                        // value is not an number, reject it
                        cell.valid = false;
                        return false;
                    }
                    var content = self.contents[row - 1];
                        week = self.weeks[col - self.COLUMN_HEADERS],
                        matrix_cell = self.matrix[content.id][week.id],
                        delta = value - matrix_cell['value'];

                    if (content.slot_used + delta < 0 || content.slot_used + delta > content.slot_count ||
                        week.slot_used + delta < 0 || week.slot_used + delta > week.slot_count) {
                        // new value doesn't not fit within either week or content ranges
                        cell.valid = false;
                        return false;
                    }
                    cell.valid = true;
                    return true;
                },
            });

            self.$el.find('a.oe_preplanning_export_to_xls').on('click', function() {
                self.preplanning_export_to_xls.apply(self, arguments);
            });
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
        preplanning_export_to_xls: function() {
            var self = this;
            instance.web.blockUI();
            this.session.get_file({
                url: '/event/export/preplanning',
                data: {data: JSON.stringify({
                    event_id: self.get('event_id'),
                    weeks: self.weeks,
                    contents: self.contents,
                    matrix: self.matrix
                })},
                complete: instance.web.unblockUI
            });
        }
    });

    instance.web.form.custom_widgets.add('event_preplanning', 'instance.event.EventPreplanning');
};
