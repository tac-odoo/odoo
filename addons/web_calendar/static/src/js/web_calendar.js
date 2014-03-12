/*---------------------------------------------------------
 * OpenERP web_calendar
 *---------------------------------------------------------*/

_.str.toBoolElse = function (str, elseValues, trueValues, falseValues) {
    var ret = _.str.toBool(str, trueValues, falseValues);
    if (_.isUndefined(ret)) {
        return elseValues;
    }
    return ret;
};

openerp.web_calendar = function(instance) {

    var _t = instance.web._t,
        _lt = instance.web._lt,
        QWeb = instance.web.qweb;

    function get_class(name) {
        return new instance.web.Registry({'tmp' : name}).get_object("tmp");
    }

    function get_fc_defaultOptions() {
        return {
            weekNumberTitle: _t("W"),
            allDayText: _t("all-day"),
            monthNames: Date.CultureInfo.monthNames,
            monthNamesShort: Date.CultureInfo.abbreviatedMonthNames,
            dayNames: Date.CultureInfo.dayNames,
            dayNamesShort: Date.CultureInfo.abbreviatedDayNames,
            firstDay: Date.CultureInfo.firstDayOfWeek,
            weekNumbers: true
        };
    }

    function is_virtual_id(id) {
        return typeof id === "string" && id.indexOf('-') >= 0;
    }

    function isNullOrUndef(value) {
        return _.isUndefined(value) || _.isNull(value);
    }

    instance.web.views.add('calendar', 'instance.web_calendar.CalendarView');

    instance.web_calendar.CalendarView = instance.web.View.extend({
        template: "CalendarView",
        display_name: _lt('Calendar'),
        quick_create_instance: 'instance.web_calendar.QuickCreate',

        init: function (parent, dataset, view_id, options) {
            this._super(parent);
            this.ready = $.Deferred();
            this.set_default_options(options);
            this.dataset = dataset;
            this.model = dataset.model;
            this.fields_view = {};
            this.view_id = view_id;
            this.view_type = 'calendar';
            this.color_map = {};
            this.range_start = null;
            this.range_stop = null;
            this.selected_filters = [];
            this.many2manys = [];

            // QWeb initalization
            this.qweb = new QWeb2.Engine();
            this.qweb.debug = instance.session.debug;
            this.qweb.default_dict = _.clone(QWeb.default_dict);
            this.qweb_context = {};
        },

        set_default_options: function(options) {
            this._super(options);
            _.defaults(this.options, {
                confirm_on_delete: true
            });
        },

        destroy: function() {
            this.$calendar.fullCalendar('destroy');
            if (this.$small_calendar) {
                this.$small_calendar.datepicker('destroy');
            }
            this._super.apply(this, arguments);
        },

        view_loading: function (fv) {
            /* xml view calendar options */
            var attrs = fv.arch.attrs,
                self = this;
            this.fields_view = fv;
            this.$calendar = this.$el.find(".oe_calendar_widget");

            this.info_fields = [];

            /* buttons */
            this.$buttons = $(QWeb.render("CalendarView.buttons", {'widget': this}));
            if (this.options.$buttons) {
                this.$buttons.appendTo(this.options.$buttons);
            } else {
                this.$el.find('.oe_calendar_buttons').replaceWith(this.$buttons);
            }

            this.$buttons.on('click', 'button.oe_calendar_button_new', function () {
                self.dataset.index = null;
                self.do_switch_view('form');
            });

            /* custom calendar item template */
            this.add_qweb_template();
            this.qweb.templates['CalendarView.popover.layout'] = QWeb.templates['CalendarView.popover.layout'].cloneNode(true);
            this.qweb.templates['CalendarView.popover.buttons'] = QWeb.templates['CalendarView.popover.buttons'].cloneNode(true);

            this.qweb_context = {
                instance: instance,
                widget: this,
                read_only_mode: this.options.read_only_mode
            };
            for (var p in this) {
                if (_.str.startsWith(p, 'calendar_') && _.isFunction(this[p])) {
                    this.qweb_context[p] = _.bind(this[p], this);
                }
            }

            if (!attrs.date_start) {
                throw new Error(_t("Calendar view has not defined 'date_start' attribute."));
            }

            this.$el.addClass(attrs['class']);

            this.name = fv.name || attrs.string;
            this.view_id = fv.view_id;

            this.mode = attrs.mode;                 // one of month, week or day
            this.date_start = attrs.date_start;     // Field name of starting date field
            this.date_delay = attrs.date_delay;     // duration
            this.date_stop = attrs.date_stop;
            this.all_day = attrs.all_day;
            this.how_display_event = '';
            this.use_intermediate_popover = false;

            if (!isNullOrUndef(attrs.use_intermediate_popover)) {
                self.use_intermediate_popover = true;
            }

            this.attendee_people = attrs.attendee;

            if (!isNullOrUndef(attrs.quick_create_instance)) {
                self.quick_create_instance = 'instance.' + attrs.quick_create_instance;
            }

            //if quick_add = False, we don't allow quick_add
            //if quick_add = not specified in view, we use the default quick_create_instance
            //if quick_add = is NOT False and IS specified in view, we this one for quick_create_instance'   

            this.quick_add_pop = (isNullOrUndef(attrs.quick_add) || _.str.toBoolElse(attrs.quick_add,true) );
            if (this.quick_add_pop && !isNullOrUndef(attrs.quick_add)) {
                self.quick_create_instance = 'instance.' + attrs.quick_add;
            }
            // The display format which will be used to display the event where fields are between "[" and "]"
            if (!isNullOrUndef(attrs.display)) {
                this.how_display_event = attrs.display; // String with [FIELD]
            }

            // If this field is set ot true, we don't open the event in form view, but in a popup with the view_id passed by this parameter
            if (isNullOrUndef(attrs.event_open_popup) || !_.str.toBoolElse(attrs.event_open_popup,true)) {
                this.open_popup_action = false;
            }
            else {
                this.open_popup_action = attrs.event_open_popup;
            }
            // If this field is set to true, we will use de calendar_friends model as filter and not the color field.
            this.useContacts = (!isNullOrUndef(attrs.use_contacts) && _.str.toBool(attrs.use_contacts)) && (!isNullOrUndef(self.options.$sidebar));

            // If this field is set ot true, we don't add itself as an attendee when we use attendee_people to add each attendee icon on an event
            // The color is the color of the attendee, so don't need to show again that it will be present
            this.colorIsAttendee = (!(isNullOrUndef(attrs.color_is_attendee) || !_.str.toBoolElse(attrs.color_is_attendee, true))) && (!isNullOrUndef(self.options.$sidebar));

            // if we have not sidebar, (eg: Dashboard), we don't use the filter "coworkers"
            if (isNullOrUndef(self.options.$sidebar)) {
                this.useContacts = false;
                this.colorIsAttendee = false;
                this.attendee_people = undefined;
            }

/*
            Will be more logic to do it in futur, but see below to stay Retro-compatible
            
            if (isNull(attrs.avatar_model)) {
                this.avatar_model = 'res.partner'; 
            }
            else {
                if (attrs.avatar_model == 'False') {
                    this.avatar_model = null;
                }
                else {  
                    this.avatar_model = attrs.avatar_model;
                }
            }            
*/
            if (isNullOrUndef(attrs.avatar_model)) {
                this.avatar_model = null;
            }
            else {
                this.avatar_model = attrs.avatar_model;
            }

            if (isNullOrUndef(attrs.avatar_title)) {
                this.avatar_title = this.avatar_model;
            }
            else {
                this.avatar_title = attrs.avatar_title;
            }
            this.color_field = attrs.color;

            if (this.color_field && this.selected_filters.length === 0) {
                var default_filter;
                if ((default_filter = this.dataset.context['calendar_default_' + this.color_field])) {
                    this.selected_filters.push(default_filter + '');
                }
            }

            this.fields = fv.fields;

            for (var fld = 0; fld < fv.arch.children.length; fld++) {
                if (fv.arch.children[fld].tag == 'field') {
                    var field_attrs = fv.arch.children[fld].attrs;
                    var field_name = field_attrs.name;
                    var field_modifiers = JSON.parse(field_attrs.modifiers || '{}');

                    this.info_fields.push(field_name);

                    if (!!field_modifiers.readonly) {
                        if (field_name === this.date_start) {
                            this.date_start_readonly = field_modifiers.readonly;
                        } else if (field_name === this.date_duration) {
                            this.date_duration_readonly = field_modifiers.readonly;
                        } else if (field_name === this.date_stop) {
                            this.date_stop_readonly = field_modifiers.readonly;
                        }
                    }
                }
            }

            return (new instance.web.Model(this.dataset.model))
                .call("check_access_rights", ["create", false])
                .then(function (create_right) {
                    self.create_right = create_right;
                    self.init_calendar().then(function() {
                        self.trigger('calendar_view_loaded', fv);
                        self.ready.resolve();
                    });
                });
        },
        get_fc_init_options_i18n: function() {
            var i18n_options = {
                buttonText: {
                    today: _t("Today"),
                    day: _t("Day"),
                    week: _t("Week"),
                    month: _t("Month")
                }
            };
            if (Date.CultureInfo.dateElementOrder == 'ymd' || Date.CultureInfo.dateElementOrder == 'mdy') {
                i18n_options = $.extend(i18n_options, {
                    columnFormat: {
                        month: 'ddd',
                        week: 'ddd M/d',
                        day: 'dddd M/d'
                    },
                    titleFormat: {
                        month: 'MMMM yyyy',
                        week: "MMM d[ yyyy]{ '&#8212;'[ MMM] d yyyy}",
                        day: 'dddd, MMM d, yyyy'
                    }
                });
            }
            else {
                i18n_options = $.extend(i18n_options, {
                    columnFormat: {
                        month: 'ddd',
                        week: 'ddd d/M',
                        day: 'dddd d/M'
                    },
                    titleFormat: {
                        month: 'MMMM yyyy',
                        week: "d[ MMM][ yyyy]{ '&#8212;' d MMM yyyy}",
                        day: 'dddd, d MMM, yyyy'
                    }
                });
            }
            return i18n_options;
        },
        get_fc_init_options: function () {
            //Documentation here : http://arshaw.com/fullcalendar/docs/
            var self = this;
            return $.extend({}, get_fc_defaultOptions(), self.get_fc_init_options_i18n(), {
                
                defaultView: (this.mode == "month")?"month":
                    (this.mode == "week"?"agendaWeek":
                     (this.mode == "day"?"agendaDay":"month")),
                header: {
                    left: 'prev,next today',
                    center: 'title',
                    right: 'month,agendaWeek,agendaDay'
                },
                selectable: !this.options.read_only_mode && this.create_right,
                selectHelper: true,
                editable: !this.options.read_only_mode,
                droppable: true,

                // callbacks

                eventDrop: function (event, _day_delta, _minute_delta, _all_day, _revertFunc) {
                    var data = self.get_event_data(event);
                    self.proxy('update_record')(event._id, data); // we don't revert the event, but update it.
                },
                eventResize: function (event, _day_delta, _minute_delta, _revertFunc) {
                    var data = self.get_event_data(event);
                    self.proxy('update_record')(event._id, data);
                },
                eventRender: function (event, element, view) {
                    self.render_event(event, element, view);
                },
                eventAfterRender: function (event, element, view) {
                    if ((view.name !== 'month') && (((event.end-event.start)/60000)<=30)) {
                        //if duration is too small, we see the html code of img
                        var current_title = $(element.find('.fc-event-time')).text();
                        var new_title = current_title.substr(0,current_title.indexOf("<img")>0?current_title.indexOf("<img"):current_title.length);
                        element.find('.fc-event-time').html(new_title);
                    }
                },
                eventDestroy: function (event, element, view) {
                    self.destroy_event(event, element, view);
                },
                eventClick: function (event, jsEvent, view) {
                    if (self.popover) {
                        self.popover.event_clicked(event, jsEvent, view);
                    } else {
                        self.open_event(event._id,event.title);
                    }
                },
                select: function (start_date, end_date, all_day, _js_event, _view) {
                    var data_template = self.get_event_data({
                        start: start_date,
                        end: end_date,
                        allDay: all_day,
                    });
                    self.open_quick_create(data_template);

                },

                unselectAuto: false,

                // Options
                timeFormat : {
                   // for agendaWeek and agendaDay
                    agenda: 'h:mm{ - h:mm}', // 5:00 - 6:30

                    // for all other views
                    '': 'h(:mm)tt'  // 7pm
                },
                weekMode : 'liquid',
                aspectRatio: 1.8,
                snapMinutes: 15,
            });
        },

        calendarMiniChanged: function (context) {
            return function(datum,obj) {
                var curView = context.$calendar.fullCalendar( 'getView');
                var curDate = new Date(obj.currentYear , obj.currentMonth, obj.currentDay);

                if (curView.name == "agendaWeek") {
                    if (curDate <= curView.end && curDate >= curView.start) {
                        context.$calendar.fullCalendar('changeView','agendaDay');
                    }
                }
                else if (curView.name != "agendaDay" || (curView.name == "agendaDay" && curDate.compareTo(curView.start)===0)) {
                        context.$calendar.fullCalendar('changeView','agendaWeek');
                }
                context.$calendar.fullCalendar('gotoDate', obj.currentYear , obj.currentMonth, obj.currentDay);
            };
        },

        init_calendar: function() {
            var self = this;
             
            if (!this.popover && self.use_intermediate_popover) {
                this.popover = new instance.web_calendar.EventPopover(this);
                this.popover.appendTo(this.$el.find('.oe_calendar_popover_container'));
            }

            if (!this.sidebar && this.options.$sidebar) {
                this.sidebar = new instance.web_calendar.Sidebar(this);
                this.sidebar.appendTo(this.$el.find('.oe_calendar_sidebar_container'));

                this.$small_calendar = self.$el.find(".oe_calendar_mini");
                $.datepicker.setDefaults({
                    clearText: _t('Clear'),
                    clearStatus: _t('Erase the current date'),
                    closeText: _t('Done'),
                    closeStatus: _t('Close without change'),
                    prevText: _t('<Prev'),
                    prevStatus: _t('Show the previous month'),
                    nextText: _t('Next>'),
                    nextStatus: _t('Show the next month'),
                    currentText: _t('Today'),
                    currentStatus: _t('Show the current month'),
                    monthNames: Date.CultureInfo.monthNames,
                    monthNamesShort: Date.CultureInfo.abbreviatedMonthNames,
                    monthStatus: _t('Show a different month'),
                    yearStatus: _t('Show a different year'),
                    weekHeader: _t('Wk'),
                    weekStatus: _t('Week of the year'),
                    dayNames: Date.CultureInfo.dayNames,
                    dayNamesShort: Date.CultureInfo.abbreviatedDayNames,
                    dayNamesMin: Date.CultureInfo.shortestDayNames,
                    dayStatus: _t('Set DD as first week day'),
                    dateStatus: _t('Select D, M d'),
                    firstDay: Date.CultureInfo.firstDayOfWeek,
                    initStatus: _t('Select a date'),
                    isRTL: false
                });
                this.$small_calendar.datepicker({
                    onSelect: self.calendarMiniChanged(self),
                    showWeek: true,
                    firstDay: Date.CultureInfo.firstDayOfWeek
                });

                if (this.useContacts) {
                    //Get my Partner ID
                    
                    new instance.web.Model("res.users").query(["partner_id"]).filter([["id", "=",this.dataset.context.uid]]).first()
                        .done(
                            function(result) {
                                var sidebar_items = {};
                                var filter_value = result.partner_id[0];
                                var filter_item = {
                                    value: filter_value,
                                    label: result.partner_id[1] + _lt(" [Me]"),
                                    color: self.get_color(filter_value),
                                    avatar_model: self.avatar_model,
                                    is_checked: true
                                };

                                sidebar_items[filter_value] = filter_item ;
                                filter_item = {
                                        value: -1,
                                        label: _lt("Everybody's calendars"),
                                        color: self.get_color(-1),
                                        avatar_model: self.avatar_model,
                                        is_checked: false
                                    };
                                sidebar_items[-1] = filter_item ;
                                //Get my coworkers/contacts
                                new instance.web.Model("calendar.contacts").query(["partner_id"]).filter([["user_id", "=",self.dataset.context.uid]]).all().then(function(result) {
                                    _.each(result, function(item) {
                                        filter_value = item.partner_id[0];
                                        filter_item = {
                                            value: filter_value,
                                            label: item.partner_id[1],
                                            color: self.get_color(filter_value),
                                            avatar_model: self.avatar_model,
                                            is_checked: true
                                        };
                                        sidebar_items[filter_value] = filter_item ;
                                    });

                                    self.all_filters = sidebar_items;
                                    self.now_filter_ids = $.map(self.all_filters, function(o) { return o.value; });
                                    
                                    self.sidebar.filter.events_loaded(self.all_filters);
                                    self.sidebar.filter.set_filters();
                                                                        
                                    self.sidebar.filter.addUpdateButton();
                                }).done(function () {
                                    self.$calendar.fullCalendar('refetchEvents');
                                });
                            }
                         );
                }
                this.extraSideBar();                
            }
            self.$calendar.fullCalendar(self.get_fc_init_options());
            
            return $.when();
        },
        extraSideBar: function() {
        },

        open_quick_create: function(data_template) {
            if (!isNullOrUndef(this.quick)) {
                return this.quick.trigger('close');
            }
            var QuickCreate = get_class(this.quick_create_instance);
            
            this.options.disable_quick_create =  this.options.disable_quick_create || !this.quick_add_pop;
            
            this.quick = new QuickCreate(this, this.dataset, true, this.options, data_template);
            this.quick.on('added', this, this.quick_created)
                    .on('slowadded', this, this.slow_created)
                    .on('close', this, function() {
                        this.quick.destroy();
                        delete this.quick;
                        this.$calendar.fullCalendar('unselect');
                    });
            this.quick.replace(this.$el.find('.oe_calendar_qc_placeholder'));
            this.quick.focus();
            
        },

        /**
         * Refresh one fullcalendar event identified by it's 'id' by reading OpenERP record state.
         * If event was not existent in fullcalendar, it'll be created.
         */
        refresh_event: function(id) {
            var self = this;
            if (is_virtual_id(id)) {
                // Should avoid "refreshing" a virtual ID because it can't
                // really be modified so it should never be refreshed. As upon
                // edition, a NEW event with a non-virtual id will be created.
                console.warn("Unwise use of refresh_event on a virtual ID.");
            }
            this.dataset.read_ids([id], _.keys(this.fields)).done(function (incomplete_records) {
                self.perform_necessary_name_gets(incomplete_records).then(function(records) {
                    // Event boundaries were already changed by fullcalendar, but we need to reload them:
                    var new_event = self.event_data_transform(records[0]);
                    // fetch event_obj
                    var event_objs = self.$calendar.fullCalendar('clientEvents', id);
                    if (event_objs.length == 1) { // Already existing obj to update
                        var event_obj = event_objs[0];
                        // update event_obj
                        _(new_event).each(function (value, key) {
                            event_obj[key] = value;
                        });
                        self.$calendar.fullCalendar('updateEvent', event_obj);
                    } else { // New event object to create
                        self.$calendar.fullCalendar('renderEvent', new_event);
                        // By forcing attribution of this event to this source, we
                        // make sure that the event will be removed when the source
                        // will be removed (which occurs at each do_search)
                        self.$calendar.fullCalendar('clientEvents', id)[0].source = self.event_source;
                    }
                });
            });
        },

        get_color: function(key) {
            if (this.color_map[key]) {
                return this.color_map[key];
            }
            var index = (((_.keys(this.color_map).length + 1) * 5) % 24) + 1;
            this.color_map[key] = index;
            return index;
        },
        /**
          * Event Rendering
          * ===============
          */
        transform_record: function(record) {
            var self = this,
                new_record = {},
                calendar_field_names = _(this.calendar_fields).chain()
                                            .values().pluck('name').value(),
                fields = _.uniq(_.keys(self.fields_view.fields)
                                .concat(calendar_field_names));
            _.each(record, function(value, name) {
                if (_.indexOf(fields, name) === -1) {
                    return;
                }
                var r = _.clone(self.fields_view.fields[name] || {});
                if ((r.type === 'date' || r.type === 'datetime') && value) {
                    r.raw_value = instance.web.auto_str_to_date(value);
                } else {
                    r.raw_value = value;
                }
                if (self.fields[name].type == 'many2many' && record['__display_name_'+name] !== undefined) {
                    r.value = record['__display_name_'+name];
                } else {
                    r.value = instance.web.format_value(value, r);
                }
                new_record[name] = r;
            });
            return new_record;
        },
        /*  add_qweb_template
         *   select the nodes into the xml and send to extract_aggregates the nodes with TagName="field"
         */
        add_qweb_template: function() {
            for (var i=0, ii=this.fields_view.arch.children.length; i < ii; i++) {
                var child = this.fields_view.arch.children[i];
                if (child.tag === "templates") {
                    this.transform_qweb_template(child);
                    this.qweb.add_template(instance.web.json_node_to_xml(child));
                    break;
                }
            }
        },
        transform_qweb_template: function(node) {
            var qweb_add_if = function(node, condition) {
                if (node.attrs[QWeb.prefix + '-if']) {
                    condition = _.str.sprintf("(%s) and (%s)", node.attrs[QWeb.prefix + '-if'], condition);
                }
                node.attrs[QWeb.prefix + '-if'] = condition;
            };
            // Process modifiers
            if (node.tag && node.attrs.modifiers) {
                var modifiers = JSON.parse(node.attrs.modifiers || '{}');
                if (modifiers.invisible) {
                    qweb_add_if(node, _.str.sprintf("!calendar_compute_domain(%s)", JSON.stringify(modifiers.invisible)));
                }
            }
            switch (node.tag) {
                case 'field':
                    if (this.fields_view.fields[node.attrs.name].type === 'many2many') {
                        if (_.indexOf(this.many2manys, node.attrs.name) < 0) {
                            this.many2manys.push(node.attrs.name);
                        }
                    }
                    node.tag = QWeb.prefix;
                    node.attrs[QWeb.prefix + '-esc'] = 'record.' + node.attrs['name'] + '.value';
                    break;
            }
            if (node.children) {
                for (var i = 0, ii = node.children.length; i < ii; i++) {
                    this.transform_qweb_template(node.children[i]);
                }
            }
        },
        destroy_event: function(event, element, view) {
            // Called when destroying item on the calendar view (inverse of 'render')
            // This doesn't mean we 'delete/unlink' the event!
        },
        render_event: function(event, element, view) {
            var self = this;

            var result = event.title;  // default value
            if (!!self.qweb.templates['calendar-event-title'] && !!event.record) {
                var qweb_context = _.extend({}, this.qweb_context || {}, {
                    display_short: false,
                    record: event.record,
                    event_title: event.title,
                    event_start: event.start,
                    event_end: event.end,
                    event_is_allday: event.allDay
                });
                result = this.qweb.render('calendar-event-title', qweb_context);
            }
            element.find('.fc-event-title').html(result);
            return false; // always use our custom rendering only
        },
        render_has_template: function(template_name) {
            return !!this.qweb.templates[template_name];
        },
        calendar_compute_domain: function(domain) {
            return instance.web.form.compute_domain(domain, this.values);
        },
        calendar_dates_range: function(start_date, end_date, allDay) {
            end_date = end_date || start_date;
            var range = '';
            var format_value = instance.web.format_value;
            var formats = {
                'datetime': {type: 'datetime'},
                'date': {type: 'date'},
                'time': {type: 'time'}
            };
            var is_same_day = start_date.isSameDay(end_date);
            if (allDay) {
                if (is_same_day) {
                    range = _.str.sprintf('%s', format_value(start_date, formats.date));
                } else {
                    range = _.str.sprintf('%s - %s', format_value(start_date, formats.date),
                                                     format_value(end_date, formats.date));
                }
            } else {
                range = _.str.sprintf('%s - %s',
                            format_value(start_date, formats.datetime),
                            format_value(end_date, is_same_day ? formats.time : formats.datetime));
            }
            return range;
        },
        /**
         * In o2m case, records from dataset won't have names attached to their *2o values.
         * We should make sure this is the case.
         */
        perform_necessary_name_gets: function(evts) {
            var def = $.Deferred();
            var self = this;
            var to_get = {};
            _(this.info_fields).each(function (fieldname) {
                if (!_(["many2one", "one2one", "many2many"]).contains(
                    self.fields[fieldname].type))
                    return;
                to_get[fieldname] = [];
                _(evts).each(function (evt) {
                    var value = evt[fieldname];
                    if (self.fields[fieldname].type === "many2many") {
                        _(evt[fieldname]).each(function (id) {
                            to_get[fieldname].push(id);
                        });
                    }
                    if (value === false || (value instanceof Array)) {
                        return;
                    }
                    to_get[fieldname].push(value);
                });
                if (to_get[fieldname].length === 0) {
                    delete to_get[fieldname];
                }
            });
            var defs = _(to_get).map(function (ids, fieldname) {
                return (new instance.web.Model(self.fields[fieldname].relation))
                    .call('name_get', [ids]).then(function (vals) {
                        return [fieldname, vals];
                    });
            });

            $.when.apply(this, defs).then(function() {
                var values = arguments;
                _(values).each(function(value) {
                    var fieldname = value[0];
                    var name_gets = value[1];
                    // for many2many fields
                    if (self.fields[fieldname].type == 'many2many') {
                        var name_gets_dict = {};
                        _(name_gets).each(function (v) {
                            name_gets_dict[v[0]] = v[1];
                        });
                        _(evts).each(function(evt) {
                            evt['__display_name_'+fieldname] =
                                _(evt[fieldname])
                                    .map(function (id){return name_gets_dict[id];})
                                    .join(', ');
                        });
                        return;
                    }
                    // for many2one, one2one fields
                    _(name_gets).each(function(name_get) {
                        _(evts).chain()
                            .filter(function (e) {return e[fieldname] == name_get[0];})
                            .each(function(evt) {
                                evt[fieldname] = name_get;
                            });
                    });
                });
                def.resolve(evts);
            });
            return def;
        },
        is_range_multiday: function(start, stop) {
            if (start === undefined || stop === undefined) {
                return false;
            }
            if (stop.isAfter(start) && !stop.isSameDay(start)) {
                return true;
            }
            return false;
        },
        /**
         * Transform OpenERP event object to fullcalendar event object
         */
        event_data_transform: function(evt) {
            var self = this;

            var date_delay = evt[this.date_delay] || 1.0,
                all_day = this.all_day ? evt[this.all_day] : false,
                res_computed_text = '',
                the_title = '',
                attendees = [];

            if (!all_day) {
                date_start = instance.web.auto_str_to_date(evt[this.date_start]);
                date_stop = this.date_stop ? instance.web.auto_str_to_date(evt[this.date_stop]) : null;
            }
            else {
                date_start = instance.web.auto_str_to_date(evt[this.date_start].split(' ')[0],'date');
                date_stop = this.date_stop ? instance.web.auto_str_to_date(evt[this.date_stop].split(' ')[0],'date').addMinutes(-1) : null;
            }

            if (this.info_fields) {
                var temp_ret = {};
                res_computed_text = this.how_display_event;
                
                _.each(this.info_fields, function (fieldname) {
                    var value = evt[fieldname];
                    if (_.contains(["many2one", "one2one"], self.fields[fieldname].type)) {
                        if (value === false) {
                            temp_ret[fieldname] = null;
                        }
                        else if (value instanceof Array) {
                            temp_ret[fieldname] = value[1]; // no name_get to make
                        }
                        else {
                            throw new Error("Incomplete data received from dataset for record " + evt.id);
                        }
                    }
                    else if (_.contains(["one2many","many2many"], self.fields[fieldname].type)) {
                        if (value === false) {
                            temp_ret[fieldname] = null;
                        }
                        else if (value instanceof Array)  {
                            temp_ret[fieldname] = value; // if x2many, keep all id !
                        }
                        else {
                            throw new Error("Incomplete data received from dataset for record " + evt.id);
                        }
                    }
                    else {
                        temp_ret[fieldname] = value;
                    }
                    res_computed_text = res_computed_text.replace("["+fieldname+"]",temp_ret[fieldname]);
                });

                
                if (res_computed_text.length) {
                    the_title = res_computed_text;
                }
                else {
                    var res_text= [];
                    _.each(temp_ret, function(val,key) { res_text.push(val); });
                    the_title = res_text.join(', ');
                }
                the_title = _.escape(the_title);
                
                
                the_title_avatar = '';
                
                if (! _.isUndefined(this.attendee_people)) {
                    var MAX_ATTENDEES = 3;
                    var attendee_showed = 0;
                    var attendee_other = '';

                    _.each(temp_ret[this.attendee_people],
                        function (the_attendee_people) {
                            attendees.push(the_attendee_people);
                            attendee_showed += 1;
                            if (attendee_showed<= MAX_ATTENDEES) {
                                if (self.avatar_model !== null) {
                                       the_title_avatar += '<img title="' + self.all_attendees[the_attendee_people] + '" class="attendee_head"  \
                                                            src="/web/binary/image?model=' + self.avatar_model + '&field=image_small&id=' + the_attendee_people + '&session_id=' + instance.session.session_id + '"></img>';
                                }
                                else {
                                    if (!self.colorIsAttendee || the_attendee_people != temp_ret[self.color_field]) {
                                            tempColor = (self.all_filters[the_attendee_people] !== undefined) 
                                                        ? self.all_filters[the_attendee_people].color
                                                        : self.all_filters[-1].color;
                                        the_title_avatar += '<i class="fa fa-user attendee_head color_'+tempColor+'" title="' + self.all_attendees[the_attendee_people] + '" ></i>';
                                    }//else don't add myself
                                }
                            }
                            else {
                                attendee_other += self.all_attendees[the_attendee_people] +", ";
                            }
                        }
                    );
                    if (attendee_other.length>2) {
                        the_title_avatar += '<span class="attendee_head" title="' + attendee_other.slice(0, -2) + '">+</span>';
                    }
                    the_title = the_title_avatar + the_title;
                }
            }
            
            if (!date_stop && date_delay) {
                date_stop = date_start.clone().addHours(date_delay);
            }
            var r = {
                'record': this.transform_record(evt),
                'start': date_start.toString('yyyy-MM-dd HH:mm:ss'),
                'end': date_stop.toString('yyyy-MM-dd HH:mm:ss'),
                'title': the_title,
                'allDay': (this.fields[this.date_start].type == 'date' || (this.all_day && evt[this.all_day]) || this.is_range_multiday(date_start, date_stop)),
                'id': evt.id,
                'attendees':attendees
            };

            // Setup event access
            r['access'] = {
                'edit': this.is_action_enabled('edit') && !this.options.read_only_mode,
                'delete': this.is_action_enabled('delete') && !this.options.read_only_mode,
            }
            var values = {};
            _.each(evt, function(v, k) {
                values[k] = { value: v }
            });
            var calendar_fields_readonly = {};
            _.each(['date_start', 'date_stop', 'duration'], function(field) {
                var field_ro_domain = self[field + '_readonly'];
                calendar_fields_readonly[field] = field_ro_domain
                    ? instance.web.form.compute_domain(field_ro_domain || [], values)
                    : false;
            });
            r['startEditable'] = r.access.edit && !calendar_fields_readonly['date_start'];
            r['durationEditable'] = r.access.edit && !calendar_fields_readonly['date_stop'] && !calendar_fields_readonly['duration'];

            var color_key = evt[this.color_field];
            var color_field = this.fields[this.color_field];
            if (typeof color_key === "object") {
                color_key = color_key[0];
            }
            if (color_field.type === 'selection') {
                color_key = _.pluck(color_field.selection, 0).indexOf(color_key);
            }

            if (!self.useContacts || self.all_filters[color_key] !== undefined) {
                if (this.color_field && evt[this.color_field]) {
                    r.className = 'cal_opacity calendar_color_'+ this.get_color(color_key);
                }
            }
            else  { // if form all, get color -1
                  r.className = 'cal_opacity calendar_color_'+ self.all_filters[-1].color;
            }
            return r;
        },
        
        /**
         * Transform fullcalendar event object to OpenERP Data object
         */
        get_event_data: function(event) {

            // Normalize event_end without changing fullcalendars event.
            var data = {
                name: event.title
            };            
            
            var event_end = event.end;
            //Bug when we move an all_day event from week or day view, we don't have a dateend or duration...            
            if (event_end == null) {
                event_end = new Date(event.start).addHours(2);
            }

            if (event.allDay) {
                // Sometimes fullcalendar doesn't give any event.end.
                if (event_end == null || _.isUndefined(event_end)) {
                    event_end = new Date(event.start);
                }
                if (this.all_day) {
                    event_end = (new Date(event_end.getTime())).addDays(1);
                    date_start_day = new Date(event.start.getFullYear(),event.start.getMonth(),event.start.getDate(),12);
                    date_stop_day = new Date(event_end.getFullYear(),event_end.getMonth(),event_end.getDate(),12);
                }
                else {
                    date_start_day = new Date(event.start.getFullYear(),event.start.getMonth(),event.start.getDate(),7);
                    date_stop_day = new Date(event_end.getFullYear(),event_end.getMonth(),event_end.getDate(),19);
                }
                data[this.date_start] = instance.web.parse_value(date_start_day, this.fields[this.date_start]);
                if (this.date_stop) {
                    data[this.date_stop] = instance.web.parse_value(date_stop_day, this.fields[this.date_stop]);
                }
                diff_seconds = Math.round((date_stop_day.getTime() - date_start_day.getTime()) / 1000);
                                
            }
            else {
                data[this.date_start] = instance.web.parse_value(event.start, this.fields[this.date_start]);
                if (this.date_stop) {
                    data[this.date_stop] = instance.web.parse_value(event_end, this.fields[this.date_stop]);
                }
                diff_seconds = Math.round((event_end.getTime() - event.start.getTime()) / 1000);
            }

            if (this.all_day) {
                data[this.all_day] = event.allDay;
            }

            if (this.date_delay) {
                
                data[this.date_delay] = diff_seconds / 3600;
            }
            return data;
        },

        do_search: function(domain, context, _group_by) {
            var self = this;
           if (! self.all_filters) {            
                self.all_filters = {}                
           }

            if (! _.isUndefined(this.event_source)) {
                this.$calendar.fullCalendar('removeEventSource', this.event_source);
            }
            this.event_source = {
                events: function(start, end, callback) {
                    var current_event_source = self.event_source;
                    self.dataset.read_slice(_.keys(self.fields), {
                        offset: 0,
                        domain: self.get_range_domain(domain, start, end),
                        context: context,
                    }).done(function(events) {

                        if (self.event_source !== current_event_source) {
                            console.log("Consecutive ``do_search`` called. Cancelling.");
                            return;
                        }
                        
                        if (!self.useContacts) {  // If we use all peoples displayed in the current month as filter in sidebars
                                                        
                            var filter_field = self.fields[self.color_field];
                            var filter_label;
                            var filter_value;
                            var filter_item;
                            
                            self.now_filter_ids = [];

                            if (filter_field.type === 'selection') {
                                // preload filter for field.selection
                                // we want to see all possible value
                                _.each(filter_field.selection, function(v, i) {
                                    if (!self.all_filters[i]) {
                                        filter_item = {
                                            value: i,
                                            label: v[1],
                                            color: self.get_color(i),
                                            avatar_model: self.avatar_model,
                                            is_checked: true
                                        };
                                        self.all_filters[i] = filter_item;
                                    }
                                });
                            }

                            _.each(events, function (e) {
                                filter_value = e[self.color_field];
                                filter_label = filter_value;
                                if (filter_field.type === 'many2one') {
                                    if (filter_value) {
                                        filter_label = filter_value[1];
                                        filter_value = filter_value[0];
                                    } else {
                                        filter_value = -1;
                                        filter_label = _('No value');
                                    }
                                }
                                if (filter_field.type === 'selection') {
                                    // replace value by index in selection values list
                                    filter_value = _.pluck(filter_field.selection, 0).indexOf(filter_value);
                                    filter_label = filter_field.selection[filter_value][1];
                                }
                                if (!self.all_filters[filter_value]) {
                                    filter_item = {
                                        value: filter_value,
                                        label: filter_label,
                                        color: self.get_color(filter_value),
                                        avatar_model: self.avatar_model,
                                        is_checked: true
                                    };
                                    self.all_filters[filter_value] = filter_item;
                                }
                                if (! _.contains(self.now_filter_ids, filter_value)) {
                                    self.now_filter_ids.push(filter_value);
                                }
                            });

                            if (self.sidebar) {
                                self.sidebar.filter.events_loaded();
                                self.sidebar.filter.set_filters();
                                
                                events = $.map(events, function (e) {
                                    filter_value = e[self.color_field];
                                    if (filter_field.type === 'many2one') {
                                        if (filter_value) {
                                            filter_value = filter_value[0];
                                        } else {
                                            filter_value = -1;
                                        }
                                    }
                                    if (filter_field.type === 'selection') {
                                        filter_value = _.pluck(filter_field.selection, 0).indexOf(filter_value);
                                    }
                                    if (_.contains(self.now_filter_ids, filter_value) &&  self.all_filters[filter_value].is_checked) {
                                        return e;
                                    }
                                    return null;
                                });
                            }
                            return self.perform_necessary_name_gets(events).then(callback);
                        }
                        else { //WE USE CONTACT
                            if (self.attendee_people !== undefined) {
                                //if we don't filter on 'Everybody's Calendar
                                if (!self.all_filters[-1] || !self.all_filters[-1].is_checked) {
                                    var checked_filter = $.map(self.all_filters, function(o) { if (o.is_checked) { return o.value; }});
                                    // If we filter on contacts... we keep only events from coworkers
                                    events = $.map(events, function (e) {
                                        if (_.intersection(checked_filter,e[self.attendee_people]).length) {
                                            return e;
                                        }
                                        return null;
                                    });
                                }
                            }

                            var all_attendees = $.map(events, function (e) { return e[self.attendee_people]; });
                            all_attendees = _.chain(all_attendees).flatten().uniq().value();

                            self.all_attendees = {};
                            if (self.avatar_title !== null) {
                                new instance.web.Model(self.avatar_title).query(["name"]).filter([["id", "in", all_attendees]]).all().then(function(result) {
                                    _.each(result, function(item) {
                                        self.all_attendees[item.id] = item.name;
                                    });
                                }).done(function() {
                                    return self.perform_necessary_name_gets(events).then(callback);
                                });
                            }
                            else {
                                _.each(all_attendees,function(item){
                                        self.all_attendees[item] = '';
                                });
                                return self.perform_necessary_name_gets(events).then(callback);
                            }
                        }
                    });
                },
                eventDataTransform: function (event) {
                    return self.event_data_transform(event);
                },
            };
            this.$calendar.fullCalendar('addEventSource', this.event_source);
        },
        /**
         * Build OpenERP Domain to filter object by this.date_start field
         * between given start, end dates.
         */
        get_range_domain: function(domain, start, end) {
            var format = instance.web.date_to_str;
            
            extend_domain = [[this.date_start, '>=', format(start.clone())],
                     [this.date_start, '<=', format(end.clone())]];

            if (this.date_stop) {
                //add at start 
                extend_domain.splice(0,0,'|','|','&');
                //add at end 
                extend_domain.push(
                                '&',
                                [this.date_start, '<=', format(start.clone())],
                                [this.date_stop, '>=', format(start.clone())],
                                '&',
                                [this.date_start, '<=', format(end.clone())],
                                [this.date_stop, '>=', format(start.clone())]
                );
                //final -> (A & B) | (C & D) | (E & F) ->  | | & A B & C D & E F
            }
            return new instance.web.CompoundDomain(domain, extend_domain);
        },

        /**
         * Updates record identified by ``id`` with values in object ``data``
         */
        update_record: function(id, data) {
            var self = this;
            delete(data.name); // Cannot modify actual name yet
            var index = this.dataset.get_id_index(id);
            if (index !== null) {
                event_id = this.dataset.ids[index];
                this.dataset.write(event_id, data, {}).done(function() {
                    if (is_virtual_id(event_id)) {
                        // this is a virtual ID and so this will create a new event
                        // with an unknown id for us.
                        self.$calendar.fullCalendar('refetchEvents');
                    } else {
                        // classical event that we can refresh
                        self.refresh_event(event_id);
                    }
                });
            }
            return false;
        },
        open_event: function(id,title) {
            var self = this;
            var event_objs = self.$calendar.fullCalendar('clientEvents', id);
            if (event_objs.length == 1) {
                event_objs = event_objs[0];
            } else {
                event_objs = null;
            }

            if (! this.open_popup_action) {
                var index = this.dataset.get_id_index(id);
                this.dataset.index = index;
                this.do_switch_view('form', null,
                                    { mode: (event_objs && event_objs.access.edit) ? "edit" : "view" });
            }
            else {
                var def = $.Deferred();
                var pop = new instance.web.form.FormOpenPopup(this);
                pop.show_element(this.dataset.model, id, this.dataset.get_context(), {
                    title: _.str.sprintf(_t("View: %s"),title),
                    view_id: +this.open_popup_action,
                    res_id: id,
                    target: 'new',
                    readonly:true
                });

               var form_controller = pop.view_form;
               form_controller.on("load_record", self, function(){
                    button_delete = _.str.sprintf("<button class='oe_button oe_bold delme'><span> %s </span></button>",_t("Delete"));
                    button_edit = _.str.sprintf("<button class='oe_button oe_bold editme oe_highlight'><span> %s </span></button>",_t("Edit Event"));
                    
                    if (event_objs && event_objs.access.edit) {
                        pop.$el.closest(".ui-dialog").find(".ui-dialog-buttonpane").prepend(button_delete);
                    }
                    if (event_objs && event_objs.access.unlink) {
                        pop.$el.closest(".ui-dialog").find(".ui-dialog-buttonpane").prepend(button_edit);
                    }

                    $('.delme').click(
                        function() {
                            $('.oe_form_button_cancel').trigger('click');
                            self.remove_event(id);
                        }
                    );
                    $('.editme').click(
                        function() {
                            $('.oe_form_button_cancel').trigger('click');
                            self.dataset.index = self.dataset.get_id_index(id);
                            self.do_switch_view('form', null, { mode: "edit" });

                        }
                    );
               });
                pop.on('closed', self, function() {
                    // ``self.trigger('close')`` would itself destroy all child element including
                    // the slow create popup, which would then re-trigger recursively the 'closed' signal.
                    // Thus, here, we use a deferred and its state to cut the endless recurrence.
                    if (def.state() === "pending") {
                        def.resolve();
                    }
                });
                def.then(function() {
                    // after closing the popup, force refetching the events.
                    self.$calendar.fullCalendar('refetchEvents');
                });
            }
            return false;
        },

        do_show: function() {
            if (this.$buttons) {
                this.$buttons.show();
            }
            this.do_push_state({});
            return this._super();
        },
        do_hide: function () {
            if (this.$buttons) {
                this.$buttons.hide();
            }
            return this._super();
        },
        is_action_enabled: function(action) {
            if (action === 'create' && !this.options.creatable) {
                return false;
            }
            return this._super(action);
        },

        /**
         * Handles a newly created record
         *
         * @param {id} id of the newly created record
         */
        quick_created: function (id) {

            /** Note:
             * it's of the most utter importance NOT to use inplace
             * modification on this.dataset.ids as reference to this
             * data is spread out everywhere in the various widget.
             * Some of these reference includes values that should
             * trigger action upon modification.
             */
            this.dataset.ids = this.dataset.ids.concat([id]);
            this.dataset.trigger("dataset_changed", id);
            this.refresh_event(id);
        },
        slow_created: function () {
            // refresh all view, because maybe some recurrents item
            var self = this;
            if (self.sidebar) {
                // force filter refresh
                self.sidebar.filter.is_loaded = false;
            }
            self.$calendar.fullCalendar('refetchEvents');
        },

        remove_event: function(id) {
            var self = this;
            function do_it() {
                return $.when(self.dataset.unlink([id])).then(function() {
                    self.$calendar.fullCalendar('removeEvents', id);
                });
            }
            if (this.options.confirm_on_delete) {
                if (confirm(_t("Are you sure you want to delete this record ?"))) {
                    return do_it();
                }
            } else
                return do_it();
        },
    });


    /**
     * Quick creation view.
     *
     * Triggers a single event "added" with a single parameter "name", which is the
     * name entered by the user
     *
     * @class
     * @type {*}
     */
    instance.web_calendar.QuickCreate = instance.web.Widget.extend({
        template: 'CalendarView.quick_create',
        
        init: function(parent, dataset, buttons, options, data_template) {
            this._super(parent);
            this.dataset = dataset;
            this._buttons = buttons || false;
            this.options = options;

            // Can hold data pre-set from where you clicked on agenda
            this.data_template = data_template || {};
        },
        get_title: function () {
            var parent = this.getParent();
            if (_.isUndefined(parent)) {
                return _t("Create");
            }
            var title = (_.isUndefined(parent.field_widget)) ?
                    (parent.string || parent.name) :
                    parent.field_widget.string || parent.field_widget.name || '';
            return _t("Create: ") + title;
        },
        start: function () {
            var self = this;

            if (this.options.disable_quick_create) {
                this.$el.hide();
                this.slow_create();
                return;
            }

            self.$input = this.$el.find('input');
            self.$input.keyup(function enterHandler (event) {
                if(event.keyCode == 13){
                    self.$input.off('keyup', enterHandler);
                    if (!self.quick_add()){
                        self.$input.on('keyup', enterHandler);
                    }
                }
            });
            
            var submit = this.$el.find(".oe_calendar_quick_create_add");
            submit.click(function clickHandler() {
                submit.off('click', clickHandler);
                if (!self.quick_add()){
                   submit.on('click', clickHandler);                }
                self.focus();
            });
            this.$el.find(".oe_calendar_quick_create_edit").click(function () {
                self.slow_add();
                self.focus();
            });
            this.$el.find(".oe_calendar_quick_create_close").click(function (ev) {
                ev.preventDefault();
                self.trigger('close');
            });
            self.$input.keyup(function enterHandler (e) {
                if (e.keyCode == 27 && self._buttons) {
                    self.trigger('close');
                }
            });
            self.$el.dialog({ title: this.get_title()});
            self.on('added', self, function() {
                self.trigger('close');
            });
            
            self.$el.on('dialogclose', self, function() {
                self.trigger('close');
            });

        },
        focus: function() {
            this.$el.find('input').focus();
        },

        /**
         * Gathers data from the quick create dialog a launch quick_create(data) method
         */
        quick_add: function() {
            var val = this.$input.val();
            if (/^\s*$/.test(val)) {
                return false;
            }
            return this.quick_create({'name': val}).always(function() { return true; });
        },
        
        slow_add: function() {
            var val = this.$input.val();
            this.slow_create({'name': val});
        },

        /**
         * Handles saving data coming from quick create box
         */
        quick_create: function(data, options) {
            var self = this;
            return this.dataset.create($.extend({}, this.data_template, data), options)
                .then(function(id) {
                    self.trigger('added', id);
                    self.$input.val("");
                }).fail(function(r, event) {
                    event.preventDefault();
                    // This will occurs if there are some more fields required
                    self.slow_create(data);
                });
        },

        /**
         * Show full form popup
         */
         get_form_popup_infos: function() {
            var parent = this.getParent();
            var infos = {
                view_id: false,
                title: this.name,
            };
            if (!_.isUndefined(parent) && !(_.isUndefined(parent.ViewManager))) {
                infos.view_id = parent.ViewManager.get_view_id('form');
            }
            return infos;
        },
        slow_create: function(data) {
            //if all day, we could reset time to display 00:00:00
            
            var self = this;
            var def = $.Deferred();
            var defaults = {};

            _.each($.extend({}, this.data_template, data), function(val, field_name) {
                defaults['default_' + field_name] = val;
            });
                        
            var pop_infos = self.get_form_popup_infos();
            var pop = new instance.web.form.FormOpenPopup(this);
            var context = new instance.web.CompoundContext(this.dataset.context, defaults);
            pop.show_element(this.dataset.model, null, this.dataset.get_context(defaults), {
                title: this.get_title(),
                disable_multiple_selection: true,
                view_id: pop_infos.view_id,
                // Ensuring we use ``self.dataset`` and DO NOT create a new one.
                create_function: function(data, options) {
                    return self.dataset.create(data, options).done(function(r) {
                    }).fail(function (r, event) {
                       if (!r.data.message) { //else manage by openerp
                            throw new Error(r);
                       }
                    });
                },
                read_function: function(id, fields, options) {
                    return self.dataset.read_ids.apply(self.dataset, arguments).done(function() {
                    }).fail(function (r, event) {
                        if (!r.data.message) { //else manage by openerp
                            throw new Error(r);
                        }
                    });
                },
            });
            pop.on('closed', self, function() {
                // ``self.trigger('close')`` would itself destroy all child element including
                // the slow create popup, which would then re-trigger recursively the 'closed' signal.  
                // Thus, here, we use a deferred and its state to cut the endless recurrence.
                if (def.state() === "pending") {
                    def.resolve();
                }
            });
            pop.on('create_completed', self, function(id) {
                 self.trigger('slowadded');
            });
            def.then(function() {
                self.trigger('close');
            });
            return def;
        },
    });


    /**
     * Form widgets
     */

    function widget_calendar_lazy_init() {
        if (instance.web.form.Many2ManyCalendarView) {
            return;
        }

        instance.web_calendar.FieldCalendarView = instance.web_calendar.CalendarView.extend({

            init: function (parent) {
                this._super.apply(this, arguments);
                // Warning: this means only a field_widget should instanciate this Class
                this.field_widget = parent;
            },

            view_loading: function (fv) {
                var self = this;
                return $.when(this._super.apply(this, arguments)).then(function() {
                    self.on('event_rendered', this, function (event, element, view) {

                    });
                });
            },

            // In forms, we could be hidden in a notebook. Thus we couldn't
            // render correctly fullcalendar so we try to detect when we are
            // not visible to wait for when we will be visible.
            init_calendar: function() {
                if (this.$calendar.width() !== 0) { // visible
                    return this._super();
                }
                // find all parents tabs.
                var def = $.Deferred();
                var self = this;
                this.$calendar.parents(".ui-tabs").on('tabsactivate', this, function() {
                    if (self.$calendar.width() !== 0) { // visible
                        self.$calendar.fullCalendar(self.get_fc_init_options());
                        def.resolve();
                    }
                });
                return def;
            },
        });
    }

    instance.web_calendar.BufferedDataSet = instance.web.BufferedDataSet.extend({

        /**
         * Adds verification on possible missing fields for the sole purpose of
         * O2M dataset being compatible with the ``slow_create`` detection of
         * missing fields... which is as simple to try to write and upon failure
         * go to ``slow_create``. Current BufferedDataSet would'nt fail because
         * they do not send data to the server at create time.
         */
        create: function (data, options) {
            var def = $.Deferred();
            var self = this;
            var create = this._super;
            if (_.isUndefined(this.required_fields)) {
                this.required_fields = (new instance.web.Model(this.model))
                    .call('fields_get').then(function (fields_def) {
                        return _(fields_def).chain()
                         // equiv to .pairs()
                            .map(function (value, key) { return [key, value]; })
                         // equiv to .omit(self.field_widget.field.relation_field)
                            .filter(function (pair) { return pair[0] !== self.field_widget.field.relation_field; })
                            .filter(function (pair) { return pair[1].required; })
                            .map(function (pair) { return pair[0]; })
                            .value();
                    });
            }
            $.when(this.required_fields).then(function (required_fields) {
                var missing_fields = _(required_fields).filter(function (v) {
                    return _.isUndefined(data[v]);
                });
                var default_get = (missing_fields.length !== 0) ?
                    self.default_get(missing_fields) : [];
                $.when(default_get).then(function (defaults) {

                    // Remove all fields that have a default from the missing fields.
                    missing_fields = _(missing_fields).filter(function (f) {
                        return _.isUndefined(defaults[f]);
                    });
                    if (missing_fields.length !== 0) {
                        def.reject(
                            _.str.sprintf(
                                _t("Missing required fields %s"), missing_fields.join(", ")),
                            $.Event());
                        return;
                    }
                    create.apply(self, [data, options]).then(function (result) {
                        def.resolve(result);
                    });
                });
            });
            return def;
        },
    });

    instance.web_calendar.fields_dataset = new instance.web.Registry({
        'many2many': 'instance.web.DataSetStatic',
        'one2many': 'instance.web_calendar.BufferedDataSet',
    });


    function get_field_dataset_class(type) {
        var obj = instance.web_calendar.fields_dataset.get_any([type]);
        if (!obj) {
            throw new Error(_.str.sprintf(_t("Dataset for type '%s' is not defined."), type));
        }

        // Override definition of legacy datasets to add field_widget context
        return obj.extend({
            init: function (parent) {
                this._super.apply(this, arguments);
                this.field_widget = parent;
            },
            get_context: function() {
                this.context = this.field_widget.build_context();
                return this.context;
            }
        });
    }

    /**
     * Common part to manage any field using calendar view
     */
    instance.web_calendar.FieldCalendar = instance.web.form.AbstractField.extend({

        disable_utility_classes: true,
        calendar_view_class: 'instance.web_calendar.FieldCalendarView',

        init: function(field_manager, node) {
            this._super(field_manager, node);
            widget_calendar_lazy_init();
            this.is_loaded = $.Deferred();
            this.initial_is_loaded = this.is_loaded;

            var self = this;

            // This dataset will use current widget to '.build_context()'.
            var field_type = field_manager.fields_view.fields[node.attrs.name].type;
            this.dataset = new (get_field_dataset_class(field_type))(
                this, this.field.relation);

            this.dataset.on('unlink', this, function(_ids) {
                this.dataset.trigger('dataset_changed');
            });

            // quick_create widget instance will be attached when spawned
            this.quick_create = null;

            this.no_rerender = true;

        },

        start: function() {
            this._super.apply(this, arguments);

            var self = this;

            self.load_view();
            self.on("change:effective_readonly", self, function() {
                self.is_loaded = self.is_loaded.then(function() {
                    self.calendar_view.destroy();
                    return $.when(self.load_view()).done(function() {
                        self.render_value();
                    });
                });
            });
        },

        load_view: function() {
            var self = this;
            var calendar_view_class = get_class(this.calendar_view_class);
            this.calendar_view = new calendar_view_class(this, this.dataset, false, $.extend({
                'create_text': _t("Add"),
                'creatable': self.get("effective_readonly") ? false : true,
                'quick_creatable': self.get("effective_readonly") ? false : true,
                'read_only_mode': self.get("effective_readonly") ? true : false,
                'confirm_on_delete': false,
            }, this.options));
            var embedded = (this.field.views || {}).calendar;
            if (embedded) {
                this.calendar_view.set_embedded_view(embedded);
            }
            var loaded = $.Deferred();
            this.calendar_view.on("calendar_view_loaded", self, function() {
                self.initial_is_loaded.resolve();
                loaded.resolve();
            });
            this.calendar_view.on('switch_mode', this, this.open_popup);
            $.async_when().done(function () {
                self.calendar_view.appendTo(self.$el);
            });
            return loaded;
        },

        render_value: function() {
            var self = this;
            this.dataset.set_ids(this.get("value"));
            this.is_loaded = this.is_loaded.then(function() {
                return self.calendar_view.do_search(self.build_domain(), self.dataset.get_context(), []);
            });
        },

        open_popup: function(type, unused) {
            if (type !== "form") { return; }
            if (this.dataset.index == null) {
                if (typeof this.open_popup_add === "function") {
                    this.open_popup_add();
                }
            } else {
                if (typeof this.open_popup_edit === "function") {
                    this.open_popup_edit();
                }
            }
        },

        open_popup_add: function() {
            throw new Error("Not Implemented");
        },

        open_popup_edit: function() {
            var id = this.dataset.ids[this.dataset.index];
            var self = this;
            var pop = (new instance.web.form.FormOpenPopup(this));
            pop.show_element(this.field.relation, id, this.build_context(), {
                title: _t("Open: ") + this.string,
                write_function: function(id, data, _options) {
                    return self.dataset.write(id, data, {}).done(function() {
                        // Note that dataset will trigger itself the
                        // ``dataset_changed`` signal
                        self.calendar_view.refresh_event(id);
                    });
                },
                read_function: function(id, fields, options) {
                    return self.dataset.read_ids.apply(self.dataset, arguments).done(function() {
                    }).fail(function (r, event) {
                        throw new Error(r);
                    });
                },

                alternative_form_view: this.field.views ? this.field.views.form : undefined,
                parent_view: this.view,
                child_name: this.name,
                readonly: this.get("effective_readonly")
            });
        }
    });

    instance.web_calendar.Sidebar = instance.web.Widget.extend({
        template: 'CalendarView.sidebar',
        
        start: function() {
            this._super();
            this.filter = new instance.web_calendar.SidebarFilter(this, this.getParent());
            this.filter.appendTo(this.$el.find('.oe_calendar_filter'));
        }
    });
    instance.web_calendar.SidebarFilter = instance.web.Widget.extend({
        events: {
            'change input:checkbox': 'filter_click'
        },
        init: function(parent, view) {
            this._super(parent);
            this.view = view;
        },
        set_filters: function() {
            var self = this;
            _.forEach(self.view.all_filters, function(o) {
                if (_.contains(self.view.now_filter_ids, o.value)) {
                    self.$('div.oe_calendar_responsible input[value=' + o.value + ']').prop('checked',o.is_checked);
                }
            });
        },
        events_loaded: function(filters) {
            var self = this;

            if (filters == null) {
                filters = [];
                _.forEach(self.view.all_filters, function(o) {
                    if (_.contains(self.view.now_filter_ids, o.value)) {
                        filters.push(o);
                    }
                });
            }            

            if (this.view.useContacts) {
                // Ensure 'All calendars' item always appears last.
                filters = _.values(filters).sort(function(a, b) {
                    if (a.value === -1) { return 1; }
                    if (b.value == -1) { return -1; }
                    return 0;
                });
            }
            this.$el.html(QWeb.render('CalendarView.sidebar.responsible', { filters: filters, session_id: instance.session.session_id }));
        },
        filter_click: function(e) {
            var self = this;            
            self.view.all_filters[parseInt(e.target.value)].is_checked = e.target.checked;
            self.view.$calendar.fullCalendar('refetchEvents');
        },
        addUpdateButton: function() {
            var self=this;
            this.$('div.oe_calendar_all_responsibles').append(QWeb.render('CalendarView.sidebar.button_add_contact'));
            this.$(".add_contacts_link_btn").on('click', function() {
                self.rpc("/web/action/load", {
                    action_id: "core_calendar.action_calendar_contacts"
                }).then( function(result) { return self.do_action(result); });
            });
            
        },
    });

    instance.web_calendar.EventPopover = instance.web.Widget.extend({
        template: 'CalendarView.popover',
        init: function(parent) {
            this._super(parent);
            this.view = this.getParent();
            this.displayed_event_id = null;
            this.pos = null;
        },
        start: function() {
            var self = this;
            this.$content = this.$el.find('.oe_calendar_popover_content');
            this.$buttons = this.$el.find('.oe_calendar_button_box');
            this.$el.find('.oe_calendar_action_close').on('click', this.proxy('hide'));
            $(window).on('keydown:fullcalendar-event-popover', function(e) {
                if (e.which === $.ui.keyCode.ESCAPE) {
                    self.hide();
                }
            });
            $(window).on('click:fullcalendar-event-popover', function(ev) {
                if (self.$el.is(':visible')) {
                    var target = ev.target || ev.srcElement;
                    if (self.$el.find(target).length === 0) {
                        // Clicked outside of popup, hiding it
                        self.hide();
                    }
                }
            });
            return $.when();
        },
        destroy: function() {
            if (this.$el) {
                this.$el.find('.oe_calendar_popover_close').off();
                this.$el.find('a.oe_button').off();
            }
            $(window).off('keydown:fullcalendar-event-popover');
            $(window).off('click:fullcalendar-event-popover');
            this._super();
        },
        event_clicked: function(event, jsEvent, view) {
            if (event.id == this.displayed_event_id) {
                this.hide();
                return;
            }
            // Set popup position
            this.pos = {
                x: jsEvent.pageX,
                y: jsEvent.pageY
            };
            this.show(event);
        },
        show: function(event) {
            if (!!this.pos) {
                this.render_popover(event);
                this.$el.css('left', this.pos.x - this.$el.width() / 2.0 - this.$el.parent().offset().left);
                this.$el.css('top', this.pos.y - this.$el.height() - 12 - this.$el.parent().offset().top);
                this.$el.css('display', 'block');
                this.displayed_event_id = event.id;
                this.$el.find('.oe_calendar_popover').trigger('focusin');
            }
        },
        hide: function() {
            this.$el.css('display', 'none');
            this.displayed_event_id = null;
        },
        render_popover: function(event) {
            var self = this;
            var qweb_context = _.extend({}, this.view.qweb_context || {}, {
                widget: this,
                display_short: true,
                record: event.record,
                event_start: event.start,
                event_end: event.end,
                event_title: event.title,
                event_is_allday: event.allDay,
                event_access: event.access,
                custom_title: true
            });
            // popover-content
            this.$content.html(this.view.qweb.render('CalendarView.popover.layout', qweb_context));

            // popover-buttons
            this.$buttons.find('.oe_button').off('click');
            this.$buttons.html(this.view.qweb.render('CalendarView.popover.buttons', qweb_context));
            this.$el.find('.oe_calendar_button_edit').on('click', function() {
                var displayed_event = self.view.$calendar.fullCalendar('clientEvents', self.displayed_event_id)[0];
                self.view.open_event(self.displayed_event_id, displayed_event.title);
                self.hide();
            });
            this.$el.find('.oe_calendar_button_delete').on('click', function() {
                self.view.remove_event(self.displayed_event_id);
                self.hide();
            });
        }
    });

};
