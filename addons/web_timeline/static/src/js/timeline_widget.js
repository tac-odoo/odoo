
(function () {

	var _t = openerp.web._t,
		_lt = openerp.web._lt;		
	var QWeb = openerp.web.qweb;

	openerp.web_timeline.Timeline = openerp.web.Widget.extend({
//		template: 'TimelineWidget',

		init: function(parent, model, domain, options) {
			this._super(parent, model, domain, options);
			
			console.log("Timeline : Init Widget");
		},

		start: function(){
			var self = this;

			console.log("Timeline : Start Widget");

			this.$el.append("<h1> Hello dear Odoo user! </h1>");
			this.$el.append("<p> This is the new Timeline View. </p>");
		},
	});

})();
