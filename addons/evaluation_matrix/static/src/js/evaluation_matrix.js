$(document).ready(function () {
	console.log("JS loaded");

    var qweb = openerp.qweb,
    website = openerp.website;
    website.add_template_file('/evaluation_matrix/static/src/views/evaluation_matrix.xml');

	$('.oe_table-comparison-factors').on('click', '.show-children', function (ev) {
            ev.preventDefault();
            var $elem = $(ev.currentTarget);
            var comparison_factor_id = $elem.attr('comparison-factor');
            var children = $elem.closest("tr").attr('children'); // children are displayed or hidden (hidden by default)
            if(children == "hidden") {
                var products = [];
                $('.oe_comparison-product').each(function() {
                    products.push(parseInt($(this).attr("product-id")));
                });
                openerp.jsonRpc('/comparison/load_children', 'call', {
                    'comparison_factor_id': +comparison_factor_id,
                    'comparison_products': products,
                }).then(function (res) {
                    $('.row_' + comparison_factor_id).after(qweb.render("comparison_factor_children", {'comp_factor_children': res.comp_factor_children, 'comparison_results' : res.comparison_results, 'comparison_products' : res.comparison_products}));
                    $('.row_' + comparison_factor_id).attr('children','displayed');
                });
            }
            else {
                $('.child_row_' + comparison_factor_id).remove();
                $('.row_' + comparison_factor_id).closest("tr").attr('children','hidden');
            }
    });

});