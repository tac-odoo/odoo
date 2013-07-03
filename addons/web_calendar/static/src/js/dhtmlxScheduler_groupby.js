// Monkey patch dhtmlxScheduler instance ('scheduler') to add support
// for group_by.
if (!scheduler.web_calendar_groupby) {

scheduler.web_calendar_groupby = true;
scheduler._sections = {};

scheduler.templates['day_section_label'] = function(section) {
    return section ? section.label : '';
};
scheduler.templates['week_section_label'] = function(section) {
    return section ? section.label : '';
};

scheduler.is_group_by_mode = function() {
    if (this.config && this.config.section_key &&
        (this._mode == 'day' || this._mode == 'week')) {
        return true;
    }
    return false;
};

var old_reset_hours_scale = scheduler._reset_hours_scale;
scheduler._reset_hours_scale = function(b,dd,sd) {
    if (!this.is_group_by_mode()) {
        return old_reset_hours_scale.apply(this, arguments);
    }
    var c=document.createElement("DIV");
    c.className="dhx_scale_holder";
    c.style.left = this.config.section_width+"px";

    var date = new Date(1980,1,1,this.config.first_hour,0,0);
    for (var i=this.config.first_hour*1; i < this.config.last_hour; i++) {
        var cc=document.createElement("DIV");
        cc.className="dhx_scale_hour";
        cc.style.height=this.config.section_hour_size_px-(this._quirks?0:1)+"px";
        cc.style.width=this.xy.scale_width+"px";
        cc.style.lineHeight = cc.style.height;
        cc.innerHTML=scheduler.templates.hour_scale(date);

        c.appendChild(cc);
        date=this.date.add(date,1,"hour");
    }
    b.appendChild(c);
};

scheduler._reset_section = function(b, section) {
    if (!this.is_group_by_mode()) {
        return;
    }
    var view_mode = this._mode;
    var c = document.createElement("DIV");
    c.className="dhx_matrix_scell"
    c.style.left = 0;
    c.style.height = (((this.config.last_hour - (this.config.first_hour*1)) * this.config.section_hour_size_px) - (this._quirks?0:1))+"px";
    c.style.width = (this.config.section_width-1)+"px";
    var cspan = document.createElement("DIV");
    cspan.innerHTML = scheduler.templates[view_mode+"_section_label"](section);
    c.appendChild(cspan);
    b.appendChild(c);
    return true;
};

var old_pre_render_events = scheduler._pre_render_events;
scheduler._pre_render_events = function(evs, hold) {
    // TODO: improve this!
    if (!this.is_group_by_mode()) {
        return old_pre_render_events.apply(this, arguments);
    }
    var hb = this.xy.bar_height;
    var h_old = this._colsS.heights;
    var h = this._colsS.heights = [0, 0, 0, 0, 0, 0, 0];
    var data = this._els["dhx_cal_data"][0];

    if (!this._table_view)
        evs = this._pre_render_events_line(evs, hold); //ignore long events for now
    //else
    //    evs = this._pre_render_events_table(evs, hold);

    return evs;  // FIXME: this is juste a temporary hack
    //
    //
    //
    //
    if (this._table_view) {
        if (hold)
            this._colsS.heights = h_old;
        else {
            var evl = data.firstChild;
            if (evl.rows) {
                for (var i = 0; i < evl.rows.length; i++) {
                    h[i]++;
                    if ((h[i]) * hb > this._colsS.height - 22) { // 22 - height of cell's header
                        //we have overflow, update heights
                        var cells = evl.rows[i].cells;
                        for (var j = 0; j < cells.length; j++) {
                            cells[j].childNodes[1].style.height = h[i] * hb + "px";
                        }
                        h[i] = (h[i - 1] || 0) + cells[0].offsetHeight;
                    }
                    h[i] = (h[i - 1] || 0) + evl.rows[i].cells[0].offsetHeight;
                }
                h.unshift(0);
                if (evl.parentNode.offsetHeight < evl.parentNode.scrollHeight && !evl._h_fix) {
                    //we have v-scroll, decrease last day cell
                    for (var i = 0; i < evl.rows.length; i++) {
                        var cell = evl.rows[i].cells[6].childNodes[0];
                        var w = cell.offsetWidth - scheduler.xy.scroll_width + "px";
                        cell.style.width = w;
                        cell.nextSibling.style.width = w;
                    }
                    evl._h_fix = true;
                }
            } else {
                if (!evs.length && this._els["dhx_multi_day"][0].style.visibility == "visible")
                    h[0] = -1;
                if (evs.length || h[0] == -1) {
                    //shift days to have space for multiday events
                    var childs = evl.parentNode.childNodes;
                    var dh = ((h[0] + 1) * hb + 1) + "px"; // +1 so multiday events would have 2px from top and 2px from bottom by default
                    data.style.top = (this._els["dhx_cal_navline"][0].offsetHeight + this._els["dhx_cal_header"][0].offsetHeight + parseInt(dh, 10)) + 'px';
                    data.style.height = (this._obj.offsetHeight - parseInt(data.style.top, 10) - (this.xy.margin_top || 0)) + 'px';
                    var last = this._els["dhx_multi_day"][0];
                    last.style.height = dh;
                    last.style.visibility = (h[0] == -1 ? "hidden" : "visible");
                    last = this._els["dhx_multi_day"][1];
                    last.style.height = dh;
                    last.style.visibility = (h[0] == -1 ? "hidden" : "visible");
                    last.className = h[0] ? "dhx_multi_day_icon" : "dhx_multi_day_icon_small";
                    this._dy_shift = (h[0] + 1) * hb;
                    h[0] = 0;
                }
            }
        }
    }

    return evs;
};

var old_pre_render_events_line = scheduler._pre_render_events_line;
scheduler._pre_render_events_line = function(evs, hold) {
    if (!this.is_group_by_mode()) {
        return old_pre_render_events_line.apply(this, arguments);
    }
    evs.sort(function(a, b) {
        if (a.start_date.valueOf() == b.start_date.valueOf())
            return a.id > b.id ? 1 : -1;
        return a.start_date > b.start_date ? 1 : -1;
    });
    var days = []; //events by weeks
    var evs_originals = [];
    this._min_mapped_duration = Math.ceil(this.xy.min_event_height * 60 / this.config.section_hour_size_px);  // values could change along the way
    for (var i = 0; i < evs.length; i++) {
        var ev = evs[i];

        //check date overflow
        var sd = ev.start_date;
        var ed = ev.end_date;
        //check scale overflow
        var sh = sd.getHours();
        var eh = ed.getHours();

        ev._sday = this._get_event_sday(ev); // sday based on event start_date
        var ev_section = ev['section_key'];
        if (!days[ev._sday]) days[ev._sday] = {};
        if (!days[ev._sday][ev_section]) days[ev._sday][ev_section] = [];

        if (!hold) {
            ev._inner = false;

            // xal: #2: fix max_count per section
            var stack = days[ev._sday][ev_section];

            while (stack.length) {
                var t_ev = stack[stack.length - 1];
                var t_end_date = this._get_event_mapped_end_date(t_ev);
                if (t_end_date.valueOf() <= ev.start_date.valueOf()) {
                    stack.splice(stack.length - 1, 1);
                } else {
                    break;
                }
            }

            var sorderSet = false;
            for (var j = 0; j < stack.length; j++) {
                var t_ev = stack[j];
                var t_end_date = this._get_event_mapped_end_date(t_ev);
                if (t_end_date.valueOf() <= ev.start_date.valueOf()) {
                    sorderSet = true;
                    ev._sorder = t_ev._sorder;
                    stack.splice(j, 1);
                    ev._inner = true;
                    break;
                }
            }

            if (stack.length)
                stack[stack.length - 1]._inner = true;

            if (!sorderSet) {
                if (stack.length) {
                    if (stack.length <= stack[stack.length - 1]._sorder) {
                        if (!stack[stack.length - 1]._sorder)
                            ev._sorder = 0;
                        else
                            for (j = 0; j < stack.length; j++) {
                                var _is_sorder = false;
                                for (var k = 0; k < stack.length; k++) {
                                    if (stack[k]._sorder == j) {
                                        _is_sorder = true;
                                        break;
                                    }
                                }
                                if (!_is_sorder) {
                                    ev._sorder = j;
                                    break;
                                }
                            }
                        ev._inner = true;
                    } else {
                        var _max_sorder = stack[0]._sorder;
                        for (j = 1; j < stack.length; j++) {
                            if (stack[j]._sorder > _max_sorder)
                                _max_sorder = stack[j]._sorder;
                        }
                        ev._sorder = _max_sorder + 1;
                        ev._inner = false;
                    }

                } else
                    ev._sorder = 0;
            }

            stack.push(ev);

            if (stack.length > (stack.max_count || 0)) {
                stack.max_count = stack.length;
                ev._count = stack.length;
            } else {
                ev._count = (ev._count) ? ev._count : 1;
            }
        }
        if (sh < this.config.first_hour || eh >= this.config.last_hour) {
            // Need to create copy of event as we will be changing it's start/end date
            // e.g. first_hour = 11 and event.start_date hours = 9. Need to preserve that info
            evs_originals.push(ev);
            evs[i] = ev = this._copy_event(ev);

            if (sh < this.config.first_hour) {
                ev.start_date.setHours(this.config.first_hour);
                ev.start_date.setMinutes(0);
            }
            if (eh >= this.config.last_hour) {
                ev.end_date.setMinutes(0);
                ev.end_date.setHours(this.config.last_hour);
            }

            if (ev.start_date > ev.end_date || sh == this.config.last_hour) {
                evs.splice(i, 1);
                i--;
                continue;
            }
        }
    }
    if (!hold) {
        for (var i = 0; i < evs.length; i++) {
            var skey = evs[i]['section_key'];
            evs[i]._count = days[evs[i]._sday][skey].max_count;
        }
        for (var i = 0; i < evs_originals.length; i++) {
            // xal: #2: fix max_count per section
            var skey = evs_originals[i]['section_key'];
            evs_originals[i]._count = days[evs_originals[i]._sday][skey].max_count;
        }
    }

    return evs;
};

var old_set_size = scheduler.set_sizes;
scheduler.set_sizes = function() {
    if (!this.is_group_by_mode()) {
        return old_set_size.apply(this, arguments);
    }
    var w = this._x = this._obj.clientWidth-this.xy.margin_left;
    var h = this._y = this._obj.clientHeight-this.xy.margin_top;

    //not-table mode always has scroll - need to be fixed in future
    var scale_x=this._table_view?0:(this.xy.scale_width+this.xy.scroll_width);
    var scale_s=this._table_view?-1:this.xy.scale_width;

    var section_w = this.config.section_width;

    this.set_xy(this._els["dhx_cal_navline"][0],w,this.xy.nav_height,0,0);
    this.set_xy(this._els["dhx_cal_header"][0],w-scale_x-section_w,this.xy.scale_height,scale_s+section_w,this.xy.nav_height+(this._quirks?-1:1));
    //to support alter-skin, we need a way to alter height directly from css
    var actual_height = this._els["dhx_cal_navline"][0].offsetHeight;
    if (actual_height > 0) this.xy.nav_height = actual_height;

    var data_y=this.xy.scale_height+this.xy.nav_height+(this._quirks?-2:0);
    this.set_xy(this._els["dhx_cal_data"][0],w,h-(data_y+2),0,data_y+2);
};

var old_reset_scale = scheduler._reset_scale;
scheduler._reset_scale = function() {
    if (!this.is_group_by_mode()) {
        return old_reset_scale.apply(this, arguments);
    }
    //current mode doesn't support scales
    //we mustn't call reset_scale for such modes, so it just to be sure
    if (!this.templates[this._mode + "_date"]) return;

    var h = this._els["dhx_cal_header"][0];
    var b = this._els["dhx_cal_data"][0];
    var c = this.config;

    h.innerHTML = "";
    b.scrollTop = 0; //fix flickering in FF
    b.innerHTML = "";

    var str = ((c.readonly || (!c.drag_resize)) ? " dhx_resize_denied" : "") + ((c.readonly || (!c.drag_move)) ? " dhx_move_denied" : "");
    if (str) b.className = "dhx_cal_data" + str;

    this._scales = {};
    this._sections = {};
    this._cols = [];    //store for data section
    this._colsS = {height: 0};
    this._dy_shift = 0;
    this.set_sizes();
    var summ=parseInt(h.style.width,10); //border delta
    var left=0;

    var d,dd,sd,today;
    dd=this.date[this._mode+"_start"](new Date(this._date.valueOf()));
    d=sd=this._table_view?scheduler.date.week_start(dd):dd;
    today=this.date.date_part(new Date());

    //reset date in header
    var ed=scheduler.date.add(dd,1,this._mode);
    var count = 7;

    if (!this._table_view){
        var count_n = this.date["get_"+this._mode+"_end"];
        if (count_n) ed = count_n(dd);
        count = Math.round((ed.valueOf()-dd.valueOf())/(1000*60*60*24));
    }

    this._min_date=d;
    this._els["dhx_cal_date"][0].innerHTML=this.templates[this._mode+"_date"](dd,ed,this._mode);

    // create columns (1 per day)
    var column_summ = summ;
    for (var i=0; i<count; i++) {
        this._cols[i] = Math.floor(column_summ/(count-i));
        column_summ -= this._cols[i];
        this._colsS[i]=(this._cols[i-1]||0)+(this._colsS[i-1]||(this._table_view?0:this.xy.scale_width+this.config.section_width+2));
        this._colsS['col_length'] = count+1;
    }
    this._colsS[count]=this._cols[count-1]+this._colsS[count-1];

    // render calendar header
    var header_left=left;
    for (var i=0; i<count; i++) {
        var column_date = this.date.add(d, i, "day");
        this._render_x_header(i, header_left, column_date, h);
        header_left += this._cols[i];
    }
    //this._max_date=d;
    this._max_date = this.date.add(d, count, "day");

    var sections = this.config.sections;
    if (!sections || (sections && sections.length ==0)) {
        sections = [{key: false, label: 'Undefined'}];
    }

    // create section container and scales
    var section_top = 0;
    for (var sidx=0; sidx < sections.length; sidx++) {
        var section = {
            'order': sidx,
            'key': sections[sidx].key,
            'label': sections[sidx].label,
            'element': document.createElement("DIV"),
            'top': section_top,
            'width': parseInt(b.style.width) - this.xy.scroll_width,
            'height': 0,
            'data_element': null,
            'multiday_element': null,
            'multiday_icon_element': null,
        };
        this._sections[section.key] = section;
        b.appendChild(section.element);

        /* create section structured
         *   ________________________
         *  | sect. | multi day evt. |
         *  | name  | -------------- |
         *  |       | std evt. std ev|
         *  |_______|________________|
         */
        var section_data = document.createElement("DIV");
        section.element.appendChild(section_data);
        section.data_element = section_data;


        var left = 0;
        for (var i=0; i<this._cols.length; i++) {
            var column_date = this.date.add(d, i, "day");

            if (!this._table_view) { // i.e not month or timeline
                var scale = document.createElement("DIV");
                var scale_class = (column_date.valueOf() == today.valueOf()) ? "dhx_scale_holder_now" : "dhx_scale_holder";
                scale.className = scale_class+" "+this.templates.week_date_class(column_date, today);

                // set background image size relative to hour_size_px
                scale.style.backgroundSize = "auto "+this.config.section_hour_size_px+"px";
                // then force scale position
                var scale_width = this._cols[i] - 1,
                    scale_height = this.config.section_hour_size_px*(this.config.last_hour-this.config.first_hour),
                    scale_left = left+this.xy.scale_width+this.config.section_width+1,
                    scale_top = 0; // -1 for border
                this.set_xy(scale, scale_width, scale_height, scale_left, scale_top);
                left += scale_width + 1;

                section.data_element.appendChild(scale);
                this.callEvent("onScaleAdd", [scale, column_date, section]); // TODO: need to fix signature for "section scale added" events"

                section.height = Math.max(section.height, scale_height);
            };
        }

        // update section data sizes
        // fix section sizes
        this.set_xy(section.data_element, section.width, section.height, 0, 0);
        section.data_element.style.position = "absolute";

        if (this._table_view) { // month view
            this._reset_month_scale(section.data_element,dd,sd); // TEST ME
        } else {
            this._reset_hours_scale(section.data_element,dd,sd);

            if (c.multi_day) {
                var dhx_multi_day = 'dhx_multi_day';

            //  if(this._els[dhx_multi_day]) {
            //      this._els[dhx_multi_day][0].parentNode.removeChild(this._els[dhx_multi_day][0]);
            //      this._els[dhx_multi_day] = null;
            //  }

            //  var navline = this._els["dhx_cal_navline"][0];
            //  var top = navline.offsetHeight + this._els["dhx_cal_header"][0].offsetHeight+1;
                var top = section.top;

                var c1 = document.createElement("DIV");
                c1.className = dhx_multi_day;
                c1.style.visibility="hidden";
                this.set_xy(c1, this._colsS[this._colsS.col_length-1]+this.xy.scroll_width+this.config.section_width, 0, 0, top); // 2 extra borders, dhx_header has -1 bottom margin
                section.element.insertBefore(c1, section.data_element);
                //b.parentNode.insertBefore(c1,b);
                section.multiday_element = c1;

                var c2 = c1.cloneNode(true);
                c2.className = dhx_multi_day+"_icon";
                c2.style.visibility="hidden";
                this.set_xy(c2, this.xy.scale_width, 0, this.config.section_width, top); // dhx_header has -1 bottom margin

                c1.appendChild(c2);
                section.multiday_icon_element = c2;
                c1.onclick = this._click.dhx_cal_data;
            //  this._els[dhx_multi_day]=[c1,c2];
            //  this._els[dhx_multi_day][0].onclick = this._click.dhx_cal_data;
            }
            this._reset_section(section.element, section);


        // update style of ful section
        this.set_xy(section.element, section.width, section.height, 0, section_top);
        section.element.style.position = "absolute";
        if (sidx > 0) {
            section.element.style.borderTop = "1px solid #CECECE";
        }
        section_top += section.height;

    }
    }

    if (!this._table_view) {
        if (c.multi_day) {
            var dhx_multi_day = 'dhx_multi_day';

            if(this._els[dhx_multi_day]) {
                this._els[dhx_multi_day][0].parentNode.removeChild(this._els[dhx_multi_day][0]);
                this._els[dhx_multi_day] = null;
            }

            var navline = this._els["dhx_cal_navline"][0];
            var top = navline.offsetHeight + this._els["dhx_cal_header"][0].offsetHeight+1;

            var c1 = document.createElement("DIV");
            c1.className = dhx_multi_day;
            c1.style.visibility="hidden";
            this.set_xy(c1, this._colsS[this._colsS.col_length-1]+this.xy.scroll_width+this.config.section_width, 0, 0, top); // 2 extra borders, dhx_header has -1 bottom margin
            b.parentNode.insertBefore(c1,b);

            var c2 = c1.cloneNode(true);
            c2.className = dhx_multi_day+"_icon";
            c2.style.visibility="hidden";
            this.set_xy(c2, this.xy.scale_width, 0, this.config.section_width, top); // dhx_header has -1 bottom margin

            c1.appendChild(c2);
            this._els[dhx_multi_day]=[c1,c2];
            this._els[dhx_multi_day][0].onclick = this._click.dhx_cal_data;
        }
    }
};

var old_locate_holder = scheduler.locate_holder;
scheduler.locate_holder = function(day, section_key) {
    if (!this.is_group_by_mode()) {
        return old_locate_holder.apply(this, [day]);
    }
    var section = scheduler._sections[section_key];
    if (!section) {
        return old_locate_holder.apply(this, [day]);
    }
    var element_idx = this.config.multi_day ? 1 : 0
    return section.data_element.childNodes[day];
};

var old_render_event = scheduler.render_event;
scheduler.render_event = function(ev) {
    if (!this.is_group_by_mode()) {
        return old_render_event.apply(this, arguments);
    }
    var menu = scheduler.xy.menu_width;
    if (ev._sday < 0) return; //can occur in case of recurring event during time shift
    var parent = scheduler.locate_holder(ev._sday, ev['section_key']);
    if (!parent) return; //attempt to render non-visible event
    var sm = ev.start_date.getHours() * 60 + ev.start_date.getMinutes();
    var em = (ev.end_date.getHours() * 60 + ev.end_date.getMinutes()) || (this.config.last_hour * 60);
    var ev_count = ev._count || 1;
    var ev_sorder = ev._sorder || 0;
    var top = (Math.round((sm * 60 * 1000 - this.config.first_hour * 60 * 60 * 1000) * this.config.section_hour_size_px / (60 * 60 * 1000))) % (this.config.section_hour_size_px * 24); //42px/hour
    var height = Math.max(scheduler.xy.min_event_height, (em - sm) * this.config.section_hour_size_px / 60); //42px/hour
    var width = Math.floor((parent.clientWidth - menu) / ev_count);
    var left = ev_sorder * width + 1;
    if (!ev._inner) width = width * (ev_count - ev_sorder);
    if (this.config.cascade_event_display) {
        var limit = this.config.cascade_event_count;
        var margin = this.config.cascade_event_margin;
        left = ev_sorder % limit * margin;
        var right = (ev._inner) ? (ev_count - ev_sorder - 1) % limit * margin / 2 : 0;
        width = Math.floor(parent.clientWidth - menu - left - right);
    }

    var d = this._render_v_bar(ev.id, menu + left, top, width, height, ev._text_style, scheduler.templates.event_header(ev.start_date, ev.end_date, ev), scheduler.templates.event_text(ev.start_date, ev.end_date, ev));

    this._rendered.push(d);
    parent.appendChild(d);

    left = left + parseInt(parent.style.left, 10) + menu;

    if (this._edit_id == ev.id) {

        d.style.zIndex = 1; //fix overlapping issue
        width = Math.max(width - 4, scheduler.xy.editor_width);
        d = document.createElement("DIV");
        d.setAttribute("event_id", ev.id);
        this.set_xy(d, width, height - 20, left, top + 14);
        d.className = "dhx_cal_editor";

        var d2 = document.createElement("DIV");
        this.set_xy(d2, width - 6, height - 26);
        d2.style.cssText += ";margin:2px 2px 2px 2px;overflow:hidden;";

        d.appendChild(d2);
        this._els["dhx_cal_data"][0].appendChild(d);
        this._rendered.push(d);

        d2.innerHTML = "<textarea class='dhx_cal_editor'>" + ev.text + "</textarea>";
        if (this._quirks7) d2.firstChild.style.height = height - 12 + "px"; //IEFIX
        this._editor = d2.firstChild;
        this._editor.onkeydown = function(e) {
            if ((e || event).shiftKey) return true;
            var code = (e || event).keyCode;
            if (code == scheduler.keys.edit_save) scheduler.editStop(true);
            if (code == scheduler.keys.edit_cancel) scheduler.editStop(false);
        };
        this._editor.onselectstart = function (e) {
            return (e || event).cancelBubble = true;
        };
        d2.firstChild.focus();
        //IE and opera can add x-scroll during focusing
        this._els["dhx_cal_data"][0].scrollLeft = 0;
        d2.firstChild.select();

    }
    if (this.xy.menu_width !== 0 && this._select_id == ev.id) {
        if (this.config.cascade_event_display && this._drag_mode)
            d.style.zIndex = 1; //fix overlapping issue for cascade view in case of dnd of selected event
        var icons = this.config["icons_" + ((this._edit_id == ev.id) ? "edit" : "select")];
        var icons_str = "";
        var bg_color = (ev.color ? ("background-color: " + ev.color + ";") : "");
        var color = (ev.textColor ? ("color: " + ev.textColor + ";") : "");
        for (var i = 0; i < icons.length; i++) {
            icons_str += "<div class='dhx_menu_icon " + icons[i] + "' style='" + bg_color + "" + color + "' title='" + this.locale.labels[icons[i]] + "'></div>";
        }
        // xal: #4: fix event menu lightbox top relatively to section
        var ev_section = scheduler._sections[ev['section_key']];
        if (ev_section === undefined) {
            console.log('error ev_section is undefined!');
            ev_section = {'top': 0}; // FIXME: check why we get here!
        }
        var v_bar_absolute_top = ev_section.top + top;
        var obj = this._render_v_bar(ev.id, left - menu + 1, v_bar_absolute_top, menu, icons.length * 20 + 26 - 2, "", "<div style='" + bg_color + "" + color + "' class='dhx_menu_head'></div>", icons_str, true);
        obj.style.left = left - menu + 1;
        this._els["dhx_cal_data"][0].appendChild(obj);
        this._rendered.push(obj);
    }
};

scheduler.mouse_groupby = function(pos) {
    pos.x=Math.min(this._cols.length-1, Math.max(0,Math.ceil(pos.x/this._cols[0])-1));

    // xal: we have to adjust 'y' relatively to section "data" container
    for (var i in scheduler._sections) {
        if (scheduler._sections.hasOwnProperty(i)) {
            var s = scheduler._sections[i];
            if (pos.y >= s.top && pos.y <= s.top+s.height) {
                pos.y -= s.top;
                pos.section = i; // xal: keep pos section for futher usages
                break
            }
        }
    }
    pos.y=Math.max(0,Math.ceil(pos.y*60/(this.config.time_step*this.config.section_hour_size_px))-1)+this.config.first_hour*(60/this.config.time_step);

    return pos;
};

var old_mouse_coords = scheduler._mouse_coords;
scheduler._mouse_coords= function(ev) {
    if (!this.is_group_by_mode()) {
        return old_mouse_coords.apply(this, arguments);
    }
    var pos;
    var b=document.body;
    var d = document.documentElement;
    if(ev.pageX || ev.pageY)
        pos={x:ev.pageX, y:ev.pageY};
    else pos={
        x:ev.clientX + (b.scrollLeft||d.scrollLeft||0) - b.clientLeft,
        y:ev.clientY + (b.scrollTop||d.scrollTop||0) - b.clientTop
    };

    //apply layout
    pos.x-=getAbsoluteLeft(this._obj)+(this._table_view?0:this.xy.scale_width+this.config.section_width);
    pos.y-=getAbsoluteTop(this._obj)+this.xy.nav_height+(this._dy_shift||0)+this.xy.scale_height-this._els["dhx_cal_data"][0].scrollTop;
    pos.ev = ev;

    var handler = this["mouse_"+this._mode];
    if (handler)
        return handler.call(this,pos);

    //transform to date
    if (!this._table_view) {
        pos.x=Math.min(this._cols.length-1, Math.max(0,Math.ceil(pos.x/this._cols[0])-1));
        pos.y=Math.max(0,Math.ceil(pos.y*60/(this.config.time_step*this.config.section_hour_size_px))-1)+this.config.first_hour*(60/this.config.time_step);
    } else {
        if (!this._cols || !this._colsS) // agenda/map views
            return pos;
        var dy=0;
        for (dy=1; dy < this._colsS.heights.length; dy++)
            if (this._colsS.heights[dy]>pos.y) break;

        pos.y=Math.ceil( (Math.max(0, pos.x/this._cols[0])+Math.max(0,dy-1)*7)*24*60/this.config.time_step );

        if (scheduler._drag_mode || this._mode == "month")
            pos.y=(Math.max(0,Math.ceil(pos.x/this._cols[0])-1)+Math.max(0,dy-1)*7)*24*60/this.config.time_step;

        pos.x=0;
    }

    return pos;
};

// Handle specific limit per groupby "section"
scheduler.attachEvent("onScaleAdd", function(area, day, section) {
    if (scheduler._table_view && scheduler._mode != "month")
        return;

    if (this.is_group_by_mode()) { // we are in the group by mode and need to draw it's sections as well

        var day_index = day.getDay();
        var day_value = day.valueOf();
        var mode = this._mode;
        var timespans = scheduler._marked_timespans;
        var r_configs = [];

        if (timespans['groupby'] && timespans['groupby'][section.key]) {
            var unit_zones = timespans['groupby'][section.key];
            var unit_types = scheduler._get_types_to_render(unit_zones[day_index], unit_zones[day_value]);
            r_configs.push.apply(r_configs, scheduler._get_configs_to_render(unit_types));
        }

        for (var i=0; i<r_configs.length; i++) {
            scheduler._render_marked_timespan(r_configs[i], area, day);
        }

    }

});

var old_scheduler_render_marked_timespan = scheduler._render_marked_timespan;

scheduler._render_marked_timespan = function(options, area, day) {
    if (this.is_group_by_mode()) {
        var old_hour_size = scheduler.config.hour_size_px;
        scheduler.config.hour_size_px = scheduler.config.section_hour_size_px;
    }
    var rval = old_scheduler_render_marked_timespan.apply(this, arguments);
    if (this.is_group_by_mode()) {
        scheduler.config.hour_size_px = old_hour_size;
    }
    return rval;
};


// end-of-scheduler monkey-patch
}

