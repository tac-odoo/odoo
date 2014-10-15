(function () {
    'use strict';
    var website = openerp.website;

    website.if_dom_contains('#email_designer', function () {
        website.snippet.BuildingBlock.include({
            _get_snippet_url: function () {
                var url_data = website.parseQS(window.location.search.substring(1));
                var url_hash = website.parseHash(window.location.hash.substring(1));
                $.extend( url_data, url_hash );
                if(url_data.hasOwnProperty('theme_id') && url_data.theme_id != 'basic_theme'){
                    return '/website_mail/snippets/' + url_data.theme_id;
                }
                return '/website_mail/snippets';
            },
            hide: function () {},
        });
    });
    
    var load_qweb = function load_template(template_name){
        return openerp.jsonRpc('/web/dataset/call', 'call', {
            'model': 'ir.ui.view',
            'method': 'read_template',
            'args': [template_name, openerp.website.get_context()]
        }).done(function (data) {
            openerp.qweb.add_template(data);
        });
    }

    load_qweb('website_mail.mass_mail_theme_list').then(function(){
        load_qweb('website_mail.dialog_email_template_theme');
    });

    website.snippet.options["width-x"] = website.snippet.Option.extend({
        start: function () {
            this.container_width = 600;
            var parent = this.$target.closest('[data-max-width]');
            if(parent.length != 0){
                this.container_width = parseInt(parent.attr('data-max-width'));
            } 
            var self = this;
            var offset,sib_offset,target_width,sib_width;
            this.is_image=false;
            this._super();

            var resize_values = this.getSize();
            this.$overlay.find(".oe_handle.e").removeClass("readonly");
            this.$overlay.find(".oe_handle.w").removeClass("readonly");
            if( this.$target.is('img')){
                this.$overlay.find(".oe_handle.w").addClass("readonly");
                this.$overlay.find(".oe_snippet_remove").addClass("hidden");
                this.$overlay.find(".oe_snippet_move").addClass("hidden");
                this.$overlay.find(".oe_snippet_clone").addClass("hidden");
                this.is_image=true;
            }

            this.$overlay.find(".oe_handle").on('mousedown', function (event){
                event.preventDefault();
                var $handle = $(this);
                var resize_values = self.getSize();
                var compass = false;
                var XY = false;
                if ($handle.hasClass('n')) {
                    compass = 'n';
                }
                else if ($handle.hasClass('s')) {
                    compass = 's';
                }
                else if ($handle.hasClass('e')) { 
                    compass = 'e';
                }
                else if ($handle.hasClass('w')) {
                    compass = 'w';
                }
                if(self.is_image){
                    compass="image";
                }
                self.BuildingBlock.editor_busy = true;

                var $body = $(document.body);

                var body_mousemove = function (event){
                    event.preventDefault();
                    offset = self.$target.offset().left;
                    target_width = self.get_max_width(self.$target);
                    if (compass === 'e' && self.$target.next().offset()) {
                        sib_width = self.get_max_width(self.$target.next());
                        sib_offset = self.$target.next().offset().left;
                        self.change_width(event, self.$target, target_width, offset ,'plus');
                        self.change_width(event, self.$target.next(), sib_width, sib_offset ,'minus');
                    }
                    if (compass === 'w' && self.$target.prev().offset()) {
                        sib_width = self.get_max_width(self.$target.prev());
                        sib_offset = self.$target.prev().offset().left;
                        self.change_width(event, self.$target, target_width, offset ,'minus');
                        self.change_width(event, self.$target.prev(), sib_width, sib_offset, 'plus');
                    }
                    if (compass === 'image'){
                        self.change_width(event, self.$target, target_width, offset ,'plus');
                    }
                }
                var body_mouseup = function(){
                    $body.unbind('mousemove', body_mousemove);
                    $body.unbind('mouseup', body_mouseup);
                    self.BuildingBlock.editor_busy = false;
                    self.$target.removeClass("resize_editor_busy");
                };
                $body.mousemove(body_mousemove);
                $body.mouseup(body_mouseup);
            });

        },
        change_width:function(event, target ,target_width, offset, type){
            var self = this;
            if(type == 'plus'){
                var width = event.pageX-offset;
            }else{
                var width = offset + target_width - event.pageX;
            }
            target.css("width", width+"px");
            self.BuildingBlock.cover_target(self.$overlay, self.$target);
            return;
        },
        get_int_width: function (el) {
            var el_width = el.css('width');
            return parseInt(el_width.substring(0,el_width.length -2));
        },
        get_max_width: function (el) {
            var max_width = 0;
            var self = this;
            _.each(el.siblings(),function(sib){
                max_width +=  self.get_int_width($(sib));
            })
            return this.container_width - max_width;
        },
        getSize: function () {
            this.grid = {};
            return this.grid;
        },
        on_clone: function ($clone) {
            this.BuildingBlock.cover_target(this.$overlay, this.$target);
        }
    })

        // Inline Background Color Picker For Templates
    website.snippet.options.inline_bg_colorpicker = website.snippet.options.colorpicker.extend({
        bind_events: function () {
            var self = this;
            var $td = this.$el.find("table.colorpicker td");
            var $colors = $td.children();
            var bg_color = self.$target.css('background-color');
            $colors
                .mouseenter(function () {
                    if($(this).hasClass('no_color')){
                        self.$target.css('background-color',"");
                    }else{
                        self.$target.css('background-color',$(this).css('background-color'));
                    }
                })
                .mouseleave(function () {
                    self.$target.css('background-color',bg_color);
                })
                .click(function () {
                    $td.removeClass("selected");
                    $(this).parent().addClass("selected");
                    if($(this).hasClass('no_color')){
                        bg_color = "";
                    }else{
                        bg_color = $td.filter(".selected").children().css('background-color');
                     }
                });
        }
    })

    // Inline Font Color Picker For Templates
    website.snippet.options.inline_font_colorpicker = website.snippet.options.colorpicker.extend({
        fa_color_change:function(color){
            this.$target.find("img[src^='/fa_to_img/']").each(function (i, el) {
                var src = $(el).attr('src');
                var match = src.match(/fa_to_img\/[^/]*\/([^/]*)\//); 
                $(el).attr('src',src.replace(match[1],color.replace(/ /g,'')))
                $(el).attr('data-cke-saved-src',src.replace(match[1],color.replace(/ /g,'')));
            })
        },
        bind_events: function () {
            var self = this;
            var $td = this.$el.find("table.colorpicker td");
            var $colors = $td.children();
            var color = self.$target.css('color');
            $colors
            .mouseenter(function () {
                if($(this).hasClass('no_color')){
                    self.$target.css('color',"");
                }else{
                    self.fa_color_change($(this).css('background-color'));
                    self.$target.css('color',$(this).css('background'));
                }
            })
            .mouseleave(function () {
                self.fa_color_change($(this).css('background-color'));
                self.$target.css('color',color);
            })
            .click(function () {
                $td.removeClass("selected");
                $(this).parent().addClass("selected");
                if($(this).hasClass('no_color')){
                    color = "";
                }else{
                    color = $td.filter(".selected").children().css('background-color');
                }
            });
        }
    })

    // For Converting Bootstrap Button CSS To Inline Button CSS 
    website.editor.RTELinkDialog.include({
        class_to_inline:function(element,attrs){
            var $JQ_el = $(element);
            _.each(attrs,function(attr){
                var val = $JQ_el.css(attr);
                $JQ_el.css(attr, val)
            })
        },
        save:function(){
            this._super();
            var self = this;
            _.each($('#email_body_html .btn'),function(button){
                $(button).attr('style',"-webkit-user-select: none;-moz-user-select: none;-ms-user-select: none;user-select: none; cursor: pointer")
                 self.class_to_inline(button, ['padding','font-size','line-height', 'border-radius','color','background-color','border-color',"text-decoration","display","margin-bottom","font-weight","text-align","vertical-align","background-image","border","white-space","border-top-left-radius","border-top-right-radius","border-bottom-left-radius","border-bottom-right-radius"])
            });
        }
    })

    // Copy the template to the body of the email
    $(document).ready(function () {
        $('.js_template_set').click(function(ev) {
            $('#email_designer').show();
            $('#email_template').hide();
            $(".js_content", $(this).parent().parent()).children().clone().appendTo('#email_body');
            $(".js_content", $(this).parent().parent()).children().clone().appendTo('#email_body_html');
            $('#email_body').addClass('oe_dirty');
            $('#email_body_html').addClass('oe_dirty');
            
            var url_hash = website.parseHash();
            var snippet_xml_id = $(this).attr('data-snippet-xmlid');
            if ( snippet_xml_id !== undefined){
                window.location.hash = "theme_id=" + snippet_xml_id;
            }
            openerp.website.editor_bar.edit();
            event.preventDefault();
        });
    });

    openerp.website.EmailTemplateTheme = openerp.Widget.extend({
        template: 'website_mail.dialog_email_template_theme',
        events: {
            'click .close': 'close',
            'click .theme_thumbnail div .btn': 'select_template',
        },
        start: function () {
            var self= this;
            setTimeout(function () {self.$el.addClass('in');}, 0);
        },
        select_template:function(e){
            var url_data = website.parseQS(window.location.search.substring(1));
            url_data['snippet_xml_id'] = $(e.target).attr('data-snippet-xmlid'); 
            openerp.jsonRpc('/website_mail/set_template_theme', 'call', url_data)
                .then(function (res) {
                    window.location.href = _.str.sprintf("%s?model=%s&res_id=%s&theme_id=%s", window.location.pathname,url_data.model,url_data.res_id,url_data.snippet_xml_id);
                    openerp.website.editor_bar.edit();
                 })
        },
        close: function () {
            var self = this;
            this.$el.removeClass('in');
            this.$el.addClass('out');
            setTimeout(function () {self.destroy();}, 500);
        }
    });
    website.editor.FontIconsDialog = website.editor.FontIconsDialog.extend({
        save: function () {
            this.media.renameNode("img");
            this.media.$.className = ""
            var icon = this.$('#fa-icon').val();
            var char = $.trim($("span[data-id="+icon+"]").text());
            var size = this.$('#fa-size').val();
            var color = $(this.parent.media.$).css('color');
            var size_list = { 'fa-2x':200,'fa-3x':300, 'fa-4x':400,'fa-5x':500}
            var url = _.str.sprintf('/fa_to_img/%s/%s/%s',char,color,size_list[size])
            $(this.media).attr('src', url);
            $(this.media).attr('data-cke-saved-src',url);
        },
    });
    openerp.website.ready().done(function() {
        function theme_customize() {
            var dialog = new openerp.website.EmailTemplateTheme();
            dialog.appendTo($(document.body));
        }
        $('.info_popover').popover({
            placement: "bottom",
            animation: true,
            html: true,
        });
        $('.theme_thumbnail div .btn').click(function(e){new openerp.website.EmailTemplateTheme().select_template(e)});
        $(document).on('click', "a.email_template_theme_select",theme_customize);
    });

})();