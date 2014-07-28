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
            this.is_set_keys = false;
        },
        test_linkedin: function(show_dialog) {
            var self = this;
            if (this.is_set_keys) {
                return $.when();
            }
            return new instance.web.Model("linkedin").call("test_linkedin_keys", []).then(function(a) {
                if (!!a) {
                    self.is_set_keys = a;
                    return true;
                } else {
                    if (show_dialog) {
                        var dialog = new instance.web.Dialog(self, {
                            title: _t("LinkedIn is not enabled"),
                            buttons: [
                                {text: _t("Ok"), click: function() { self.parents('.modal').modal('hide'); }}
                            ],
                        }, QWeb.render('LinkedIn.DisabledWarning')).open();
                    }
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
                this.display_dm.add(instance.web_linkedin.tester.test_linkedin(true)).done(function() {
                    self.open_in_process = false;
                    var text = (self.get("value") || "").replace(/^\s+|\s+$/g, "").replace(/\s+/g, " ");
                    var pop = new instance.web_linkedin.LinkedinSearchPopup(self, text);
                    pop.on("search_completed", self, function() {
                        pop.open();
                    });
                    pop.on("selected", self, function(entity) {
                        self.selected_entity(entity);
                    });
                    pop.do_search();
                });
            }
        },
        selected_entity: function(entity) {
            var self = this;
            this.create_on_change(entity).done(function(to_change) {
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

            _.each(to_change, function (val, key) {
                if (self.field_manager.datarecord[key]) {
                    to_change[key] = self.field_manager.datarecord[key];
                }
            });

            to_change.child_ids = [];
            var children_def = $.Deferred();
            var context = instance.web.pyeval.eval('context');
            //Here limit will be 25 because count range can between 0 to 25
            //https://developer.linkedin.com/documents/people-search-api
            res = new instance.web.Model("linkedin").call("get_people_from_company", [entity.universalName, 25, window.location.href, context]).done(function(result) {
                var result = _.reject(result.people.values || [], function(el) {
                        return ! el.formattedName;
                });
                self.create_or_modify_company_partner(result).then(function (childs_to_change) {
                    _.each(childs_to_change, function (data) {
                        // [0,0,data] if it's a new partner
                        to_change.child_ids.push( data.id ? [1, data.id, data] : [0, 0, data] );
                    });
                    children_def.resolve();
                });
            }).fail(function () {
                    children_def.reject();
            });

            return $.when(image_def, children_def).then(function () {
                return to_change;
            });
        },
        create_or_modify_company_partner: function (entities) {
            var self = this;
            var deferrer = $.Deferred();
            var defs = [];
            var childs_to_change = [];

            _.each(entities, function (entity, key) {
                var entity = _.extend(entity, {
                    '__type': "people",
                    '__company': entity.universalName,
                    'parent_id': self.field_manager.datarecord.id || 0
                });
                defs.push(self.create_or_modify_partner_change(entity).then(function (to_change) {
                    childs_to_change[key] = to_change;
                }));
            });
            $.when.apply($, defs).then(function () {
                new instance.web.DataSetSearch(this, 'res.partner').call("linkedin_check_similar_partner", [entities]).then(function (partners) {
                    _.each(partners, function (partner, i) {
                        _.each(partner, function (val, key) {
                            if (val) {
                                childs_to_change[i][key] = val;
                            }
                        });
                    });
                    deferrer.resolve(childs_to_change);
                });
            });
            return deferrer;
        },
        create_or_modify_partner: function (entity, rpc_search_similar_partner) {
            var self = this;
            return this.create_or_modify_partner_change(entity).then(function (to_change) {
                // find similar partners
                _.each(to_change, function (val, key) {
                    if (self.field_manager.datarecord[key]) {
                        to_change[key] = self.field_manager.datarecord[key];
                    }
                });
                return to_change;
            });
        },
        create_or_modify_partner_change: function (entity) {
            var to_change = {};
            var defs = [];
            to_change.is_company = false;
            to_change.name = entity.formattedName;
            if (entity.pictureUrl) {
                defs.push(this.rpc('/web_linkedin/binary/url2binary',
                                   {'url': entity.pictureUrl}).then(function(data){
                    to_change.image = data;
                }));
            }
            _.each((entity.phoneNumbers || {}).values || [], function(el) {
                if (el.phoneType === "mobile") {
                    to_change.mobile = el.phoneNumber;
                } else {
                    to_change.phone = el.phoneNumber;
                }
            });
            var positions = (entity.positions || {}).values || [];
            for (key in positions) {
                var position = positions[key];
                if (position.isCurrent) {
                    var company_name = position.company ? position.company.name : false;
                    if (!entity.parent_id && entity.parent_id !== 0 && company_name) {
                        defs.push(new instance.web.DataSetSearch(this, 'res.partner').call("search", [[["name", "=", company_name]]]).then(function (data) {
                            if(data[0]) to_change.parent_id = data[0];
                            else position.title = position.title + ' (' + company_name + ') ';
                            to_change.function = position.title;
                        }));
                    } else if (!entity.__company || !company_name || company_name == entity.__company) {
                        to_change.function = position.title + (company_name ? ' (' + company_name + ') ':'');
                    }
                    break;
                }
            };

            if (entity.parent_id) {
                to_change.parent_id = entity.parent_id;
            }
            to_change.linkedin_url = to_change.linkedin_public_url = entity.publicProfileUrl || false;
            to_change.linkedin_id = entity.id || false;

            return $.when.apply($, defs).then(function () {
                return to_change;
            });
        },
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
            var self = this;
            this._super();
            this.bind_event();
            this.has_been_loaded = $.Deferred()
            $.when(this.has_been_loaded).done(function(profile) {
                self.display_account(profile);
            });
        },
        bind_event: function() {
            var self = this;
            this.$el.parents('.modal').on("click", ".oe_linkedin_logout", function () {
                self.rpc("/linkedin/linkedin_logout", {}).done(function(result) {
                    if (result) {
                        self.destroy();
                    }
                });
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
        display_account: function(profile) {
            var self = this;
            $(QWeb.render('LinkedIn.loginInformation', profile)).appendTo(self.$el.parents('.modal').find(".oe_dialog_custom_buttons"));
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
            self.rpc("/linkedin/get_search_popup_data", _.extend({'search_term': this.search, 'from_url': window.location.href, 'local_context': context}, params)).done(function(result) {
                if(result.status && result.status == 'need_auth' && confirm(_t("You will be redirected to LinkedIn authentication page, once authenticated after that you use this widget."))) {
                    instance.web.redirect(result.url);
                } else { //We can check (result.status == 'OK') and other status
                    self.trigger('search_completed');
                    self.has_been_loaded.resolve(result.current_profile)
                    self.do_result_companies(result.companies);
                    self.do_result_people(result.people);
                    if (result.warnings) { self.show_warnings(result.warnings); }
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
        show_warnings: function(warnings) {
            var self = this;
            _.each(warnings, function(warning) {
                self.do_warn(warning[0], warning[1]);
            });
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
        init: function() {
            this.display_dm = new instance.web.DropMisordered(true);
            return this._super.apply(this, arguments);
        },
        load_kanban: function() {
            var self = this;
            var super_res = this._super.apply(this, arguments);
            if(this.dataset.model == 'res.partner') {
                this.display_dm.add(instance.web_linkedin.tester.test_linkedin(false)).done(function() {
                    $linkedin_button = $(QWeb.render("KanbanView.linkedinButton", {'widget': self}));
                    $linkedin_button.appendTo(self.$buttons);
                    $linkedin_button.click(function() {
                        var context = instance.web.pyeval.eval('context');
                        res = self.rpc("/linkedin/sync_linkedin_contacts", {
                            from_url: window.location.href,
                            local_context: context
                        }).done(function(result) {
                            if (result instanceof Object && result.status && result.status == 'need_auth') {
                                if (confirm(_t("You will be redirected to LinkedIn authentication page, once authenticated after that you use this widget."))) {
                                    instance.web.redirect(result.url);
                                }
                            } else {
                                self.do_reload();
                            }
                        });
                    });
                });
            }
            return super_res;
        }
    });
};
// vim:et fdc=0 fdl=0:
