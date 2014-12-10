openerp.web_timeline = function(instance) {
    var _t = instance.web._t,
        _lt = instance.web._lt;
	var QWeb = instance.web.qweb;

	console.log("javascript bonjour !")

    instance.web_timeline = {};

	instance.web_timeline.MailsList = instance.web.Widget.extend({
		template: "MailsList"
		start: function() {
			var self = this;
			new instance.web.Model("mail.message").query(["date", "subject", "author_id", "body"]).then(function(result){
				_.each(result, function(item){
					var $item = $(QWeb.render("Mail", {item: item}));
					self.$el.append($item);
					$item.click(function(){
						self.item_clicked(item);						
					});
				});
			});
		},

		item_clicked: function(item) {
			this.do_action({
				type: "ir_actions.act_windows",
				res_model: "mail.message",
				res_id : item.body,
				views:[[false, 'tree']],
				target: "current",
				context: {},
			});
		},
	});

	// instance.web.client_actions.add('timeline.testpage', 'instance.web_timeline.MailsList');
}
