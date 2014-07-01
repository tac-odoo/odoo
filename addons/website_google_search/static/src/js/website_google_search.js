(function () {
    'use strict';

    var website = openerp.website;

    website.snippet.options['google-search'] = website.snippet.Option.extend({
        start: function () {
            this._super.apply(this, arguments);
            debugger;
        },
    });

})();
