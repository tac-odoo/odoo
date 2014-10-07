$(document).ready(function() {
    "use strict";
    
    var cover_resize_class = "";
    var cover_background = "#000000";
    var cover_opacity = 1.0;

    var website = openerp.website;
    var _t = openerp._t;

    website.EditorBarContent.include({
        new_blog_post: function() {
            website.session.model('blog.blog').call('name_search', [], { context: website.get_context() })
            .then(function(blog_ids) {
                if (blog_ids.length == 1) {
                    document.location = '/blogpost/new?blog_id=' + blog_ids[0][0];
                }
                else if(blog_ids.length > 1){
                    website.prompt({
                        id: "editor_new_blog",
                        window_title: _t("New Blog Post"),
                        select: "Select Blog",
                        init: function (field) {
                          return blog_ids;
                        },
                    }).then(function (blog_id) {
                        document.location = '/blogpost/new?blog_id=' + blog_id;
                      });
                }
            });
        },
    });
    if ($('.website_blog').length) {
        website.EditorBar.include({
            edit: function () {
                var self = this;
                $('.popover').remove();
                this._super();
                $('body').on('click','#change_cover', _.bind(this.change_cover, self.rte.editor));
                $('body').on('click', '#clear_cover', this.clean_bg);
                $('body').on('click mouseover', '.cover_cust_menu',this.click_event);
                $('body').on('mouseleave', '.cover_cust_menu',this.mouseleave_event);
                $('body').on('media-saved', self, function (o) {
                    if ($('.cover').length) {
                        $.blockUI.defaults.css = { width: '30%',top: '40%',left: '35%',textAlign: 'center',color:'#FFFFFF'};
                        $.blockUI({ message: '<div><i class="fa fa-spinner fa-5x fa-spin"></i><br/>Uploading...' }); 
                        $('ul.cover_background li').removeClass("active");
                        var url = $('.cover-storage').attr('src');
                        $('.js_blogcover').css({"background-image": !_.isUndefined(url) ? 'url(' + url + ')' : "pink"});
                        $('.cover-storage').replaceWith("<div class='cover-storage oe_hidden'></div>");
                        $.unblockUI();
                    }
                });
                if ($('.cover').length) {
                  cover_resize_class = $('#title').attr("class");
                  cover_background = $('.js_blogcover').css("background-color");
                  cover_opacity = $(".js_blogcover").css("opacity");
                }
            },
            save : function() {
                var res = this._super();
                if ($('.cover').length) {
                    openerp.jsonRpc("/blogpost/change_background", 'call', {
                        'post_id' : $('#blog_post_name').attr('data-oe-id'),
                        'cover_properties' : '{"background-image": "'+ $('.js_blogcover').css("background-image").replace(/"/g,'') +'","background-color": "'+ $('.js_blogcover').css("background-color") +'","opacity":"'+ cover_opacity +'","resize_class": "'+cover_resize_class + '"}',
                    });
                }
                return res;
            },
            clean_bg : function() {
                $('.js_blogcover').css({"background":'none', 'opacity':1});
            },
            click_event : function(e) {
                if(e.type=="click") {
                    $('#' + $(this).attr('id') + ' li').removeClass("active");
                    $('#' + e.target.id).parent().addClass("active");
                    if($(this).attr('id') == "cover_resize"){
                        $('#title').attr("class" ,"cover " + e.target.id)
                        cover_resize_class = $('#title').attr("class");
                    }
                    else if($(this).attr('id') == "cover_opacity"){
                        $('.js_blogcover').css("opacity",e.target.id);
                        cover_opacity = e.target.id;
                    }
                    else if($(this).attr('id') == "cover_color"){
                        $('.js_blogcover').css("background-color",e.target.id);
                        cover_background = e.target.id;
                    }
                }
                else {
                    if($(this).attr('id') == "cover_resize"){
                        $('#title').attr("class" ,"cover " + e.target.id);
                    }
                    else if($(this).attr('id') == "cover_opacity"){
                        $('.js_blogcover').css("opacity",e.target.id);
                    }
                    else if($(this).attr('id') == "cover_color"){
                        $('.js_blogcover').css("background-color",e.target.id);
                    }
                }
            },
            mouseleave_event : function(e) {
                if($(this).attr('id') == "cover_resize"){
                    $('#title').attr("class",cover_resize_class);
                }
                else if($(this).attr('id') == "cover_opacity"){
                    $('.js_blogcover').css("opacity",cover_opacity);
                }
                else if($(this).attr('id') == "cover_color"){
                    $('.js_blogcover').css("background-color",cover_background);
                }
            },
            change_cover : function() {
                var self  = this;
                var element = new CKEDITOR.dom.element(self.element.find('.cover-storage').$[0]);
                var editor  = new website.editor.MediaDialog(self, element);
                editor.appendTo('body');
                editor.$('[href="#editor-media-video"], [href="#editor-media-icon"]').addClass('hidden');
            },
        });
    }
});
