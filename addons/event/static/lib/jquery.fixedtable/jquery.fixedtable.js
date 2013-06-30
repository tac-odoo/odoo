/*

Source: http://www.novasoftware.com/download/jquery_fixedtable/jquery_fixedtable.aspx
This jQuery plugin is learned from https://www.open2space.com/projects/fixedtable.
We have improved it, and fixed some bugs.

@2013-05-30: Changed by xal@openerp.com to allow better fix for OpenERP.
             - removed  mouseout, hover colors
	     - removed fixedColumnsWidth => this is now automatically computed
	     - remove outerId => we automatically take element parent

Example:

$(document).ready(function() {
    $(".tableDiv").each(function() {
        var Id = $(this).get(0).id;
        var maintbheight = 555;
        var maintbwidth = 760;

        $("#" + Id + " .FixedTables").fixedTable({
            width: maintbwidth,
            height: maintbheight,
            fixedColumns: 1,
            classHeader: "fixedHead",
            classFooter: "fixedFoot",
            classColumn: "fixedColumn",
        });
    });
});

*/

(function($) {
    // ***********************************************
    //The main fixedTable function
    $.fn.fixedTable = function(opts) {

        // plugin default options
        var defaults = {
            'width': '100%',
            'height': '100%',
            'fixedColumns': 0,
            'classHeader': 'fixedHead',
            'classFooter': 'fixedFoot',
            'classColumn': 'fixedColumn',
        };

        var $main_element = $(this[0]);
        var $outer_element = $($main_element.parent());
        //default options defined in $.fn.fixedTable.defaults - at the bottom of this file.
        //var options = $.extend({}, $.fn.fixedTable.defaults, opts);
        var options = $.extend({}, defaults, opts);

        // setting up options
        var maindiv_width = options.width;
        if (maindiv_width.search('%') > -1) {
            $main_element.hide();
            maindiv_width = $main_element.parent().width();
            $main_element.show();
        }
        // update size of main element
        // $main_element.width(maindiv_width);

        var fixedColumnWidth = 0;
        var columns_width = [];
        if (options.fixedColumns > 0 && !isNaN(options.fixedColumns)) {
            $main_element.find('thead tr > *:lt('+ options.fixedColumns + ')').each(function() {
                fixedColumnWidth += $(this).outerWidth();
                columns_width.push($(this).width());
            });
        }

        var header_rows_height = [];
        $main_element.find('thead tr > th:first-child').each(function() {
            header_rows_height.push($(this).height());
        })

        var tbl = this;
        var layout = buildLayout(tbl, options, columns_width);
        //see the buildLayout() function below

        //we need to set the width (in pixels) for each of the tables in the fixedContainer area
        //but, we need to subtract the width of the fixedColumn area.
        var w = maindiv_width - fixedColumnWidth - _getScrollbarWidth();
        //sanity check
        if (w <= 0) { w = maindiv_width }

        $(".fixedContainer", layout).width(w);

        $(".fixedContainer ." + options.classHeader, layout).css({
            width: (w) + "px",
            "float": "left",
            "overflow": "hidden"
        });

        $(".fixedContainer .fixedTable", layout).css({
            "float": "left",
            width: (w + 16) + "px",
            "overflow": "auto"
        });
        $(".fixedContainer", layout).css({
            width: w - 1,
            "float": "left"
        });    //adjust the main container to be just larger than the fixedTable

        $(".fixedContainer ." + options.classFooter, layout).css({
            width: (w) + "px",
            "float": "left",
            "overflow": "hidden"
        });
        $("." + options.classColumn + " > .fixedTable", layout).css({
            "width": fixedColumnWidth,
            "overflow": "hidden",
            "border-collapse": $(tbl).css("border-collapse"),
            "padding": "0"
        });

        $("." + options.classColumn, layout).width(fixedColumnWidth);
        $("." + options.classColumn, layout).height(options.height);
        $("." + options.classColumn + " ." + options.classHeader + " table tbody tr", layout).each(function(header_row_index) {
            $(this).find('td').each(function(col_index) {
                $(this).width(columns_width[col_index]);
                $(this).height(header_rows_height[header_row_index]);
            });
        });
        $("." + options.classColumn + " ." + options.classFooter + " table tbody tr td", layout).width(function (index) {
            $(this).width(columns_width[index]);
        });

        //adjust the table widths in the fixedContainer area
        var fh = $(".fixedContainer > ." + options.classHeader + " > table", layout);
        var ft = $(".fixedContainer > .fixedTable > table", layout);
        var ff = $(".fixedContainer > ." + options.classFooter + " > table", layout);

        var maxWidth = fh.width();
        if (ft.length > 0 && ft.width() > maxWidth) { maxWidth = ft.width(); }
        if (ff.length > 0 && ff.width() > maxWidth) { maxWidth = ff.width(); }


        if (fh.length) { fh.width(maxWidth); }
        if (ft.length) { ft.width(maxWidth); }
        if (ff.length) { ff.width(maxWidth); }

        //adjust the widths of the fixedColumn header/footer to match the fixed columns themselves
        $("." + options.classColumn + " > ." + options.classHeader + " > table > tbody > tr:first > td", layout).each(function(pos) {
            var tblCell = $("." + options.classColumn + " > .fixedTable > table > tbody > tr:first > td:eq(" + pos + ")", layout);
            var tblFoot = $("." + options.classColumn + " > ." + options.classFooter + " > table > tbody > tr:first > td:eq(" + pos + ")", layout);
            var maxWidth = $(this).width();
            if (tblCell.width() > maxWidth) { maxWidth = tblCell.width(); }
            if (tblFoot.length && tblFoot.width() > maxWidth) { maxWidth = tblFoot.width(); }
            $(this).width(maxWidth);
            $(tblCell).width(maxWidth);
            if (tblFoot.length) { $(tblFoot).width(maxWidth); }
        });


        //set the height of the table area, minus the heights of the header/footer.
        // note: we need to do this after the other adjustments, otherwise these changes would be overwrote
        var h = options.height - parseInt($(".fixedContainer > ." + options.classHeader, layout).height()) - parseInt($(".fixedContainer > ." + options.classFooter, layout).height());
        //sanity check
        if (h < 0) { h = options.height; }
        $(".fixedContainer > .fixedTable", layout).height(h);
        $("." + options.classColumn + " > .fixedTable", layout).height(h);

        //Adjust the fixed column area if we have a horizontal scrollbar on the main table
        // - specifically, make sure our fixedTable area matches the main table area minus the scrollbar height,
        //   and the fixed column footer area lines up with the main footer area (shift down by the scrollbar height)
        var h = $(".fixedContainer > .fixedTable", layout)[0].offsetHeight - 16;
        $("." + options.classColumn + " > .fixedTable", layout).height(h);  //make sure the row area of the fixed column matches the height of the main table, with the scrollbar

        // Apply the scroll handlers
        $(".fixedContainer > .fixedTable", layout).scroll(function() { handleScroll($outer_element, options); });
        //the handleScroll() method is defined near the bottom of this file.

        //$.fn.fixedTable.adjustSizes(mainid);
        adjustSizes($outer_element, options, header_rows_height);
        return tbl;
    }

    /*
     * return int
     * get the width of the browsers scroll bar
     */
    function _getScrollbarWidth() {
        var scrollbarWidth = 0;
        
        if (!scrollbarWidth) {
            if (/msie/.test(navigator.userAgent.toLowerCase())) {
                var $textarea1 = $('<textarea cols="10" rows="2"></textarea>')
                                    .css({ position: 'absolute', top: -1000, left: -1000 }).appendTo('body'),
                    $textarea2 = $('<textarea cols="10" rows="2" style="overflow: hidden;"></textarea>')
                                    .css({ position: 'absolute', top: -1000, left: -1000 }).appendTo('body');
                scrollbarWidth = $textarea1.width() - $textarea2.width() + 2; // + 2 for border offset
                $textarea1.add($textarea2).remove();
            } else {
                var $div = $('<div />')
                            .css({ width: 100, height: 100, overflow: 'auto', position: 'absolute', top: -1000, left: -1000 })
                            .prependTo('body').append('<div />').find('div')
                            .css({ width: '100%', height: 200 });
                scrollbarWidth = 100 - $div.width();
                $div.parent().remove();
            }
        }
        return scrollbarWidth;
    }

    function buildLayout(src, options, columns_width) {
        //create a working area and add it just after our table.
        //The table will be moved into this working area
        var area = $("<div class=\"fixedArea\"></div>")
                        .width(options.width)
                        .height(options.height)
                        .appendTo($(src).parent());

        //fixed column items
        var fc = $("<div class=\"" + options.classColumn + "\" style=\"float: left;\"></div>").appendTo(area);
        var fch = $("<div class=\"" + options.classHeader + "\"></div>").appendTo(fc);
        var fct = $("<div class=\"fixedTable\"></div>").appendTo(fc);
        var fcf = $("<div class=\"" + options.classFooter + "\"></div>").appendTo(fc);

        //fixed container items
        var fcn = $("<div class=\"fixedContainer\"></div>").appendTo(area);
        var fcnh = $("<div class=\"" + options.classHeader + "\"></div>").appendTo(fcn);
        var fcnt = $("<div class=\"fixedTable\"></div>").appendTo(fcn);
        var fcnf = $("<div class=\"" + options.classFooter + "\"></div>").appendTo(fcn);

        //create the fixed column area
        if (options.fixedColumns > 0 && !isNaN(options.fixedColumns)) {
            buildFixedColumns(src, "thead", options.fixedColumns, fch, columns_width);
            buildFixedColumns(src, "tbody", options.fixedColumns, fct, columns_width);
            buildFixedColumns(src, "tfoot", options.fixedColumns, fcf, columns_width);
            //see the buildFixedColumns() function below
        }

        //Build header / footer areas
        buildFixedTable(src, "thead", fcnh);
        buildFixedTable(src, "tfoot", fcnf);
        //see the buildFixedTable() function below

        //Build the main table
        //we'll cheat here - the src table should only be a tbody section, with the remaining columns, 
        //so we'll just add it to the fixedContainer table area.
        fcnt.append(src);
        return area;
    }

    /* ******************************************************************** */
    // duplicate a table section (thead, tfoot, tbody), but only for the desired number of columns
    function buildFixedColumns(src, section, cols, target, columns_width) {
        //TFOOT - get the needed columns from the table footer
        if ($(section, src).length) {
            var colHead = $("<table></table>").appendTo(target);

            //If we have a thead or tfoot, we're looking for "TH" elements, otherwise we're looking for "TD" elements
            var cellType = "td";  //deafault cell type
            if (section.toLowerCase() == "thead" || section.toLowerCase() == "tfoot") { cellType = "th"; }

            //check each of the rows in the thead
            $(section + " tr", src).each(function() {
                var tr = $("<tr></tr>").appendTo(colHead);
                $(cellType + ":lt(" + cols + ")", this).each(function(index) {
                    var c = $("<td>" + $(this).html() + "</td>")
                            .addClass(this.className)
                            .attr("id", this.id)
                            .width(columns_width[index])
                            .css('min-width', columns_width[index]+'px')
                            .appendTo(tr);
                    for (var i=0; i < this.attributes.length; i++) {
                        var attr = this.attributes[i];
                        if (!attr.name.indexOf('data-')) {
                            c.attr(attr.name, attr.value);
                        }
                    }
                    //Note, we copy the class names and ID from the original table cells in case there is any processing on them.
                    //However, if the class does anything with regards to the cell size or position, it could mess up the layout.

                    //Remove the item from our src table.
                    $(this).remove();
                });
            });
        }
    }

    /* ******************************************************************** */
    // duplicate a table section (thead, tfoot, tbody)
    function buildFixedTable(src, section, target) {
        if ($(section, src).length) {
            var th = $("<table></table>").appendTo(target);
            var tr = null;

            //If we have a thead or tfoot, we're looking for "TH" elements, otherwise we're looking for "TD" elements
            var cellType = "td";  //deafault cell type
            if (section.toLowerCase() == "thead" || section.toLowerCase() == "tfoot") { cellType = "th"; }

            $(section + " tr", src).each(function() {
                var tr = $("<tr></tr>").appendTo(th);
                $(cellType, this).each(function() {
                    var c = $("<td>" + $(this).html() + "</td>")
                                .addClass(this.className)
                                .appendTo(tr);
                    for (var i=0; i < this.attributes.length; i++) {
                        var attr = this.attributes[i];
                        if (!attr.name.indexOf('data-')) {
                            c.attr(attr.name, attr.value);
                        }
                    }
                });

            });
            //The header *should* be added to our head area now, so we can remove the table header
            $(section, src).remove();
        }
    }

    // ***********************************************
    // Handle the scroll events
    function handleScroll(mainid, options) {
        //Find the scrolling offsets
        var tblarea = mainid.find(" .fixedContainer > .fixedTable");
        var x = tblarea[0].scrollLeft;
        var y = tblarea[0].scrollTop;

        mainid.find(" ." + options.classColumn + " > .fixedTable")[0].scrollTop = y;
        mainid.find(" .fixedContainer > ." + options.classHeader)[0].scrollLeft = x;
        mainid.find(" .fixedContainer > ." + options.classFooter)[0].scrollLeft = x;
    }

    // ***********************************************
    //  Reset the heights of the rows in our fixedColumn area
    function adjustSizes(mainid, options, headers_row_height) {
        var maintbheight = options.height;

        // row height
        mainid.find("." + options.classColumn + " .fixedTable table tbody tr").each(function(i) {
            var maxh = 0;
            var fixedh = $(this).height();
            var contenth = mainid.find(".fixedContainer .fixedTable table tbody tr").eq(i).height();
            if (contenth > fixedh) {
                maxh = contenth;
            }
            else {
                maxh = fixedh;
            }
            //$(this).height(contenth);
            $(this).children("td").height(maxh);
            mainid.find(".fixedContainer .fixedTable table tbody tr").eq(i).children("td").height(maxh);
        });

        //adjust the cell widths so the header/footer and table cells line up
        var htbale = mainid.find(".fixedContainer ." + options.classHeader + " table");
        var ttable = mainid.find(".fixedContainer .fixedTable table");
        var ccount = mainid.find(".fixedContainer ." + options.classHeader + " table tr:first td").size();
        var widthArray = new Array();
        var totall = 0;

        mainid.find(".fixedContainer ." + options.classHeader + " table tr:first td").each(function(pos) {
            var cwidth = $(this).width();
            mainid.find(".fixedContainer .fixedTable table tbody td").each(function(i) {
                if (i % ccount == pos) {
                    if ($(this).width() > cwidth) {
                        cwidth = $(this).width();
                    }
                }
            });
            widthArray[pos] = cwidth;
            totall += (cwidth + 2);
        });

        mainid.find(".fixedContainer ." + options.classHeader + " table").width(totall + 100);
        mainid.find(".fixedContainer .fixedTable table").width(totall + 100);
        mainid.find(".fixedContainer ." + options.classFooter + " table").width(totall + 100);
        for (i = 0; i < widthArray.length; i++) {
            mainid.find(".fixedContainer ." + options.classHeader + " table tr td").each(function(j) {
                if (j % ccount == i) {
                    $(this).attr("width", widthArray[i] + "px");
                }
            });

            mainid.find(".fixedContainer .fixedTable table tr td").each(function(j) {
                if (j % ccount == i) {
                    $(this).attr("width", widthArray[i] + "px");
                }
            });

            mainid.find(".fixedContainer ." + options.classFooter + " table tr td").each(function(j) {
                if (j % ccount == i) {
                    $(this).attr("width", widthArray[i] + "px");
                }
            });
        }
        mainid.find('.' + options.classColumn + ' .' + options.classHeader + ' table tr > td:first-child').each(function(index) {
            var row_height = $(this).height();
            var row_tds = $('.fixedContainer .'+ options.classHeader+' table tr:eq('+index+') td');
            $(row_tds[0]).height(row_height)
            var row_realsize = $(row_tds[0]).height();
            if (row_realsize <= row_height) {
                // increase size if browse display cell with a lower size than expected
                row_height += (row_height - row_realsize);
            }
            row_tds.height(row_height);
        });

        var contenttbH = mainid.find(".fixedContainer .fixedTable table").height();
        if (contenttbH < maintbheight) {
            mainid.find("." + options.classColumn + " .fixedTable").height(contenttbH + 20);
            mainid.find(".fixedContainer .fixedTable").height(contenttbH + 20);

            mainid.find(".fixedContainer ." + options.classHeader).width(mainid.find(".fixedContainer ." + options.classHeader).width() + 16);
            mainid.find(".fixedContainer ." + options.classFooter).width(mainid.find(".fixedContainer ." + options.classHeader).width());
        }
        else {
            //offset the footer by the height of the scrollbar so that it lines up right.
            mainid.find("." + options.classColumn + " > ." + options.classFooter).css({
                "position": "relative",
                "top": 16
            });
        }
    }

})(jQuery);
