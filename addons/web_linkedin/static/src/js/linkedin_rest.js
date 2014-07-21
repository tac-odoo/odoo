/*---------------------------------------------------------
 * OpenERP web_linkedin (module)
 *---------------------------------------------------------*/

openerp.web_linkedin = function(instance) {
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;
    
    /*
    * instance.web_linkedin.tester.test_authentication()
    * Call check if the Linkedin session is open or open a connection popup
    * return a deferrer :
    *   - resolve if the authentication is true
    *   - reject if the authentication is wrong or when the user logout
    */
    instance.web_linkedin.LinkedinTester = instance.web.Class.extend({
        init: function() {
            this.linkedin_def = $.Deferred();
            this.auth_def = $.Deferred();
        },
        test_linkedin: function() {
            var self = this;
            return this.test_api_key();
        },
        test_api_key: function() {
            var self = this;
            if (this.api_key) {
                return $.when();
            }
            return new instance.web.Model("ir.config_parameter").call("get_param", ["web.linkedin.apikey"]).then(function(a) {
                if (!!a) {
                    self.api_key = a;
                    return true;
                } else {
                    var dialog = new instance.web.Dialog(self, {
                        title: _t("LinkedIn is not enabled"),
                        buttons: [
                            {text: _t("Ok"), click: function() { self.parents('.modal').modal('hide'); }}
                        ],
                    }, QWeb.render('LinkedIn.DisabledWarning')).open();
                    return $.Deferred().reject();
                }
            });
        },
    });
    
    instance.web_linkedin.tester = new instance.web_linkedin.LinkedinTester();
    
    instance.web_linkedin.Linkedin = instance.web.form.FieldChar.extend({
        init: function() {
            this._super.apply(this, arguments);
            this.display_dm = new instance.web.DropMisordered(true);
        },
        initialize_content: function() {
            var $ht = $(QWeb.render("FieldChar.linkedin"));
            var $in = this.$("input");
            $in.replaceWith($ht);
            this.$(".oe_linkedin_input").append($in);
            this.$(".oe_linkedin_img").click(_.bind(this.search_linkedin, this));
            this._super();
        },
        search_linkedin: function() {
            var self = this;
            if (!this.open_in_process) {
                this.open_in_process = true;
                this.display_dm.add(instance.web_linkedin.tester.test_linkedin()).done(function() {
                    self.open_in_process = false;
                    var text = (self.get("value") || "").replace(/^\s+|\s+$/g, "").replace(/\s+/g, " ");
                    //instance.web_linkedin.tester.test_authentication().done(function() {
                    //self.rpc("/linkedin/").done(function(result) {
                        var pop = new instance.web_linkedin.LinkedinSearchPopup(self, text);
                        pop.on("search_completed", this, function() {
                            pop.open();
                        });
                        pop.on("selected", this, function(entity) {
                            self.selected_entity(entity);
                        });
                        pop.do_search();
                    //});
                });
            }
        },
        selected_entity: function(entity) {
            var self = this;
            //TODO
        },
        create_on_change: function(entity) {
            //TODO
        },
        create_or_modify_company: function (entity) {
            var self = this;
            //TODO
        },
        create_or_modify_partner: function (entity, rpc_search_similar_partner) {
            var self = this;
            //TODO
        },
        create_or_modify_partner_change: function (entity) {
            //TODO
        },
        create_or_modify_company_partner: function (entities) {
            //TODO
        }
    });
    instance.web.form.widgets.add('linkedin', 'instance.web_linkedin.Linkedin');
    
    instance.web_linkedin.Linkedin_url = instance.web.form.FieldChar.extend({
        initialize_content: function() {
            this.$("input,span").replaceWith($(QWeb.render("FieldChar.linkedin_url")));
            this._super();
        },
        render_value: function() {
            this._super();
            this.$(".oe_linkedin_url").attr("href", this.field_manager.datarecord.linkedin_url || "#").toggle(!!this.field_manager.datarecord.linkedin_url);
        },
    });
    instance.web.form.widgets.add('linkedin_url', 'instance.web_linkedin.Linkedin_url');
    

    instance.web_linkedin.LinkedinSearchPopup = instance.web.Dialog.extend({
        template: "Linkedin.popup",
        init: function(parent, search) {
            var self = this;
            //if (!IN.User.isAuthorized()) {
            //    this.$buttons = $("<div/>");
            //    this.destroy();
            //}
            this._super(parent, { 'title': QWeb.render('LinkedIn.AdvancedSearch', {'title': _t("LinkedIn search")}) });
            this.search = search;
            this.limit = 5;
        },
        start: function() {
            this._super();
            this.bind_event();
            //this.display_account();
            //this.do_search();
        },
        bind_event: function() {
            var self = this;
            this.$el.parents('.modal').on("click", ".oe_linkedin_logout", function () {
                IN.User.logout();
                self.destroy();
            });
            this.$search = this.$el.parents('.modal').find(".oe_linkedin_advanced_search" );
            this.$url = this.$search.find("input[name='search']" );
            this.$button = this.$search.find("button");

            this.$button.on("click", function (e) {
                e.stopPropagation();
                self.do_search(self.$url.val() || '');
            });
            this.$url
                .on("click mousedown mouseup", function (e) {
                    e.stopPropagation();
                }).on("keydown", function (e) {
                    if(e.keyCode == 13) {
                        $(e.target).blur();
                        self.$button.click();
                    }
                });
        },
        display_account: function() {
            var self = this;
            IN.API.Profile("me")
                .fields(["firstName", "lastName"])
                .result(function (result) {
                    $(QWeb.render('LinkedIn.loginInformation', result.values[0])).appendTo(self.$el.parents('.modal').find(".oe_dialog_custom_buttons"));   
            })
        },
        do_search: function(url) {
            var self = this;
            var deferrers = [];
            var params = {};
            this.$(".oe_linkedin_pop_c, .oe_linkedin_pop_p").empty();

            if (url && url.length) {
                var url = url.replace(/\/+$/, '');
                var uid = url.replace(/(.*linkedin\.com\/[a-z]+\/)|(^.*\/company\/)|(\&.*$)/gi, '');
                _.extend(params, {'search_uid': uid});
                console.log("params are :: ",params);

                this.search = url;
            }
            console.log("search term is ::: ",this.search);
            var context = instance.web.pyeval.eval('context');
            self.rpc("/linkedin/get_popup_data", _.extend({'search_term': this.search, 'from_url': window.location.href, 'local_context': context}, params)).done(function(result) {
                if(result.status && result.status == 'need_auth' && confirm(_t("You will be redirected to LinkedIn authentication page, once authenticated after that you use this widget."))) {
                    instance.web.redirect(result.url);
                } else { //We can check else if (result.status == 'authorized') and other status
                    self.trigger('search_completed');
                    self.do_result_companies(result.companies);
                    self.do_result_people(result.people);
                }
            });
            return $.when.apply($, deferrers);
        },
        do_result_companies: function(companies) {
            var lst = (companies.companies || {}).values || [];
            console.log("companies is :::",lst);
            //lst = _.first(companies, this.limit);
            lst = _.map(lst, function(el) {
                el.__type = "company";
                return el;
            });
            console.debug("Linkedin companies found:", (companies.companies || {})._total, '=>', lst.length, lst);
            return this.display_result(lst, this.$(".oe_linkedin_pop_c"));
        },
        do_result_people: function(people) {
            var plst = (people.people || {}).values || [];
            plst = _.first(plst, this.limit);
            plst = _.map(plst, function(el) {
                el.__type = "people";
                return el;
            });
            console.debug("Linkedin people found:", people.numResults, '=>', plst.length, plst);
            return this.display_result(plst, this.$(".oe_linkedin_pop_p"));
        },
        display_result: function(result, $elem) {
            var self = this;
            var $row;
            $elem.find(".oe_no_result").remove();
            _.each(result, function(el) {
                var pc = new instance.web_linkedin.EntityWidget(self, el);
                if (!$elem.find("div").size() || $elem.find(" > div:last > div").size() >= 5) {
                    $row = $("<div style='display: table-row;width:100%'/>");
                    $row.appendTo($elem);
                }
                pc.appendTo($row);
                pc.$el.css("display", "table-cell");
                pc.$el.css("width", "20%");
                pc.on("selected", self, function(data) {
                    self.trigger("selected", data);
                    self.destroy();
                });
            });
            if (!$elem.find("div").size()) {
                $elem.append($('<div class="oe_no_result">').text(_t("No results found")));
            }
        },
        
    });
    
    instance.web_linkedin.EntityWidget = instance.web.Widget.extend({
        template: "Linkedin.EntityWidget",
        init: function(parent, data) {
            this._super(parent);
            this.data = data;
        },
        start: function() {
            var self = this;
            this.$el.click(function() {
                self.trigger("selected", self.data);
            });
            if (this.data.__type === "company") {
                this.$("h3").text(this.data.name);
                self.$("img").attr("src", this.data.logoUrl);
                self.$(".oe_linkedin_entity_headline").text(this.data.industry);
            } else { // people
                this.$("h3").text(this.data.formattedName);
                self.$("img").attr("src", this.data.pictureUrl);
                self.$(".oe_linkedin_entity_headline").text(this.data.headline);
            }
        },
    });
};
// vim:et fdc=0 fdl=0:
