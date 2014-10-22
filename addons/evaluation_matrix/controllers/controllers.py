# -*- coding: utf-8 -*-
from openerp import http
from openerp import api
from openerp.api import Environment
from openerp.http import request

class EvaluationMatrix(http.Controller):

    def get_result(self, comparison_factors, comparison_products):
        Comparison_results = http.request.env['comparison_factor_result']
        comparison_results = dict((factor.id, {}) for factor in comparison_factors)
        results = Comparison_results.search([('factor_id', 'in', map(int,comparison_factors)), ('item_id', 'in', map(int,comparison_products))])
        for result in results:
            comparison_results[ result.factor_id.id ][ result.item_id.id ] = int(round(result.result, 0))
        return comparison_results

    def compute_parents(self, cr, factor, item):

        if factor.parent_id:
            Comparison_result =  http.request.env['comparison_factor_result']

            final_score = 0.0

            children_tot_ponderation = 0.0
            for child in factor.parent_id.child_ids:
                children_tot_ponderation += child.ponderation

            all_children = (','.join([str(x.id) for x in factor.parent_id.child_ids]))

            cr.execute("select cfr.result,cf.ponderation from comparison_factor_result as cfr,comparison_factor as cf where cfr.item_id=%s and cfr.votes > 0.0 and cfr.factor_id = cf.id and cf.id in (%s)"%(item.id,all_children))
            res = cr.fetchall()

            if res:
                for record in res:
                    final_score += (record[0] * record[1])

                final_score = final_score / children_tot_ponderation

                parent_result = Comparison_result.search([('factor_id', '=', factor.parent_id.id),('item_id', '=', item.id)])
                parent_result[0]['result'] = final_score
                Comparison_result.write(parent_result[0])

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
            'comparison_categories': comparison_categories,
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
                "type": comp_factor_child.type,
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
            'parent_id' : comparison_factor_id,
        }

    @http.route(['/comparison/create_criterion'], type='json', auth="public", website=True)
    def create_criterion(self, name, note, parent_id):
        Comparison_factor = http.request.env['comparison_factor']

        vals = {'name' : name, 'note' : note,'parent_id' : parent_id}
        Comparison_factor.create(vals)

    @http.route(['/comparison/up_ponderation'], type='json', auth="public", website=True)
    def up_ponderation(self, comparison_factor_id):
        cr = request.cr
        Comparison_factor = http.request.env['comparison_factor']
        Comparison_item = http.request.env['comparison_item']

        comparison_factor = Comparison_factor.browse([(comparison_factor_id)])

        comparison_factor.ponderation += 0.1
        Comparison_factor.write([comparison_factor])
        comparison_items = Comparison_item.search([])
        while(comparison_factor and comparison_factor.parent_id):
            for comparison_item in comparison_items:
                self.compute_parents(cr,comparison_factor,comparison_item)
            comparison_factor = comparison_factor.parent_id

    @http.route(['/comparison/down_ponderation'], type='json', auth="public", website=True)
    def down_ponderation(self, comparison_factor_id):
        cr = request.cr
        Comparison_factor = http.request.env['comparison_factor']
        Comparison_item = http.request.env['comparison_item']

        comparison_factor = Comparison_factor.browse([(comparison_factor_id)])

        if comparison_factor.ponderation >= 0.1:
            comparison_factor.ponderation -= 0.1
            Comparison_factor.write([comparison_factor])
            comparison_items = Comparison_item.search([])
            while(comparison_factor and comparison_factor.parent_id):
                for comparison_item in comparison_items:
                    self.compute_parents(cr,comparison_factor,comparison_item)
                comparison_factor = comparison_factor.parent_id


    @http.route(['/comparison/vote/<value>/<int:factor>/<int:item>/'], type='json', auth='public', website=True)
    def vote(self, value, factor, item):
        Comparison_vote = http.request.env['comparison_vote']
        Comparison_vote_values = http.request.env['comparison_vote_values']
        if value == 'down':
            type_vote = 'Feature Not Available'
        elif value == 'up':
            type_vote = 'Feature Available'
        else:
            type_vote = 'Available From Third Party Product'

        comparison_vote_value = Comparison_vote_values.search([('name','=',type_vote)])

        vals = {'factor_id' : factor, 'item_id' : item, 'score_id' : comparison_vote_value[0]['id'], 'note' : "", 'state' : 'valid'}
        Comparison_vote.create(vals)




    

        
