(function(){
    "use strict";
    var website = openerp.website;
    var _t = openerp._t;
    website.slide = {};
    website.slide.template = website.add_template_file('/website_slides/static/src/xml/website_slides.xml');
    website.slide.Dialog = openerp.Widget.extend({
        template: 'website.slide.dialog',
        events: {
            'hidden.bs.modal': 'destroy',
            'click button.save': 'save',
            'click button[data-dismiss="modal"]': 'cancel',
            'change .slide-upload': 'slide_upload',
            'click .list-group-item': function(ev) {
                this.$('.list-group-item').removeClass('active');
                $(ev.target).closest('li').addClass('active');
            }

        },
        init: function (el, channel_id) {
            this._super();
            this.channel_id = channel_id;
            this.file = {};
        },
        start: function () {
            var self = this;
            this.$el.modal({backdrop: 'static'});
            //this.$('input:first').focus();
           self.set_tags();
        },
        slide_upload: function(ev){
            var self = this;
            var file = ev.target.files[0];
            var ArrayReader = new FileReader();
            var BinaryReader = new FileReader();
            // file read as DataURL
            BinaryReader.readAsDataURL(file);
            BinaryReader.onloadend = function(upload) {
                var buffer = upload.target.result;
                buffer = buffer.split(',')[1];
                self.file.data = buffer;
                self.file.name = file.name;
                self.file.type = file.type;
            };

            if (file.type === 'application/pdf'){
                // file read as ArrayBuffer for PDFJS get_Document API
                this.$('.save').button('loading');
                ArrayReader.readAsArrayBuffer(file);
                ArrayReader.onload = function(evt) {
                    var buffer = evt.target.result;
                    // PDFJS can't eval path because of bundle assest
                    // https://github.com/mozilla/pdf.js/blob/master/src/pdf.js#L41
                    var path = '';
                    var pathArray = window.location.pathname.split( '/' );
                    pathArray.forEach(function(){path +='../';});
                    PDFJS.workerSrc = path + 'website_slides/static/lib/pdfjs/build/pdf.worker.js';

                    PDFJS.getDocument(buffer).then(function getPdf(pdf) {
                        pdf.getPage(1).then(function getFirstPage(page) {
                            var scale = 1;
                            var viewport = page.getViewport(scale);
                            var canvas = document.getElementById('the-canvas');
                            var context = canvas.getContext('2d');
                            canvas.height = viewport.height;
                            canvas.width = viewport.width;
                            //
                            // Render PDF page into canvas context
                            //
                            page.render({canvasContext: context, viewport: viewport}).then(function(){
                                self.$('.save').button('reset');
                            });
                        });
                    });
                };
            }
        },
        set_tags: function(){
            var self = this;
            this.$("input.slide-tags").textext({
                plugins: 'tags focus autocomplete ajax',
                keys: {8: 'backspace', 9: 'tab', 13: 'enter!', 27: 'escape!', 37: 'left', 38: 'up!', 39: 'right',
                    40: 'down!', 46: 'delete', 108: 'numpadEnter', 32: 'whitespace!'},
                ajax: {
                    url: '/slides/get_tags',
                    dataType: 'json',
                    cacheResults: true,
                },
            });
            // Adds: create tags on space + blur
            $("input.slide-tags").on('whitespaceKeyDown blur', function () {
                $(this).textext()[0].tags().addTags([ $(this).val() ]);
                $(this).val("");
            });
            $("input.slide-tags").on('isTagAllowed', function(e, data) {
                if (_.indexOf($(this).textext()[0].tags()._formData, data.tag) != -1) {
                    data.result = false;
                }
            });

        },
        get_value: function(){
            var self = this;
            var default_val = {
                'is_slide': true,
                'website_published': false,
            };
            var values= {};
            var canvas = this.$('#the-canvas')[0];
            if (self.file.type === 'application/pdf'){
                _.extend(values, {
                    'image': canvas.toDataURL().split(',')[1],
                    'width': canvas.width,
                    'height':canvas.height
                });
            }
            _.extend(values, {
                'name' : this.$('#name').val(),
                'tag_ids' : this.$('.slide-tags').textext()[0].tags()._formData,
                'datas': self.file.data || '',
                'datas_fname': self.file.name || '',
                'mimetype':self.file.type,
                'url': this.$('#url').val(),
                'parent_id': self.channel_id || ''
            });
            return _.extend(values, default_val);
        },
        validate: function(){
            this.$('.control-group').removeClass('has-error');
            if(!this.$('#name').val()){
                this.$('#name').closest('.control-group').addClass('has-error');
                return false;
            }
            if(!(this.file.name || this.$('#url').val())){
                this.$('#url').closest('.control-group').addClass('has-error');
                return false;
            }
            return true;
        },
        save: function () {
            if(this.validate()){
                var values = this.get_value();
                this.$('.modal-body').html("<h4><i class='fa fa-spinner fa-spin'></i> Redirecting to new presenation...  </h4>");
                this.$('.modal-footer').hide();
                website.form('/slides/add_slide', 'POST', values);
            }

        },
        cancel: function () {
            this.trigger("cancel");
        },
     });

    
    
    website.slide.PDFViewer_Launcher = function($PDFViewer){
        website.slide.template.then(function(){
            var file = $PDFViewer.attr('file');
            if (file){
                var PDFViewer = new website.slide.PDFViewer(file);
                PDFViewer.replace($PDFViewer);
                website.slide.PDFViewer_inst = PDFViewer;
            }
        });
    
    }; 

    website.slide.PDFViewer = openerp.Widget.extend({
        template: 'website.slide.PDFViewer',
        events: {
            'click #next': 'next',
            'click #previous': 'previous',
            'click #last': 'last',
            'click #first': 'first',
            'click #fullscreen': 'fullscreen',
            'change #page_number': 'change_page_number'
        },
        init: function(file){
            this.file = file; 
            this.file_content = null;
            this.scale = 1.5;
            this.page_number = 1;
            this.rendering = false;
        },
        start: function(){
            this.canvas = this.$('canvas')[0];
            this.ctx = this.canvas.getContext('2d');
            this.load_file();
        },
        load_file: function(){
            var self = this;
            PDFJS.getDocument(this.file).then(function (file_content) {
                self.file_content = file_content;
                self.page_count = file_content.numPages; 
                self.$('#page_count').text(self.page_count);
                self.render_page();
            });
        },
        render_page: function(){
            var self = this;
            var page_num = self.page_number;
            this.file_content.getPage(page_num).then(function(page){
                var viewport = page.getViewport(self.scale);
                self.canvas.width = viewport.width;
                self.canvas.height = viewport.height;

                var renderContext = {
                    canvasContext: self.ctx,
                    viewport: viewport
                };
                self.rendering = true;
                page.render(renderContext).then(function(){
                    self.rendering = false;
                    self.$('#PDFLoader').hide();
                    self.$('#page_number').val(page_num);
                });
            }); 
        },
        toggle_fullscreen: function() {
            var elem = document.getElementById("PDFViewer");
            if (!elem.fullscreenElement && !elem.mozFullScreenElement && !elem.webkitFullscreenElement && !elem.msFullscreenElement ) {
                if (elem.requestFullscreen) {
                    elem.requestFullscreen();
                } else if (elem.msRequestFullscreen) {
                    elem.msRequestFullscreen();
                } else if (elem.mozRequestFullScreen) {
                    elem.mozRequestFullScreen();
                } else if (elem.webkitRequestFullscreen) {
                    elem.webkitRequestFullscreen(Element.ALLOW_KEYBOARD_INPUT);
                }
            } else {
                if (elem.exitFullscreen) {
                  elem.exitFullscreen();
                } else if (elem.msExitFullscreen) {
                  elem.msExitFullscreen();
                } else if (elem.mozCancelFullScreen) {
                  elem.mozCancelFullScreen();
                } else if (elem.webkitExitFullscreen) {
                  elem.webkitExitFullscreen();
                }
            }
        },

        next: function(ev){
            ev.preventDefault();
            this.page_number = (this.page_number <= this.page_count) ? this.page_number+1 : this.page_count;
            if(!this.rendering){
                this.render_page();
            }
        },
        previous: function(ev){
            ev.preventDefault();
            this.page_number = (this.page_number > 0) ? this.page_number-1 : 1;
            if(!this.rendering){
                this.render_page();
            }
        },
        first: function(ev){
            ev.preventDefault();
            this.page_number = 1;
            if(!this.rendering){
                this.render_page();
            }
        },
        last: function(ev){
            ev.preventDefault();
            this.page_number = this.page_count;
            if(!this.rendering){
                this.render_page();
            }
        },
        fullscreen: function(ev){
            ev.preventDefault();
            this.toggle_fullscreen();
        },
        change_page_number: function(ev){
            var page_asked = parseInt(ev.target.value, 10);
            this.page_number = (page_asked > 0 && page_asked <= this.page_count) ? page_asked : this.page_count;
            if(!this.rendering){
                this.render_page();
            }
        }

     });


})();

jQuery(document).ready(function() {
    var website = openerp.website;
    website.slide.PDFViewer_Launcher($('#PDFViewer')); 
	$("timeago.timeago").timeago();
    $('.slide-container').click(function(ev){
        window.location = $(this).find("a").attr("href");
    });
    $('.slide-tabs').click(function(ev){
        ev.preventDefault();
        window.location = $(this).attr('href');
    });

    $('.slide-like, .slide-unlike').on('click' ,function(ev){
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        openerp.jsonRpc($link.data('href'), 'call', {}).then(function(data){
                $($link.data('count-el')).text(data);
        });
    });
    $('.upload').on('click' ,function(ev){
        var channel_id = $(this).attr('channel_id');
        new website.slide.Dialog(this, channel_id).appendTo(document.body);
    });
    
    $(document).keydown(function(ev){
        if (ev.keyCode == 37 || ev.keyCode == 38) {
            website.slide.PDFViewer_inst.previous(ev);
        }
        if (ev.keyCode == 39 || ev.keyCode == 40) {
            website.slide.PDFViewer_inst.next(ev);
        }
     
    });
    /*modify embed code based on options*/
    jQuery.modifyembedcode = function(currentVal) {
        var slide_embed_code = jQuery('#slide_embed_code').val();
        var new_slide_embed_code = slide_embed_code.replace(/(page=).*?([^\d]+)/,'$1' + currentVal + '$2');
        jQuery('#slide_embed_code').val(new_slide_embed_code);
    };
	// This button will increment the value
    jQuery('#btnplus').click(function(e){
        e.preventDefault();
        fieldName = jQuery(this).attr('field');
        var currentVal = parseInt(jQuery('input[name='+fieldName+']').val());
        if (!isNaN(currentVal)) {
            if(currentVal < jQuery('#pdf_page_count').val()){
                jQuery('input[name='+fieldName+']').val(currentVal + 1);
                jQuery.modifyembedcode(currentVal + 1)
            }else{
                jQuery('input[name='+fieldName+']').val(currentVal);
                jQuery.modifyembedcode(currentVal)
            }
        } else {
            jQuery('input[name='+fieldName+']').val(1);
            jQuery.modifyembedcode(1)
        }
    });
    // This button will decrement the value till 0
    jQuery("#btnminus").click(function(e) {
        e.preventDefault();
        fieldName = jQuery(this).attr('field');
        var currentVal = parseInt(jQuery('input[name='+fieldName+']').val());
        if (!isNaN(currentVal) && currentVal > 1) {
            jQuery('input[name='+fieldName+']').val(currentVal - 1);
            jQuery.modifyembedcode(currentVal - 1)
        } else {
            jQuery('input[name='+fieldName+']').val(1);
            jQuery.modifyembedcode(1)
        }
    });

    //local storage for vote once 
    if(localStorage['vote']){
        jQuery(".slide-like").hide();
        jQuery(".slide-unlike").hide();
    }
    jQuery(".slide-like").click(function(e) {
        localStorage['vote'] = true
        jQuery(".slide-like").hide();
        jQuery(".slide-unlike").hide();
    });
    jQuery(".slide-unlike").click(function(e) {
        localStorage['vote'] = true
        jQuery(".slide-like").hide();
        jQuery(".slide-unlike").hide();
    });

});

