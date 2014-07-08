(function(){
var instance = openerp;

instance.web.Planner = instance.web.WebClient.include({
    show_application: function() {
        var self = this;
        this._super.apply(this, arguments);
        root_menu = [];
        this.menu.$el.find(".oe_menu_toggler").each(function(el){
            root_menu.push($(this).data('menu'));
        });
        var planner_manager = new instance.web.PlannerManager(); 
        planner_manager.prependTo(window.$('.oe_systray'));
         // Hack, I can't convince my self to use .include for menu too ;)
        var open_menu = self.menu.open_menu;
        self.menu.open_menu = function(){
            open_menu.apply(this, arguments);
            var that = this;
            self.fetch_application_planner().then(function(application){
                var id = that.$el.find('.active').children().data("menu");
                if(_.intersection(application, root_menu, [id]).length){
                    planner_manager.active_id = id;
                    planner_manager.show();
                }else{
                    planner_manager.hide();
                }
            });
        };
    },

    // fetch application planner data only once
    fetch_application_planner: function(){
        self = this;
        var def = $.Deferred();
        var planner_application = [];
        if (this.planner_application){
            def.resolve(self.planner_application);
        }else{
            self.planner_application = [];
            (new instance.web.Model('ir.aplication.planner')).query().all().then(function(res) {
                _(res).each(function(menu){
                    self.planner_application.push(menu.application_id[0]);
                });
                def.resolve(self.planner_application);
            }).fail(function() {def.reject();});
        }
        return def;
    },
   
});


instance.web.PlannerManager = instance.web.Widget.extend({
    template: "PlannerManager",
    events: {
        'click .progress': 'toggle_dialog'
    },

    init: function(){
        this.dialog = new instance.web.PlannerDialog();
        this.dialog.appendTo(document.body);
        this.applications = [];
        this.active_id;
    },

    show: function(){
       this.$el.show();
    },

    hide: function(){
       this.$el.hide();
    },
    
    toggle_dialog: function(){
       this.dialog.$('#PlannerModal').modal('toggle');
    },
});
instance.web.PlannerDialog = instance.web.Widget.extend({
    template:'PlannerDialog',
    show: function(){
       this.$el.modal('show');
    },

    hide: function(){
       this.$el.modal('hide');
    },
});

})();
