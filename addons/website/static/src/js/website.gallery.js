(function() {
    'use strict';
    
    var website = openerp.website, 
        _t = openerp._t;

    /*--------------------------------------------------------------------------
     Template files to load
     --------------------------------------------------------------------------*/
    website.add_template_file('/website/static/src/xml/website.gallery.xml');

    /*--------------------------------------------------------------------------
      Gallery Snippet
      
      This is the snippet responsible for configuring the image galleries.
      Look at /website/views/snippets.xml for the available options
      ------------------------------------------------------------------------*/
    website.snippet.options.gallery = website.snippet.Option.extend({
        start  : function() {
            var self = this;
            this._super();
            //this.add_mutation_observer();
        },
        select : function (next_previous) {
            var self = this;
            this._super(next_previous);
            this.apply(next_previous);
        },
        apply : function (next_previous) {
            if (next_previous.$next) {
                var self = this;
                var key = next_previous.$next.data("key");
                var value = next_previous.$next.data("value");
                if (typeof this[key] === 'function') {
                    typeof this[key](key, value);
                } else {
                    if (typeof this[value] === 'function') {
                        this[value](key, value);    
                    }
                }
            }
        },
        styling  : function(key, value) {
            var self = this,
                $imgs = self.$target.find("img");
                $imgs.each(
                   function() { $(this).toggleClass(value); }
                );
            // we don't wan't self.target to spin nor to look like a thumbnail
            if (self.$target.hasClass(value)) {
                self.$target.removeClass(value);
            }
        },
        interval : function(next_previous) {
            var ms = next_previous.$next.data("value").split("-")[1];
            this.$target.attr("data-"+next_previous.$next.data("key"), ms);
        }, 
        reapply : function(key, value) {
            if (this.$target.hasClass("nomode")) {
                this.nomode();
            }
            if (this.$target.hasClass("masonry")) {
                this.masonry();
            }
            if (this.$target.hasClass("grid")) {
                this.grid();
            }
            if (this.$target.hasClass("slideshow")) {
                this.slideshow();
            }
        },
        nomode : function() {
        	//this.suspend_mutation_observer();
        	var self = this;
            var $imgs = this.$target.find("img"),
                classes="",
                cls = ['1', '2', '3', '4', '6', '12'];
            for (var i in  cls) { classes+= " col-md-"+i; }
            $imgs.each(function() {
                var $cur = $(this);
                $cur.removeClass(classes);
                self.img_responsive($cur);
            });
            this.$target.children().remove();
            this.$target.append($imgs);
            //this.resume_mutation_observer();
        },
        masonry : function() {
            //this.suspend_mutation_observer();
            var self     = this,
                $imgs    = this.$target.find("img"),
                columns  = this.get_columns(),
                colClass = undefined,
                $cols    = [];
            this.$target.children().remove();
            
            // if no columns let's default to 3, here we must update the DOM accordingly :'(
            if (columns === 0) { 
                columns = 3;
                this.$target.removeClass("columns-0").addClass("columns-"+columns);
            }
            colClass = "col-md-"+(12/columns);

            // create columns
            for (var c = 0; c < columns; c++) {
                var $col = $('<div class="col"></div>').addClass(colClass);
                this.$target.append($col);
                $cols.push($col);
            }

            // stack the images
            $imgs.each(function() {
                // this is ugly, but otherwise the load event is not reliably 
                // triggered by browsers and computing the column size is not
                // reliable
                var $img = self.img_from_src($(this).attr("src")),  
                    classes = self.styles_to_preserve($(this));
                self.img_responsive($img);
                // attach image to 1st column so its size can be computed 
                // reliably, then move it to the right target column
                $cols[0].append($img);
                $img.one('load', function(event) { 
                    var $cur = $(event.target);
                    $cur = $cur.detach(); 
                    self.lowest($cols).append($cur);
                    $cur.addClass(classes);
                 });
            });
            //this.resume_mutation_observer();

        },
        grid : function() {
            //this.suspend_mutation_observer();
            var self     = this,
                $imgs    = this.$target.find("img"),
                $img     = undefined,
                $row     = $('<div class="row"></div>'),
                columns  = this.get_columns() || 3,
                colClass = "col-md-"+(12/columns);
            this.$target.children().remove();
            $row.appendTo(this.$target);
            $imgs.each(function(index) { // 0 based index
                $img = $(this);
                self.img_preserve_styles($img);
                self.img_responsive($img);
                $img.addClass(colClass);
                $img.appendTo($row);
                if ( (index+1) % columns === 0) {
                    $row = $('<div class="row"></div>');
                    $row.appendTo(self.$target);
                }                
            });
            //this.resume_mutation_observer();

        },
        slideshow :function () {
            //this.suspend_mutation_observer();
            
            var self = this;
            var $imgs = this.$target.find("img"),
                urls = [],
                params = { 
                        srcs : urls, 
                        index: 1,
                        title: "",
                        interval : this.$target.data("interval") || false,
                        id: _.uniqueId("slideshow_")
                },
                $slideshow = undefined;
                
            $imgs.each(function() { urls.push( $(this).attr("src") ); } );
            $slideshow = $(openerp.qweb.render('website.gallery.slideshow', params));
            this.$target.children().remove();
            this.$target.append($slideshow);
            $slideshow.css("height", Math.round(window.innerHeight*0.7));
            
            //this.resume_mutation_observer();
        },
        
        columns : function(key, value) {
            this.reapply(key, value); // nothing to do, just recompute with new values
        },
        
        images_add : function() {
        	/* will be moved in ImageDialog from MediaManager */
            var self = this,
            $upload_form = $(openerp.qweb.render('website.gallery.dialog.upload')),
            $progressbar = $upload_form.find(".progress-bar");

            $upload_form.appendTo(document.body);
            
            $upload_form.on('modal.bs.hide', function() { $(this).remove(); } );
            
            $upload_form.find(".alert-success").hide();
            $upload_form.find(".alert-danger").hide();
            $progressbar.hide();

            $upload_form.on("submit", function(event) {
                event.preventDefault();
                $progressbar.show();
                var files = $(this).find('input[type="file"]')[0].files;
                var formData = new FormData();
                for (var i = 0; i < files.length; i++ ) {
                    var file = files[i];
                    formData.append('upload', file, file.name);
                }
                /* 
                 * Images upload : don't change order of contentType & processData
                 * and don't change their values, otherwise the XHR will be 
                 * wrongly conceived by jQuery. 
                 * 
                 * (missing boundary in the content-type header field)
                 * Leading to an upload failure.
                 */
                $.ajax('/website/images_upload', {
                    type: 'POST',
                    data: formData,
                    contentType: false,  /* multipart/form-data for files */
                    processData: false,            
                    dataType: 'json',
                    xhrFields: { /* progress bar support */
                        onprogress: function(up) {
                            var pc = Math.floor((up.total / up.totalSize) * 100);
                            var text = " "+pc+" %";
                            $progressbar.css({'width': pc+'%' }).attr("aria-valuenow", pc).text(text);
                        }
                    }
                }).then(
                    
                    function(response) { /* success */  
                        $progressbar.addClass("progress-bar-success");
                        $upload_form.find(".alert-success").show();
                        for (var i = 0 ; i < response.length; i++) {
                            $('<img />').attr("src", response[i].website_url).appendTo(self.$target);
                        }
                        self.reapply(); // refresh the $target
                    },  
                    
                    function(response) { /* failure */
                        $progressbar.addClass("progress-bar-danger");
                        $upload_form.find(".alert-danger").show();
                    } 
                );
            });
            $upload_form.modal({ backdrop : false });
            var filepicker = $upload_form.find('input[name="upload"]');
            filepicker.click();
            // we don't want this to be selected in the menu
            this.$target.removeClass("images_add");
        },
        images_rm   : function(next_previous) {
            this.$target.children().remove();
            this.$target.append($('<div class="alert alert-info"> Add Images from the menu</div>'));
            // we don't want this to be selected in the menu
            this.$target.removeClass("images_rm");
        },
        spacing : function() { // done via css, keep it to avoid undefined error
        },
        sizing : function() { // done via css, keep it to avoid undefined error
        },
        onBlur : function() {
            //this.remove_mutation_observer();
        },
        onFocus : function() {
            //this.add_mutation_observer();
        },
        on_remove : function() {
            //this.remove_mutation_observer();
        },
        /*
         *  helpers
         */
        styles_to_preserve : function($img) {
            var styles = [ 'img-rounded', 'img-thumbnail', 'img-circle', 'shadow', 'fa-spin' ];
            var preserved = [];
            
            for (var style in styles) {
                if ($img.hasClass(style)) {
                    preserved.push(style);
                }
            }
            return preserved.join(' ');
        },
        img_preserve_styles : function($img) {
            var classes = this.styles_to_preserve($img);
            $img.removeAttr("class");
            $img.addClass(classes);
            return $img;
        },
        img_from_src : function(src) {
            var self = this;
            var $img = $("<img></img>").attr("src", src);
            return $img;
        },
        img_responsive : function(img) {
            img.addClass("img img-responsive");
            return img;
        },
        lowest : function($cols) {
            var height = 0, min = -1, col=0, lowest = undefined;
            for (var i = 0; i < $cols.length ; i++) {
                height = $cols[i].height();
                if (min === -1 || height < min) {
                    min = height;
                    lowest = $cols[i];
                }
            }
            return lowest;
        },
        get_columns : function() { 
            var c = 0;
            if (this.$target.hasClass("columns-1")) c = 1;
            if (this.$target.hasClass("columns-2")) c = 2;
            if (this.$target.hasClass("columns-3")) c = 3;
            if (this.$target.hasClass("columns-4")) c = 4;
            if (this.$target.hasClass("columns-6")) c = 6;
            if (this.$target.hasClass("columns-12")) c = 12;
            return c;
        },
        clean_for_save: function() {
            var self = this;
            if (this.$target.hasClass("slideshow")) {
                this.$target.removeAttr("style");
            }
            //this.remove_mutation_observer();
        },
        mutation_callback : function(mutations) {
            var require_reapply = false;
            for (var i = 0; i < mutations.length; i++) {
            	if (mutations[i].removedNodes.length > 0) {
            		require_reapply = true;
            	}
            }
            window.galleryObserver.takeRecords();
            if (require_reapply) {
            	this.reapply();
            }
        },
        add_mutation_observer: function() {
            if (!window.galleryObserver) {
                window.galleryObserver = new MutationObserver(this.mutation_callback);
                //this.resume_mutation_observer();
            }
        },
        suspend_mutation_observer : function() {
            window.galleryObserver.disconnect();
        },
        resume_mutation_observer : function() {
            var galleryTarget = (this.$target.is(".gallery")) ? this.$target[0] : this.$target.closest(".gallery")[0];
            window.galleryObserver.observe(galleryTarget, { 
                subtree: true, 
                childList: true 
            }); 
        },
        remove_mutation_observer: function() {
            if (window.galleryObserver) {
                //this.suspend_mutation_observer();
                delete window.galleryObserver;
            }
        }
        
    }); // website.snippet.Option.extend

})(); // anonymous function
