
(function() {
    "use strict";

    var instance = openerp;
    instance.point_of_sale = {};

    instance.web.client_actions.add('pos.ui', 'instance.point_of_sale.PosWidget');
})();

    
