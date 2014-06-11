$(document).ready(function(){
    var employeework = new openerp.website.employeework();
});
openerp.website.employeework = openerp.Class.extend({
    init : function(){
        this.$el_weekview_txt = $(".weekview_txt");
        this.$el_save_button = $("a#save");
        this.$el_last_time = $("span#result");
        this.$el_timer = $('button.timer');
        this.start();
        this.start_interval();
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
                    hour = parseInt(hour) + 1;
                    minute = 0;
                }
                el_hour.text(hour);
                el_minute.text(minute);
            });
        }, 60000);
    },
    timer_action : function(){
        var self = this;
        this.$el_timer.click(function(){
            var id = this.id;
            var $el_cog = $(this).find('.fa-cog');
            var $el_clock = $(this).find('.fa-clock-o');
            var element = $(this).find('.text-success');
            if(!element.length) {
                $el_cog.removeClass("hidden");
                $el_clock.addClass('text-success');
                $(this).find("strong#" + id).append("<span class='hour'>0</span>H <span class='minute'>0</span>M");
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