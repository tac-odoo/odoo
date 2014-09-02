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
        render_page: function(page_number){
            var self = this;
            var page_num = page_number || self.page_number;
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
                    self.page_number = page_num;
                });
            });
        },
        next: function(ev){
            ev.preventDefault();
            if (this.page_number >= this.page_count){
                return;
            }
            this.page_number += 1;
            if(!this.rendering){
                this.render_page();
            }
        },
        previous: function(ev){
            ev.preventDefault();
            if (this.page_number <= 1){
                return;
            }
            this.page_number -= 1;
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
            //TODO: Display warning when broswer not support native fullscreen API
            website.fullScreenAPI.requestFullScreen(this.canvas);
        },
        change_page_number: function(ev){
            var page_asked = parseInt(ev.target.value, 10);
            this.page_number = (page_asked > 0 && page_asked <= this.page_count) ? page_asked : this.page_count;
            if(!this.rendering){
                this.render_page();
            }
        }

     });

    //Export fullscreen Browser Compatible API to website namespace
    var fullScreenApi = {
            supportsFullScreen: false,
            isFullScreen: function() { return false; },
            requestFullScreen: function() {},
            cancelFullScreen: function() {},
            fullScreenEventName: '',
            prefix: ''
        },
        browserPrefixes = 'webkit moz o ms khtml'.split(' ');

    // check for native support
    if (typeof document.cancelFullScreen != 'undefined') {
        fullScreenApi.supportsFullScreen = true;
    } else {
        // check for fullscreen support by vendor prefix
        for (var i = 0, il = browserPrefixes.length; i < il; i++ ) {
            fullScreenApi.prefix = browserPrefixes[i];

            if (typeof document[fullScreenApi.prefix + 'CancelFullScreen' ] != 'undefined' ) {
                fullScreenApi.supportsFullScreen = true;
                break;
            }
        }
    }

    if (fullScreenApi.supportsFullScreen) {
        fullScreenApi.fullScreenEventName = fullScreenApi.prefix + 'fullscreenchange';

        fullScreenApi.isFullScreen = function() {
            switch (this.prefix) {
                case '':
                    return document.fullScreen;
                case 'webkit':
                    return document.webkitIsFullScreen;
                default:
                    return document[this.prefix + 'FullScreen'];
            }
        };
        fullScreenApi.requestFullScreen = function(el) {
            return (this.prefix === '') ? el.requestFullScreen() : el[this.prefix + 'RequestFullScreen']();
        };
        fullScreenApi.cancelFullScreen = function(el) {
            return (this.prefix === '') ? document.cancelFullScreen() : document[this.prefix + 'CancelFullScreen']();
        };
    }

    website.fullScreenAPI = fullScreenApi;

})();

$(document).ready(function() {
    var website = openerp.website;
    website.slide.PDFViewer_Launcher($('#PDFViewer'));
    $("timeago.timeago").timeago();

    $('.slide-container').on('click', function(ev){
        window.location = $(this).find("a").attr("href");
    });
    $('.slide-tabs').on('click', function(ev){
        ev.preventDefault();
        window.location = $(this).attr('href');
    });

    $('.slide-like, .slide-unlike').on('click', function(ev){
        ev.preventDefault();
        if(!localStorage['vote']){
            var $link = $(ev.currentTarget);
            openerp.jsonRpc($link.data('href'), 'call', {}).then(function(data){
                    $($link.data('count-el')).text(data);
            });
            localStorage['vote'] = true;
        }
    });
    $('.upload').on('click' ,function(ev){
        var channel_id = $(this).attr('channel_id');
        new website.slide.Dialog(this, channel_id).appendTo(document.body);
    });

    $(document).keydown(function(ev){
        if (ev.keyCode == 37) {
            website.slide.PDFViewer_inst.previous(ev);
        }
        if (ev.keyCode == 39) {
            website.slide.PDFViewer_inst.next(ev);
        }
    });

    /*modify embed code based on options*/
    website.slide.modifyembedcode = function(currentVal) {
        var $embed_input = $('#slide_embed_code');
        var slide_embed_code = $embed_input.val();
        var tmp_embed_code = slide_embed_code.replace(/(page=).*?([^\d]+)/,'$1' + currentVal + '$2');
        $embed_input.val(tmp_embed_code);
    };
    // This button will increment the value

    $('#btnplus').on('click', function(e){
        e.preventDefault();
        var currentVal = parseInt($('#page_embed').val());
        var maxval = parseInt($('#page_count').text());
        if(currentVal < maxval){
            $('#page_embed').val(currentVal + 1);
            website.slide.modifyembedcode(currentVal + 1);
        }
    });
    $("#btnminus").on('click', function(e) {
        e.preventDefault();
        var currentVal = parseInt($('#page_embed').val());
        if (currentVal > 1) {
            $('#page_embed').val(currentVal - 1);
            website.slide.modifyembedcode(currentVal - 1)
        }
    });

    // toggle option on pdfview 
    $('.share-toggle-option').on('click', function (ev) {        
        ev.preventDefault();
        var toggleDiv = $(this).data('slide-share');
        $(toggleDiv).slideToggle();
    });

});

