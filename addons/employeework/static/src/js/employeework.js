$(document).ready(function(){
    var employeework = new openerp.website.employeework();
});

openerp.website.employeework = openerp.Class.extend({
    init : function(){
        this.$el_weekview_txt = $(".weekview_txt");
        this.$el_save_button = $("a#save");
        this.$el_last_time = $("span#result");
        this.$el_timer = $('button.timer');
        this.project_list = '';
        this.start();
        this.start_interval();
        this.add_line();
        this.timer_action();
        this.stop_invalid_input(this.$el_weekview_txt);
        this.active_save_button(this.$el_weekview_txt);
    },
    start : function(){
        var self = this;
        this.$el_save_button.hide();
        this.$el_last_time.hide();
        this.$el_save_button.click(function(){
            self.edit_weekview_data();
        });
    },
    // Update timer on 1 minute
    start_interval : function(){
        var self = this;
        setInterval(function(){
            self.$el_timer.find("i.text-success").each(function(){
                var el_hour = self.$el_timer.find("strong#" + this.id +" span.hour");
                var el_minute = self.$el_timer.find("strong#" + this.id +" span.minute");
                var hour = el_hour.text();
                var minute = el_minute.text();
                minute = parseInt(minute) + 1;
                if(minute > 60) {
                    el_hour.text(parseInt(hour) + 1);
                    minute = 0;
                }
                el_minute.text(minute);
            });
        }, 60000);
    },
    // Get project list
    get_project_list : function(){
        var self = this;
        openerp.jsonRpc("/employeework/project_list", 'call', {}).done(function(result) {
            $.each(result, function(key,value){
                 self.project_list += "<option id=" + key + ">" + value + "</option>"
            });
        });
    },
    // Add Line in dateview
    add_line : function(){
        var self = this;
        self.get_project_list();
        this.$el_addline_button = $("button.addline");
        this.$el_addline_button.click(function(){
            $(this).hide();
            if($("tr").hasClass('new_record'))
                return false;
            $("table.dateview tr:last").before("<tr class='new_record'>\
                <td>\
                    <select class='form-control project_list' data-style='btn-danger'>\
                    " + self.project_list + "\
                    </select>\
                </td>\
                <td class='new_record'><input class='form-control input-normal new_desc' type='text' placeholder='Description'/></td>\
                <td class='new_record'><input class='form-control new_hour' type='text' placeholder='Hour'/></td>\
                <td>\
                    <button type='button' class='btn btn-primary btn-gt save mt4'>\
                        <span class='fa fa-save'></span> Save\
                    </button>\
                    <button type='button' class='btn btn-primary btn-gt cancel mt4'>\
                        <span class='fa fa-trash-o'></span> Cancel\
                    </button>\
                </td>\
            </tr>");
            self.stop_invalid_input($('.new_hour'));
            $("button.cancel").click(function(){
                $("tr.new_record").remove();
                $(self.$el_addline_button).show();
            });
            $("button.save").click(function(){
                var desc = $(".new_desc").val().trim();
                var hour = $(".new_hour").val().trim();
                $("td.new_record").removeClass('has-error');
                if(desc == '') {
                    $(".new_desc").parent("td").addClass("has-error");
                    return false;
                }
                if(hour == '') {
                    $(".new_hour").parent("td").addClass("has-error");
                    return false;
                }
                openerp.jsonRpc("/employeework/addline", 'call', {'description' : desc + ' ', 'date' : $("input#hidden").val(), 'hour' : hour, 'project_id' : $(".project_list :selected").attr("id")}).done(function(result) {
                    if(!JSON.stringify(result)){
                        alert("Record not create");
                    } else {
                        window.location.reload();
                    }
                });
            });
        });
    },
    // Start and Stop timer
    timer_action : function(){
        this.$el_timer.click(function(){
            var id = this.id;
            var $el_cog = $(this).find('.fa-cog');
            var $el_clock = $(this).find('.fa-clock-o');
            var element = $(this).find('.text-success');
            if(!element.length) {
                $el_cog.removeClass("hidden");
                $el_clock.addClass('text-success');
                $(this).find("strong#" + id).html("<span class='hour'>0</span>H <span class='minute'>0</span>M");
                $.ajax({url:"/employeework/addcounter",data:'record_id=' + id,success:function(result){
                   
                }
                });
            } else {
                $el_cog.addClass("hidden");
                $el_clock.removeClass('text-success');
                $.ajax({url:"/employeework/removecounter",data:'record_id=' + id,success:function(result){
                    var result = parseFloat(result);
                    var total = $("strong#" + id).text();
                    var finaltotal = $("h4#dateview_total").text();
                    $("strong#" + id).text(parseFloat(total) + result);
                    $("h4#dateview_total").text(parseFloat(finaltotal) + result);
                }
                });
            }
        });
    },
    // Prevent to enter invalid input of textbox in weekview
    stop_invalid_input : function($el){
        $el.keypress(function(event) {
            if(event.which == 8 || event.which == 0)
                return true;
            if(event.which < 46 || event.which > 59 || event.which == 47 || event.which == 58 || event.which == 59)
                return false;
            if(event.which == 46 && this.value.indexOf('.') != -1)
                return false;
        });
    },
    // Add or Edit value of textbox in weekview
    edit_weekview_data : function(){
        var self = this;
        this.$el_find_dirty = $('table tbody').find(".dirty");
        this.$el_find_dirty.each(function(){
            hour = this.value.trim();
            if(hour != '') {
                $.ajax({url:"/employeework/editdata",data:'hour=' + hour + '&project_id=' + this.id +'&date=' + this.getAttribute('date'),success:function(result){
                    self.$el_last_time.show().text("Last saved at " + result);
                }
                });
            }
            $(this).css('color','#555555');
        });
        self.$el_find_dirty.removeClass("dirty");
        self.$el_save_button.hide(500);
    },
    // Active save button on textbox value change in weekview
    active_save_button : function($el){
        var self = this;
        $el.change(function(){
            if(this.value.trim() != '') {
                self.$el_save_button.show();
                $(this).addClass('dirty');
                $(this).css('color','#A4498C');
            } else {
                $(this).removeClass('dirty');
                $(this).css('color','#555555');
            }
        });
    },
});