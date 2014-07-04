(function () {
    "use strict";
    var website = openerp.website;
    var QWeb = openerp.qweb;

    website.add_template_file('/website_google_search/static/src/xml/website_google_search.xml');

    $(document).ready(function () {
        var $search_box = $('li.google_search_box');
        var $search_results = $('.google_search_results');
        $search_box.on('submit', 'form', function (e) {
            e.preventDefault();
            $.getJSON("https://www.googleapis.com/customsearch/v1", {
                q: $search_box.find('input[name="q"]').val(),
                cx: $search_box.find('input[name="cx"]').val(),
                key: $search_box.find('input[name="key"]').val(),
                num: 10,
            }).done(function (response) {
                var $results = $(QWeb.render('website.google_search.results', {
                    'widget': response
                }));
                $search_results.replaceWith($results);
            }).fail(function (response) {
                var $results = $(QWeb.render('website.google_search.error', {
                    'widget': JSON.parse(response.responseText)
                }));
                $search_results.replaceWith($results);
            });
        });
    });
})();
