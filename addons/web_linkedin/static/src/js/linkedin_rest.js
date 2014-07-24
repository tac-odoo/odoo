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
                        pop.on("search_completed", self, function() {
                            pop.open();
                        });
                        pop.on("selected", self, function(entity) {
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
            console.log("this is ::: ",this)
            this.create_on_change(entity).done(function(to_change) {
                console.log("to_change is ::: ",to_change);
                var values = self.view.get_fields_values();
                _.each(to_change, function (value, key) {
                    if (!/linkedin/.test(key) && !!values[key]) {
                        if(!_.isArray(values[key])) {
                            delete to_change[key];
                        }
                    }
                })
                self.view.set_values(to_change);
            });
        },
        create_on_change: function(entity) {
            return entity.__type === "company" ? this.create_or_modify_company(entity) : this.create_or_modify_partner(entity);
        },
        create_or_modify_company: function (entity) {
            console.log("Inside modify company ::: ");
            var self = this;
            var to_change = {};
            var image_def = null;
            to_change.is_company = true;
            to_change.name = entity.name;
            to_change.image = false;
            if (entity.logoUrl) {
                image_def = self.rpc('/web_linkedin/binary/url2binary',
                                   {'url': entity.logoUrl}).then(function(data){
                    to_change.image = data;
                });
            }
            to_change.website = entity.websiteUrl;
            to_change.phone = false;
            _.each((entity.locations || {}).values || [], function(el) {
                to_change.phone = el.contactInfo.phone1;
            });
            to_change.linkedin_url = _.str.sprintf("http://www.linkedin.com/company/%d", entity.id);

            console.log("to_change is before overritting value :::: ",to_change)
            _.each(to_change, function (val, key) {
                if (self.field_manager.datarecord[key]) {
                    to_change[key] = self.field_manager.datarecord[key];
                }
            });

            to_change.child_ids = [];
            var children_def = $.Deferred();
            //TODO: People-search and get partner related data
            var context = instance.web.pyeval.eval('context');
            res = new instance.web.Model("linkedin").call("get_people_from_company", [entity.universalName, true, 50, window.location.href, context]).done(function(result) {
                console.log("result is ::: ",result);
                children_def.resolve();
            });

            //TODO: add children_def, if both deferred objects are resolved then call callback function
            return $.when(image_def, children_def).then(function () {
                return to_change;
            });
        },
        create_or_modify_partner: function (entity, rpc_search_similar_partner) {
            console.log("Inside modify partner ::: ");
            var self = this;
            //TODO
            return $.Deferred().resolve();
        },
        create_or_modify_partner_change: function (entity) {
            //TODO
            return $.Deferred().resolve();
        },
        create_or_modify_company_partner: function (entities) {
            //TODO
            return $.Deferred().resolve();
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

                this.search = url;
            }
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
            //plst = _.first(plst, this.limit);
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

    /*
    Kanban include for adding import button on button bar for res.partner model to import linkedin contacts
    */
    openerp.web_kanban.KanbanView.include({
        load_kanban: function() {
            var self = this;
            var super_res = this._super.apply(this, arguments);
            //TODO: test linkedin here first, if there is no apikey or secret_key set then do not add button
            if(this.dataset.model == 'res.partner') {
                $linkedin_button = $(QWeb.render("KanbanView.linkedinButton", {'widget': this}));
                $linkedin_button.appendTo(this.$buttons);
                $linkedin_button.click(function() {
                    var context = instance.web.pyeval.eval('context');
                    res = new instance.web.Model("linkedin").call("sync_linkedin_contacts", [window.location.href, context]).done(function(result) {
                        if(result.status && result.status == 'need_auth' && confirm(_t("You will be redirected to LinkedIn authentication page, once authenticated after that you use this widget."))) {
                            instance.web.redirect(result.url);
                        } else {
                            console.log("result is ::: ",result);
                            self.do_action(result);
                        }
                        //Reload the kanban once records are synchronized
                    });
                })
            }
            return super_res;
        }
    });
};
// vim:et fdc=0 fdl=0:
