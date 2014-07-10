(function(){
var instance = openerp;
var QWeb = instance.web.qweb;

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
                if(_.intersection(_.values(application), root_menu, [id]).length){
                    planner_manager.active_id =_.invert(application)[id];
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
        if (this.planner_bymenu){
            def.resolve(self.planner_bymenu);
        }else{
            self.planner_bymenu = {};// {'apps_id': 'menu_id'}
            (new instance.web.Model('ir.aplication.planner')).query().all().then(function(res) {
                _(res).each(function(apps){
                    self.planner_bymenu[apps.id] = apps.application_id[0];
                });
                def.resolve(self.planner_bymenu);
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
        this.dialog.planner_manger = this;
        this.dialog.appendTo(document.body);
        this.applications = {}; //{ 'apps_id': 'data'}
    },

    show: function(){
        this.$el.show();
    },

    hide: function(){
        this.$el.hide();
    },

    load_apps:function(){
        var self = this;
        var def = $.Deferred();
        var id = parseInt(this.active_id, 10);
        // if application already fetch
        if(!!this.applications[id]) {
            def.resolve(this.applications[id]);
        }else{
            // fetch all fields except description
            var fields = ['category_id', 'planner_id', 'name', 'description', 'sequence', 'template_id', 'completed'];
            (new instance.web.Model('ir.application.planner.page')).query(fields)
                        .filter([["planner_id", "=", id]]).order_by(['sequence']).all().then(function(res) {
                            self.applications[id] = res;
                            def.resolve(res);
                        });
        }
        return def;
    },

    toggle_dialog: function(){
        this.dialog.$('#PlannerModal').modal('toggle');
    },
});
instance.web.PlannerDialog = instance.web.Widget.extend({
    template:'PlannerDialog',
    events: {
        'show.bs.modal': 'show',
        'click .menu-item': 'load_page',
        'click button.done' : 'complete_page'
    },

    render_menubar: function(data){
        this.$('.menubar').html(QWeb.render("PlannerMenu", {'menu':data}));
    },

    load_page: function(ev){
        var self = this;
        var template_id = $(ev.target).data('template');
        this.get_page_template(template_id).then(function(res){
            self.$('.content').html(res);
        });

    },
    get_page_template: function(template_id){
        return (new instance.web.DataSet(this, 'ir.ui.view')).call('render', [template_id]);
    },

    complete_page: function(){
        console.log('eeee');
    },

    show: function(){
        self = this;
        this.planner_manger.load_apps().then(function(data){
            var group = _.groupBy(data, function(obj){ return obj['category_id'][1]});
            self.render_menubar(group);
        });
    },


    });

})();
