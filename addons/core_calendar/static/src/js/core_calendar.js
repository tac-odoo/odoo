/*------------------------------*
 * Multi Object OpenERP Calendar*
 *------------------------------*/

openerp.core_calendar = function(instance) {

var _t = instance.web._t,
   _lt = instance.web._lt;
var QWeb = instance.web.qweb;

// We need to fix this to allow dataTransfer to be passed on drop events
jQuery.event.fixHooks.drop = { props: ['dataTransfer'] };


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
            self.resource_model = new instance.web.Model('core.calendar.timeline');  // for limit management
            self.subscribed_calendars = [];
            self.reccurent_field = null;
            $.when(this.ready).done(function() {
                // Get all subscribed calendar and display them in sidebar
                self.calendar_model.call('get_subscribed').done(function(calendars) {
                    var subscribed_calendars = [];
                    _.each(calendars, function (cal) {
                        subscribed_calendars.push(_.extend(cal, {
                            'label': cal.name,
                            'value': cal.id
                        }));
                    });
                    self.subscribed_calendars = subscribed_calendars;

                    // Allow use to create a new event (option: selectable) if it
                    // has at least one subscribed calendar with 'create' rights.
                    var has_create_right = _(subscribed_calendars)
                            .filter(function (cal) { return cal.access.create; })
                            .length > 0;
                    self.$calendar.data('fullCalendar').options.selectable = has_create_right && !self.options.read_only_mode;
                });
            });
        }
    },
    view_loading: function (fv) {
        // check if view containt specific field for recurrency, which will defined as:
        // <field name="NAME" options="{'calendar_recurrent_field'}"/>
        for (var fld=0; fld < fv.arch.children.length; fld++) {
            if (fv.arch.children[fld].tag === 'field') {
                var field_attrs = fv.arch.children[fld].attrs || {};
                var field_options = instance.web.py_eval(field_attrs.options || '{}');
                if (field_options.calendar_recurrent_field) {
                    this.recurrent_field = field_attrs.name;
                }
            }
        }
        return this._super.apply(this, arguments);
    },
    get_fc_init_options: function () {
        var self = this;

        return $.extend(this._super.apply(this, arguments), {
            select: function (start_date, end_date, all_day, _js_event, _view) {
                var item_data = {
                    start: start_date,
                    end: end_date,
                    allDay: all_day
                };
                if (self.model == 'core.calendar.event') {

                    var calendar_list = _.filter(self.subscribed_calendars, function(calendar) {
                        return !!calendar.access.create;
                    });

                    var optionpop = new instance.core_calendar.SelectOptionForm(this);
                    optionpop.select_options(calendar_list,
                        'SelectSubsribedCalendar.render',
                        {title: _.str.sprintf(_t("Select Calendar"))}
                    ).fail(function() {
                        self.$calendar.fullCalendar('unselect');
                    }).done(function(calendar) {
                        var calendar_mode = self.$calendar.fullCalendar('getView');

                        if (calendar_mode === 'month' || (item_data['allDay'] && (self.calendar !== 'month'))) {
                            var event_is_multiday = self.is_range_multiday(item_data.start, item_data.end);
                            item_data['end'].addDays(1);
                            item_data['start'].addHours(8);
                            if (!event_is_multiday) {
                                item_data['end'] = new Date(item_data['start']);
                                item_data['end'].addHours(1);
                            } else {
                                item_data['end'].addHours(-4);
                            }
                        }

                        var data_template = self.get_event_data(item_data, 'create', calendar);
                        self.open_quick_create(data_template, calendar);
                    });
                }
                else {
                    var data_template = self.get_event_data(item_data);
                    self.open_quick_create(data_template);
                }
            }
        });
    },
    init_calendar: function () {
        if (self.recurrent_field) {
            // remove recurrent field from info_fields if present
            self.info_fields = _.filter(self.info_fields, function(f){ return f != self.recurrent_field; });
        }
        return this._super.apply(this, arguments);
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
            if (typeof(parts.id_virtual) === 'string' && parts.id_virtual.match(/^[0-9]+$/)) {
                parts.id_virtual = parseInt(parts.id_virtual);
            }
            if (_virtparts.length >= 3) {
                parts.recurrent_date = _virtparts[2];
            }
        }
        return parts;
    },
    open_quick_create: function(event_obj, calendar) {
        var self = this;
        if (this.model == 'core.calendar.event' && !!calendar) {

            var calendar_form_view_id = (typeof calendar.action_form_view_id == 'object')
                                            ? calendar.action_form_view_id[0]
                                            : calendar.action_form_view_id;

            var defaults = {};
            _.each(event_obj, function(val, field_name) {
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
                    self.$calendar.fullCalendar('unselect');
                    // scheduler.deleteEvent(event_id);
                }
            });
            pop.on('create_completed', self, function(id) {
                // force full-reload to catch new recurrent event
                self.$calendar.fullCalendar('refetchEvents');
            });
        } else {
            this._super.apply(this, arguments);
        }
    },
    open_event: function(event_id, title) {
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
            // var event_obj = _.find(self.events, function(e) { return e.id === event_id;});
            var event_objs = self.$calendar.fullCalendar('clientEvents', event_id);
            if (event_objs.length != 1) {
                return;
            }
            var event_obj = event_objs[0];
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
                    readonly: !event_obj.access.edit
                });
                pop.on('write_completed', self, function(){
                    self.$calendar.fullCalendar('refetchEvents');
                });

            });

        } else {
            return this._super.apply(this, arguments);
        }
    },
    remove_event: function(event_id) {
        var self = this;
        var index = this.dataset.get_id_index(event_id);
        var event_obj = this.$calendar.fullCalendar('clientEvents', event_id)[0];
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
                    // scheduler._events[event_obj.id] = event_obj;
                    // scheduler.event_updated(event_obj);

                }).done(function(choosen_mode) {
                    if (choosen_mode.value == DELETE_ALL) {
                        self.dataset.unlink(id_parts.id_without_recurrent)
                            .done(function(){ self.$calendar.fullCalendar('refetchEvents'); });
                    } else {
                        self.dataset.unlink([self.dataset.ids[index]]).done(function() {
                            self.$calendar.fullCalendar('removeEvents', [event_id]);
                        });
                    }
                });
                return;
            }
        }
        this._super.apply(this, arguments);
    },
    event_data_transform: function(evt) {
        var self = this;
        var converted_event = this._super.apply(this, arguments);

        if (this.model == 'core.calendar.event') {

            if (this.recurrent_field) {
                converted_event['recurrent'] = evt[this.recurrent_field];
            }
            var evi = self.virtual_event_id_to_real(evt.id);
            _.each(self.subscribed_calendars, function(calendar) {
                if (!!evi && calendar.id == evi.calendar_id) {
                    converted_event.access.edit = converted_event.access.edit && !!calendar.access.write;
                    converted_event.access.delete = converted_event.access.delete && !!calendar.access.unlink;
                    if (!converted_event.access.edit) {
                        // force event as readonly
                        converted_event['startEditable'] = false;
                        converted_event['durationEditable'] = false;
                    }
                }
            });
        }
        return converted_event;
    },
    is_action_enabled: function(action) {
        if (this.model == 'core.calendar.event' && _(['edit', 'delete']).contains(action)) {
            // check that at least 1 calendar have the required access
            if (action == 'edit') { cal_action = 'write'; }
            if (action == 'delete') { cal_action = 'unlink'; }
            return _(this.subscribed_calendars)
                    .filter(function (cal){ return cal.access[cal_action]; })
                    .length > 0;
        }
        return this._super.apply(this, arguments);
    },
    get_event_data: function(event_data, mode, calendar_obj) {
        var self = this;
        if (this.model == 'core.calendar.event' && !!calendar_obj) {
            var data = {};
            if (mode === 'create') {
                data[calendar_obj.fields.name] = event_data.title || this.new_event_default_name || null;
            }
            var field_start = calendar_obj.fields.date_start;
            data[field_start] = calendar_obj.fields_type[field_start] == 'date'
                                ? instance.web.date_to_str(event_data.start)
                                : instance.web.datetime_to_str(event_data.start);
            if (calendar_obj.fields.date_end) {
                var field_end = calendar_obj.fields.date_end;
                data[field_end] = calendar_obj.fields_type[field_end] == 'date'
                                  ? instance.web.date_to_str(event_data.end)
                                  : instance.web.datetime_to_str(event_data.end);
            }
            if (calendar_obj.fields.duration) {
                var diff_seconds = Math.round((event_data.end.getTime() - event_data.start.getTime()) / 1000);
                data[calendar_obj.fields.duration] = diff_seconds / 3600;
            }
            return data;
        }
        return this._super.apply(this, arguments);
    },

    // refresh_resource_unavailibility: function() {
    //     // clear all previous marked timespans
    //     console.log('refresh resource unavailibility');
    //     scheduler._marked_timespans = { global: {} };
    //     scheduler._marked_timespans_ids = {};
    //     var range_from = this.range_start;
    //     if (range_from) {
    //         if (!scheduler.config.start_on_monday) {
    //             range_from = range_from.clone().addDays(-1);
    //         }
    //         range_from = instance.web.datetime_to_str(range_from);
    //     }
    //     var range_to = this.range_stop;
    //     if (range_to) {
    //         range_to = instance.web.datetime_to_str(range_to);
    //     }
    //     var self = this;
    //     var resource_model = 'res.users'
    //     var resource_ids = [instance.session.uid];
    //     var getresource_kwargs = {};

    //     if (!this.search_group_by_key) {
    //         // actually only display availiblity infos if the calendar only
    //         // represent a unique resource.
    //         // This is always true in group_by mode, but not in standard filtered
    //         // model. So currently we disable all availibility infos if we're not
    //         // if a group_by mode
    //         // FIXME: detected, based on domain info if filters represent only 1
    //         //        resource
    //         scheduler.updateView();
    //         return;
    //     }

    //     if (this.search_group_by_key) {
    //         resource_model = self.dataset.model;
    //         resource_ids = _.pluck(self.search_groups, 'key');
    //         getresource_kwargs['group_by_field'] = self.search_group_by_key;
    //     }

    //     this.resource_model.call('get_resource_unavailibility', [
    //         resource_model,
    //         resource_ids,
    //         range_from,
    //         range_to,
    //     ],
    //     _.extend(getresource_kwargs, {
    //         context: this.dataset.get_context(),
    //     })).done(function(unavails) {
    //         if (unavails && unavails.length) {
    //             _.each(unavails, function(c) {
    //                 c.start_date = instance.web.str_to_datetime(c.start_date);
    //                 c.end_date = instance.web.str_to_datetime(c.end_date);
    //                 if (!self.search_group_by_key) {
    //                     c.sections = null; // we are is non grouped mode - this must apply globally.
    //                 }
    //                 //console.log(c);
    //                 // console.log('marked_timespan', c);
    //                 scheduler.addMarkedTimespan(c);
    //             })
    //         }
    //         scheduler.updateView();
    //     })
    //     return;
    // },
});

};