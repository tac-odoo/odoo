openerp.event = function (instance) {
    var _t = instance.web._t;
    var _lt = instance.web._lt;

    instance.web_kanban.EventGraph = instance.web_kanban.AbstractField.extend({
        start: function() {
            this.display_graph(this.field.raw_value);
        },
        display_graph : function(data) {
            var self = this;
            nv.addGraph(function () {
                self.$el.append('<svg>');
                var chart = nv.models.pieChart()
                    .x(function(d) { return d.label; })
                    .y(function(d) { return d.value; })
                    .showLabels(false)
                    .showLegend(false)
                    .width(170)
                    .height(170);
                self.svg = self.$el.find('svg')[0];
                d3.select(self.svg)
                    .datum(data)
                    .transition().duration(350)
                    .call(chart);
            });
        },
    });
    instance.web_kanban.fields_registry.add("event_graph", "instance.web_kanban.EventGraph");
};
