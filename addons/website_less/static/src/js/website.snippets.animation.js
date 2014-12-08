// Backported from 52ca425

(function () {
    'use strict';

    var website = openerp.website;

    function load_called_snippet () {
        var ids_or_xml_ids = _.uniq($("[data-snippet]").map(function () {return $(this).data('snippet');}).get());
        if (ids_or_xml_ids.length) {
            openerp.jsonRpc('/website/multi_render', 'call', {
                    'ids_or_xml_ids': ids_or_xml_ids
                }).then(function (data) {
                    for (var k in data) {
                        $(data[k]).addClass('o_block_'+k).replace($("[data-snippet='"+k+"']"));
                    }
                });
        }
    }

    $(document).ready(load_called_snippet);
})