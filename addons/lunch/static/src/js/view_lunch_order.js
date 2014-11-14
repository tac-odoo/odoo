openerp.lunch  = function(instance) {

    instance.lunch.lunchwidget = instance.web.form.FormWidget.extend(instance.web.form.ReinitializeWidgetMixin,{
        template : 'lunchwidget',
        init: function(parent, context) {
            self = parent;
            this._super.apply(this, arguments);
            this.uid = self.dataset.context.uid;
            this.set("value", "");
            this.pref_ids = null;
            this.categories = null;
            this.render_value();
        },

        render_value: function() {
            var self = this;
            new instance.web.Model("lunch.order").call("get_lunch_order")
            .then(function(data) {
                self.pref_ids = data['pref_ids'];
                self.categories = data;
                console.log("self",self.categories);
            });
        },

    });

    instance.web.form.custom_widgets.add('lunch_widget', 'instance.lunch.lunchwidget');
};