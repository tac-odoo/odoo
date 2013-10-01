/*------------------------------*
 * Multi Object OpenERP Calendar*
 *------------------------------*/

openerp.core_calendar = function(instance) {

var _t = instance.web._t,
   _lt = instance.web._lt;
var QWeb = instance.web.qweb;

instance.web.form.widgets.add('colorpicker', 'instance.core_calendar.ColorPicker');

instance.core_calendar.ColorPicker = instance.web.form.FieldChar.extend({
    template: 'FieldColorpicker',
    destroy_content: function() {
        this.$el.find('input').colorpicker('destroy');
        this._super();
    },
    initialize_content: function() {
        this._super();
        if (!this.get("effective_readonly")) {
            var options = {
                history: false,
                showOn: 'button',
                displayIndicator: false,
                strings: [
                    _t('Theme Colors'),
                    _t('Standard Colors'),
                    _t('More Colors'),
                    _t('Less Colors'),
                    _t('Back to Palette'),
                    _t('History'),
                    _t('No history yet.'),
                ].join(','),
            }
            this.$el.find('input').colorpicker(options);
        }
    },
    render_value: function() {
        this._super();
        var show_value = this.format_value(this.get('value'), '');
        if (!this.get("effective_readonly")) {
            this.$el.find('input').colorpicker({'color': show_value});
        } else {
            this.$(".oe_form_char_content").css('color', show_value);
        }
    },
});


instance.core_calendar.SelectOptionForm = instance.web.Widget.extend({
    template: 'SelectOptionFormPopup.render',
    select_options: function(options_list, template, options) {
        this.option_selected = $.Deferred();
        this.options = options || {};
        _.defaults(this.options, {});
        this.options_list = options_list;
        this.options_template = template;
        this.choosen_option = null;
        if (this.options_list.length == 1) {
            // only 1 option to choose, don't ask user
            this.choosen_option = options_list[0];
            this.exit_selected(true);
        } else {
            this.display_popup();
        }
        return this.option_selected;
    },
    /* Display aind internal */
    start: function() {
        this._super();
        this.setup_dialog_view();
    },
    exit_selected: function(selected) {
        if (selected) {
            this.option_selected.resolve(this.choosen_option);
        } else {
            this.option_selected.reject();
        }
        this.destroy();
    },
    destroy: function () {
        if (this.$el.is(":data(dialog)")) {
            this.$el.dialog('close');
        }
        this._super();
    },
    setup_dialog_view: function() {
        var self = this;
        // bind button to code action
        this.$buttonpane.html(QWeb.render("SelectOptionFormPopup.buttons", {}));
        self.$buttonpane.find(".oe_selectoptionformpopup-form-cancel")
            .click(function(ev) {
                self.exit_selected(false);
            });
        // display all available options
        this.view = this.$el.find('.oe_popup_form');
        this.view.html(QWeb.render(this.options_template, {options: this.options_list, widget: self}));
        this.view.find('.oe_button').click(function(evt) {
            var button_index = $(evt.target).attr('index');
            self.choosen_option = self.options_list[button_index];
            self.exit_selected(true);
        });
    },
    display_popup: function() {
        var self = this;
        this.renderElement();
        var dialog = new instance.web.Dialog(this, {
            width: 'auto',
            min_width: '300px',
            dialogClass: 'oe_act_window',
            close: function(ev) {
                self.exit_selected(false);
            },
            destroy_on_close: true,
            title: this.options.title || "",
        }, this.$el).open();
        this.$buttonpane = dialog.$buttons;
        this.start();
    },

});

instance.web_calendar.CalendarView = instance.web_calendar.CalendarView.extend({
    init: function(parent, dataset, view_id, options) {
        var self = this;
        this._super(parent, dataset, view_id, options);
        if (self.model == 'core.calendar.event') {
            self.calendar_model = new instance.web.Model('core.calendar', dataset.get_context());
            self.subscribed_calendars = [];
            self.reccurent_field = null;
            $.when(this.has_been_loaded, this.ready).done(function() {
                // Get all subscribed calendar and display them in sidebar
                self.calendar_model.call('get_subscribed').done(function(calendars) {
                    _.each(calendars, function(cal) {
                        self.subscribed_calendars.push(_.extend(cal, {
                            'label': cal.name,
                            'value': cal.id,
                        }));
                    });
                    self.sidebar.filter.events_loaded(self.subscribed_calendars);
                });
            });
            $.when(this.has_been_loaded).done(function() {
                // check for recurrent field in the views
                for (var fld = 0; fld < self.fields_view.arch.children.length; fld++) {
                    var fld_node = self.fields_view.arch.children[fld];
                    var fld_options = instance.web.py_eval(fld_node.attrs.options || '{}');
                    if (fld_options.calendar_recurrent_field) {
                        self.recurrent_field = fld_node.attrs.name;
                    }
                };
                if (self.recurrent_field) {
                    // remove recurrent field from info_fields if present
                    self.info_fields = _.filter(self.info_fields, function(f){ return f != self.recurrent_field });
                }
            })
        }
        // For Limit Handling
        this.resource_model = new instance.web.Model('core.calendar.timeline');
    },
    init_scheduler: function() {
        scheduler.config.check_limits = true; // required for display marked-spans
        scheduler.config.display_marked_timespans = true;
        this._super();
        this.scheduler_attachEvent('onBeforeDrag', function(id) {
            if (!id) return true;
            return !this.getEvent(id).readonly;
        });
    },
    is_agenda_by_calendar: function() {
        return this.model && this.color_field && this.color_field == 'calendar_id';
    },
    events_loaded: function(events, fn_filter, no_filter_reload) {
        if (this.is_agenda_by_calendar()) {
            // do not reload filter for 'Agenda' has they're preloaded and must stay this way.
            no_filter_reload = true;
        }
        this._super(events, fn_filter, no_filter_reload);
    },
    convert_event: function(evt) {
        var self = this;
        var converted_event = this._super(evt);
        if (this.model == 'core.calendar.event') {
            if (this.is_agenda_by_calendar() && evt[this.color_field]) {
                // force calendar custom color, not default indexed-color palette
                var filter = evt[this.color_field];
                var filter_value = (typeof filter === 'object') ? filter[0] : filter;
                var filter_item = _.find(self.subscribed_calendars,
                                         function(cal){ return cal.value == filter_value });
                converted_event.color = filter_item.color;
                converted_event.textColor = '#ffffff';
            }
            if (this.recurrent_field) {
                converted_event['recurrent'] = evt[this.recurrent_field];
            }
            var evi = self.virtual_event_id_to_real(evt.id);
            _.each(self.subscribed_calendars, function(calendar) {
                if (calendar.id == evi.calendar_id) {
                    if (!calendar.access.write) {
                        converted_event.readonly = true;
                    }
                }
            });
        }
        return converted_event;
    },
    virtual_event_id_to_real: function(virtual_event_id) {
        if (!virtual_event_id) {
            return virtual_event_id;
        }
        var virtual_separator_idx = virtual_event_id.indexOf('-');
        if (virtual_separator_idx > -1) {
            var calendar_id = parseInt(virtual_event_id.slice(0, virtual_separator_idx))
            var real_id = virtual_event_id.slice(virtual_separator_idx+1)
            if (real_id.match(/^[0-9]*$/)) {
                real_id = parseInt(real_id);
            }
            return {calendar_id: calendar_id, real_id: real_id};
        }
        else {
            return {calendar_id: null, real_id: virtual_event_id};
        }
    },
    get_virtual_id_parts: function(virtual_event_id) {
        var parts = {
            calendar_id: null,    // #1
            base_id: null,        // #2
            recurrent_date: null, // #3
            id_full: virtual_event_id, // calendar_id + base_id + recurrent_date
            id_virtual: null,          // base_id + recurrent_date
            id_without_recurrent: null // calendar_id + base_id
        };
        if (virtual_event_id && typeof(virtual_event_id) === 'string') {
            var _virtparts = virtual_event_id.split('-');
            if (_virtparts.length >= 2) {
                parts.calendar_id = parseInt(_virtparts[0]);
                parts.base_id = parseInt(_virtparts[1]);
                parts.id_without_recurrent = _virtparts.slice(0, 2).join('-');
                parts.id_virtual = _virtparts.slice(1).join('-');
            }
            if (typeof(parts.id_virtual) === 'string' && parts.id_virtual.match(/[0-9]/)) {
                parts.id_virtual = parseInt(parts.id_virtual);
            }
            if (_virtparts.length >= 3) {
                parts.recurrent_date = _virtparts[2];
            }
        }
        return parts;
    },
    slow_create: function(event_id, event_obj) {
        var self = this;
        if (this.model == 'core.calendar.event') {

            var calendar_list = _.filter(self.subscribed_calendars, function(calendar) {
                return !!calendar.access.create;
            });

            var optionpop = new instance.core_calendar.SelectOptionForm(this);
            optionpop.select_options(calendar_list,
                'SelectSubsribedCalendar.render',
                {title: _.str.sprintf(_t("Select Calendar"))}
            ).fail(function() {
                scheduler.deleteEvent(event_id);
            }).done(function(calendar) {

                    var calendar_form_view_id = (typeof calendar.action_form_view_id == 'object')
                                                    ? calendar.action_form_view_id[0]
                                                    : calendar.action_form_view_id;

                    if (self.current_mode() === 'month') {
                        event_obj['start_date'].addHours(8);
                        if (event_obj._length === 1) {
                            event_obj['end_date'] = new Date(event_obj['start_date']);
                            event_obj['end_date'].addHours(1);
                        } else {
                            event_obj['end_date'].addHours(-4);
                        }
                    }
                    var defaults = {};
                    _.each(self.get_event_data(event_obj, calendar), function(val, field_name) {
                        defaults['default_' + field_name] = val;
                    });
                    var something_saved = false;
                    var pop = new instance.web.form.FormOpenPopup(self);
                    pop.show_element(calendar.action_res_model, null, self.dataset.get_context(defaults), {
                        title: _.str.sprintf(_t("Create: %s"), calendar.name),
                        view_id: calendar_form_view_id,
                    });
                    pop.on('closed', self, function() {
                        if (!something_saved) {
                            scheduler.deleteEvent(event_id);
                        }
                    });
                    pop.on('create_completed', self, function(id) {
                        // force full-reload to catch new recurrent event
                        self.ranged_search();
                    });
            });
        } else {
            this._super(event_id, event_obj);
        }
    },
    open_event: function(event_id) {
        var self = this;
        var index = this.dataset.get_id_index(event_id);
        if (this.model == 'core.calendar.event' && index !== null) {
            var id_from_dataset = this.dataset.ids[index]; // dhtmlx scheduler loses id's type
            var id_parts = self.get_virtual_id_parts(id_from_dataset);
            var id = id_parts.id_virtual;

            var EDIT_ONE = 1, EDIT_ALL = 2;
            var edit_mode = EDIT_ONE;
            var edit_mode_selected = $.Deferred();
            var optionpop = new instance.core_calendar.SelectOptionForm(this);
            var event_obj = scheduler.getEvent(event_id);
            if (event_obj.recurrent) {
                var options = [
                    {'value': EDIT_ONE, 'label': _t('Edit just this occurrence')},
                    {'value': EDIT_ALL, 'label': _t('Edit all occurences')},
                ];
                optionpop.select_options(options,
                    'SelectRecurrentActionMode.render',
                    {'title': _.str.sprintf(_t("Event is recurrent"))}
                ).fail(function() {
                    edit_mode_selected.reject();
                }).done(function(choosen_mode) {
                    edit_mode = choosen_mode.value;
                    if (edit_mode == EDIT_ALL) {
                        id = id_parts.base_id;
                    };
                    edit_mode_selected.resolve();
                });
            } else {
                edit_mode_selected.resolve();
            }

            $.when(edit_mode_selected).done(function() {

                var calendar = _.find(self.subscribed_calendars, function(cal) { return cal.value == id_parts.calendar_id});
                var calendar_form_view_id = (typeof calendar.action_form_view_id == 'object')
                                                ? calendar.action_form_view_id[0]
                                                : calendar.action_form_view_id;
                var pop = new instance.web.form.FormOpenPopup(self);
                pop.show_element(calendar.action_res_model, id, self.dataset.get_context(), {
                    title: _.str.sprintf(_t("Edit: %s"), calendar.name),
                    view_id: calendar_form_view_id,
                });
                pop.on('write_completed', self, function(){
                    if (edit_mode == EDIT_ALL) {
                        self.ranged_search(); // force full reload
                    } else {
                        self.reload_event(id_from_dataset);
                    }
                });

            })

        } else {
            return this._super(event_id);
        }
    },
    delete_event: function(event_id, event_obj) {
        var self = this;
        var index = this.dataset.get_id_index(event_id);
        if (this.model == 'core.calendar.event' && index !== null) {
            var id_from_dataset = this.dataset.ids[index]; // dhtmlx scheduler loses id's type
            var id_parts = self.get_virtual_id_parts(id_from_dataset);
            var optionpop = new instance.core_calendar.SelectOptionForm(this);
            var DELETE_ONE = 1, DELETE_ALL = 2;
            if (event_obj.recurrent) {
                var options = [
                    {'value': DELETE_ONE, 'label': _t('Delete just this occurrence')},
                    {'value': DELETE_ALL, 'label': _t('Delete all occurences')},
                ];
                optionpop.select_options(options,
                    'SelectRecurrentActionMode.render',
                    {'title': _.str.sprintf(_t("Event is recurrent"))}
                ).fail(function() {
                    // User cancelled - re-add event back on schedule view
                    scheduler._events[event_obj.id] = event_obj;
                    scheduler.event_updated(event_obj);

                }).done(function(choosen_mode) {
                    if (choosen_mode.value == DELETE_ALL) {
                        self.dataset.unlink(id_parts.id_without_recurrent)
                            .done(function(){ self.ranged_search() });
                    } else {
                        self.dataset.unlink(event_id);
                    }
                });
                return;
            }
        }
        this._super(event_id, event_obj);
    },
    get_event_data: function(event_obj, calendar_obj) {
        if (this.model == 'core.calendar.event' && !!calendar_obj) {
            var data = {};
            data[calendar_obj.fields.name] = event_obj.text || scheduler.locale.labels.new_event;
            var field_start = calendar_obj.fields.date_start;
            data[field_start] = calendar_obj.fields_type[field_start] == 'date'
                                ? instance.web.date_to_str(event_obj.start_date)
                                : instance.web.datetime_to_str(event_obj.start_date);
            if (calendar_obj.date_mode == 'end') {
                var field_end = calendar_obj.fields.date_end;
                data[field_end] = calendar_obj.fields_type[field_end] == 'date'
                                  ? instance.web.date_to_str(event_obj.end_date)
                                  : instance.web.datetime_to_str(event_obj.end_date);
            }
            if (calendar_obj.date_mode == 'duration') {
                var diff_seconds = Math.round((event_obj.end_date.getTime() - event_obj.start_date.getTime()) / 1000);
                data[calendar_obj.fields.duration] = diff_seconds / 3600;
            }
            return data;
        }
        return this._super(event_obj);
    },
    refresh_scheduler: function() {
        console.log('refresh scheduler', this.range_start, this.range_stop);
        if (this.range_start || this.range_stop) {
            this.refresh_resource_unavailibility();
        }
        // scheduler.addMarkedTimespan({
        //     days: 0,
        //     zones: [0, 60*24],
        //     css: "oe_marked_timespan",
        // })
        return this._super();
    },
    refresh_resource_unavailibility: function() {
        // clear all previous marked timespans
        console.log('refresh resource unavailibility');
        scheduler._marked_timespans = { global: {} };
        scheduler._marked_timespans_ids = {};
        var range_from = this.range_start;
        if (range_from) {
            if (!scheduler.config.start_on_monday) {
                range_from = range_from.clone().addDays(-1);
            }
            range_from = instance.web.datetime_to_str(range_from);
        }
        var range_to = this.range_stop;
        if (range_to) {
            range_to = instance.web.datetime_to_str(range_to);
        }
        var self = this;
        var resource_model = 'res.users'
        var resource_ids = [instance.session.uid];
        var getresource_kwargs = {};

        if (!this.search_group_by_key) {
            // actually only display availiblity infos if the calendar only
            // represent a unique resource.
            // This is always true in group_by mode, but not in standard filtered
            // model. So currently we disable all availibility infos if we're not
            // if a group_by mode
            // FIXME: detected, based on domain info if filters represent only 1
            //        resource
            scheduler.updateView();
            return;
        }

        if (this.search_group_by_key) {
            resource_model = self.dataset.model;
            resource_ids = _.pluck(self.search_groups, 'key');
            getresource_kwargs['group_by_field'] = self.search_group_by_key;
        }

        this.resource_model.call('get_resource_unavailibility', [
            resource_model,
            resource_ids,
            range_from,
            range_to,
        ],
        _.extend(getresource_kwargs, {
            context: this.dataset.get_context(),
        })).done(function(unavails) {
            if (unavails && unavails.length) {
                _.each(unavails, function(c) {
                    c.start_date = instance.web.str_to_datetime(c.start_date);
                    c.end_date = instance.web.str_to_datetime(c.end_date);
                    if (!self.search_group_by_key) {
                        c.sections = null; // we are is non grouped mode - this must apply globally.
                    }
                    //console.log(c);
                    // console.log('marked_timespan', c);
                    scheduler.addMarkedTimespan(c);
                })
            }
            scheduler.updateView();
        })
        return;
    },
});

instance.web_calendar.SidebarFilter = instance.web_calendar.SidebarFilter.extend({
    events_loaded: function(filters) {
        if (!this.view.is_agenda_by_calendar()) {
            return this._super(filters);
        }
        this.$el.html(QWeb.render('AgendaView.sidebar.calendar', { filters: filters }));
    },
});

};