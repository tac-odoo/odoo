# -*- coding: utf-8 -*-
from openerp import http
from openerp.addons.web.http import request
from openerp import SUPERUSER_ID

class EvaluationMatrix(http.Controller):
    @http.route('/comparison/selection/', auth='public', website=True)
    def index(self, **kwargs):
    	Comparison_products = http.request.env['comparison_item']
        Comparison_factor = http.request.env['comparison_factor']
    	return http.request.render('evaluation_matrix.index', {})

    def get_result(self, comparison_factors, comparison_products):
        Comparison_results = http.request.env['comparison_factor_result']
        comparison_results = dict((factor.id, {}) for factor in comparison_factors)
        results = Comparison_results.search([('factor_id', 'in', map(int,comparison_factors)), ('item_id', 'in', map(int,comparison_products))])
        for result in results:
            comparison_results[ result.factor_id.id ][ result.item_id.id ] = int(round(result.result, 0))
        return comparison_results

    @http.route(['/comparison',
                 '/comparison/<first_product>',
                 '/comparison/<first_product>/<second_product>',
                 '/comparison/<first_product>/<second_product>/<third_product>',
                ], auth='public', website=True)
    def comparison_all(self, first_product=None, second_product=None, third_product=None, **kwargs): #params = products to compare
        Comparison_product = http.request.env['comparison_item']
        Comparison_factor = http.request.env['comparison_factor']

        domain = [('load_default','=',True)]
        if first_product or second_product or third_product:
            domain = ['|','|',('name','=',first_product),('name','=',second_product),('name','=',third_product)]
        
        comparison_products = Comparison_product.search(domain, limit=3)
        comparison_categories = Comparison_factor.search([('parent_id','=', False)])

        comparison_factors = []
        for comparison_category in comparison_categories:
            comparison_factors.append(comparison_category)
            for factor in comparison_category.child_ids:
                comparison_factors.append(factor)

        comparison_results = self.get_result(comparison_factors, comparison_products)

        return http.request.render('evaluation_matrix.comparison', {
            'comparison_factors': comparison_factors,
            'comparison_products': comparison_products,
            'comparison_results': comparison_results,
        })

    @http.route(['/comparison/load_children'], type='json', auth="public", website=True)
    def load_children(self, comparison_factor_id, comparison_products, **post):
        Comparison_factor = http.request.env['comparison_factor']
        
        comp_factor_childs = Comparison_factor.search([('parent_id','=',comparison_factor_id)])
        comparison_results = self.get_result(comp_factor_childs, comparison_products)
        
        comp_factor_children = []
        for comp_factor_child in comp_factor_childs:
            comp_factor_children.append({
                "id": comp_factor_child.id,
                "name": comp_factor_child.name,
                "ponderation": comp_factor_child.ponderation,
                "child_ids": map(int, comp_factor_child.child_ids),
                "parent_id": comparison_factor_id,
                "comparison_results": comparison_results,
            })

        comp_products = []
        for comparison_product in comparison_products:
            comp_products.append({
                "id": comparison_product,
            })

        
        return {
            'comp_factor_children' : comp_factor_children,
            'comparison_results' : comparison_results,
            'comparison_products' : comp_products,
        }

        
