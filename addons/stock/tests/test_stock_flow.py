from openerp.addons.stock.tests.common import TestStockCommon
from openerp.exceptions import AccessError, ValidationError, Warning
from openerp.tools import mute_logger

class TestStockFlow(TestStockCommon):

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_00_picking_create_and_trasfer_value(self):
        """ Basic stock operation on incoming product and outgoing product."""
        LotObj = self.env['stock.production.lot']

        # ----------------------------------------------------------------------
        # Create incoming shipment of product A, B, C, D:
        # ----------------------------------------------------------------------
        #   Product A ( 1 Unit ) , Product C ( 10 Unit )
        #   Product B ( 1 Unit ) , Product D ( 10 Unit )
        #   Product D ( 5 Unit )
        # ----------------------------------------------------------------------

        picking_in = self.PickingObj.create({
            'partner_id': self.partner_delta_id, 
            'picking_type_id':self.picking_type_in})
        self.MoveObj.create({
            'name': self.productA.name,
            'product_id':self.productA.id, 
            'product_uom_qty': 1,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        self.MoveObj.create({
            'name': self.productB.name,
            'product_id':self.productB.id, 
            'product_uom_qty': 1,
            'product_uom': self.productB.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        self.MoveObj.create({
            'name': self.productC.name,
            'product_id':self.productC.id, 
            'product_uom_qty': 10,
            'product_uom': self.productC.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        self.MoveObj.create({
            'name': self.productD.name,
            'product_id':self.productD.id, 
            'product_uom_qty': 10,
            'product_uom': self.productD.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        self.MoveObj.create({
            'name': self.productD.name,
            'product_id':self.productD.id, 
            'product_uom_qty': 5,
            'product_uom': self.productD.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        # Check incoming shipment move lines state.
        for move in picking_in.move_lines:
            self.assertEqual(move.state, 'draft','Move state must be draft.')
        # Confirm incoming shipment.
        picking_in.action_confirm()
        # Check incoming shipment move lines state.
        for move in picking_in.move_lines:
            self.assertEqual(move.state, 'assigned','Move state must be draft.')
        # -------------------------------------
        # Replace pack operation of incoming shipments.
        # ---------------------------------------
        picking_in.do_prepare_partial()
        self.StockPackObj.search([('product_id', '=', self.productA.id), ('picking_id', '=', picking_in.id)]).write({
        'product_qty': 4.0})
        self.StockPackObj.search([('product_id', '=', self.productB.id), ('picking_id', '=', picking_in.id)]).write({
        'product_qty': 5.0})
        self.StockPackObj.search([('product_id', '=', self.productC.id), ('picking_id', '=', picking_in.id)]).write({
        'product_qty': 5.0})
        self.StockPackObj.search([('product_id', '=', self.productD.id), ('picking_id', '=', picking_in.id)]).write({
        'product_qty': 5.0})
        lot2_productC = LotObj.create({'name': 'C Lot 2', 'product_id': self.productC.id})
        self.StockPackObj.create({
                    'product_id': self.productC.id, 
                    'product_qty': 2,
                    'product_uom_id': self.productC.uom_id.id,
                    'location_id': self.supplier_location,
                    'location_dest_id': self.stock_location, 
                    'picking_id': picking_in.id,
                    'lot_id': lot2_productC.id})
        self.StockPackObj.create({
                    'product_id': self.productD.id, 
                    'product_qty': 2,
                    'product_uom_id': self.productD.uom_id.id,
                    'location_id': self.supplier_location,
                    'location_dest_id': self.stock_location, 
                    'picking_id': picking_in.id})
        # Check incoming shipment total quantity of pack operation
        packs = self.StockPackObj.search([('picking_id', '=', picking_in.id)])
        total_qty = [ pack.product_qty for pack in packs]
        self.assertEqual(sum(total_qty), 23, 'Invalid total quantity of pack operation.')
        # Transfer quantity of Incoming Shipment.
        picking_in.do_transfer()
        # Check total no of move lines of incoming shipment. 
        self.assertEqual(len(picking_in.move_lines), 6, 'Moves must be 6.')
        # Check incoming shipment state.
        self.assertEqual(picking_in.state, 'done', 'Picking state should be done.')
        # Check incoming shipment move lines state.
        for move in picking_in.move_lines:
            self.assertEqual(move.state, 'done', 'All moves state must be done.')
        # Check product A done quantity must be 3 and 1
        moves_product_a = self.MoveObj.search([('product_id', '=', self.productA.id), ('picking_id', '=', picking_in.id)]) 
        a_done_qty  = [move.product_uom_qty for move in moves_product_a]
        self.assertEqual(set(a_done_qty), set([1.0, 3.0]), 'Product A should have done 3 and 1 quantity.')
        # Check product B done quantity must be 4 and 1
        product_b_moves = self.MoveObj.search([('product_id', '=', self.productB.id), ('picking_id', '=', picking_in.id)]) 
        b_done_qty  = [move.product_uom_qty for move in product_b_moves]
        self.assertEqual(set(b_done_qty), set([4.0, 1.0]), 'Product B should have done 4 and 1 quantity.')
        # Check product C done quantity must be 7
        c_done_qty = self.MoveObj.search([('product_id', '=', self.productC.id), ('picking_id', '=', picking_in.id)], limit=1).product_uom_qty
        self.assertEqual(c_done_qty, 7.0, 'Incoming .')
        # Check product D done quantity must be 7
        d_done_qty = self.MoveObj.search([('product_id', '=', self.productD.id), ('picking_id', '=', picking_in.id)], limit=1).product_uom_qty
        self.assertEqual(d_done_qty, 7.0, 'Product D should have done 7 quantity.')

        # ----------------------------------------------------------------------
        # Back order of Incoming shipment.
        # ----------------------------------------------------------------------

        # Check back order created or not.
        back_order_in = self.PickingObj.search([('backorder_id', '=', picking_in.id)])
        self.assertEqual(len(back_order_in), 1, 'Back order should be created.')
        # Check total move lines of back order.
        self.assertEqual(len(back_order_in.move_lines), 3, 'Back order should be created with 3 move lines..') 
        # Check back order should be created with 3 quantity of product C.
        moves_prod_c = self.MoveObj.search([('product_id', '=', self.productC.id), ('picking_id', '=', back_order_in.id)])
        prodcut_c_qty = [move.product_uom_qty for move in moves_prod_c] 
        self.assertEqual(sum(prodcut_c_qty), 3.0, 'back order should be create for Product C with 3 quantity.')
        # Check back order should be created with 8 quantity of product D.
        moves_prod_d = self.MoveObj.search([('product_id', '=', self.productD.id), ('picking_id', '=', back_order_in.id)])
        prodcut_d_qty = [move.product_uom_qty for move in moves_prod_d] 
        self.assertEqual(sum(prodcut_d_qty), 8.0, 'back order should be create for Product D with 8 quantity.')

        # ==============================================
        # Create Outgoing shipment with ...
        #   product A ( 10 Unit ) , product B ( 5 Unit )  
        #   product C (  3 unit ) , product D ( 10 Unit )
        # ==============================================
        
        picking_out = self.PickingObj.create({
            'partner_id': self.partner_agrolite_id, 
            'picking_type_id':self.picking_type_out})
        self.MoveObj.create({
            'name': self.productA.name,
            'product_id':self.productA.id, 
            'product_uom_qty': 10,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        self.MoveObj.create({
            'name': self.productB.name,
            'product_id':self.productB.id, 
            'product_uom_qty': 5,
            'product_uom': self.productB.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location}) 
        self.MoveObj.create({
            'name': self.productC.name,
            'product_id': self.productC.id, 
            'product_uom_qty': 3,
            'product_uom': self.productC.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        self.MoveObj.create({
            'name': self.productD.name,
            'product_id':self. productD.id, 
            'product_uom_qty': 10,
            'product_uom': self.productD.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        
        # Confirm outgoing shipment.
        picking_out.action_confirm()
        for move in picking_out.move_lines:
            self.assertEqual(move.state, 'confirmed','Move state must be draft.')
        # Assing product to outgoing shipments
        picking_out.action_assign()
        for move in picking_out.move_lines:
            self.assertEqual(move.state, 'assigned','Move state must be draft.')
        # Check product A available quantity
        aval_a_qty = self.MoveObj.search([('product_id', '=', self.productA.id), ('picking_id', '=', picking_out.id)], limit=1).availability
        self.assertEqual(aval_a_qty, 4.0, 'Should have 4 available quantity.')
        # Check product B available quantity
        aval_b_qty = self.MoveObj.search([('product_id', '=', self.productB.id), ('picking_id', '=', picking_out.id)], limit=1).availability
        self.assertEqual(aval_b_qty, 5.0, 'Should have 5 available quantity.')
        # Check product C available quantity
        aval_c_qty = self.MoveObj.search([('product_id', '=', self.productC.id), ('picking_id', '=', picking_out.id)], limit=1).availability
        self.assertEqual(aval_c_qty, 3.0, 'Should have 3 available quantity.')
        # Check product D available quantity
        aval_d_qty = self.MoveObj.search([('product_id', '=', self.productD.id), ('picking_id', '=', picking_out.id)], limit=1).availability
        self.assertEqual(aval_d_qty, 7.0, 'Should have 7 available quantity.')

        # -----------------------
        # Create partial picking.
        #------------------------

        picking_out.do_prepare_partial()
        self.StockPackObj.search([('product_id', '=', self.productA.id), ('picking_id', '=', picking_out.id)]).write({
        'product_qty': 2.0})
        self.StockPackObj.search([('product_id', '=', self.productB.id), ('picking_id', '=', picking_out.id)]).write({
        'product_qty': 3.0})
        self.StockPackObj.create({
                    'product_id': self.productB.id, 
                    'product_qty': 2,
                    'product_uom_id': self.productB.uom_id.id,
                    'location_id': self.stock_location,
                    'location_dest_id': self.customer_location, 
                    'picking_id': picking_out.id})
        self.StockPackObj.search([('product_id', '=', self.productC.id), ('picking_id', '=', picking_out.id)]).write({
        'product_qty': 2.0, 'lot_id': lot2_productC.id})
        self.StockPackObj.create({
                    'product_id': self.productC.id, 
                    'product_qty': 3,
                    'product_uom_id': self.productC.uom_id.id,
                    'location_id': self.stock_location,
                    'location_dest_id': self.customer_location, 
                    'picking_id': picking_out.id})
        self.StockPackObj.search([('product_id', '=', self.productD.id), ('picking_id', '=', picking_out.id)]).write({
        'product_qty': 6.0})

        # Transfer picking.
        picking_out.do_transfer()
        
        # ----------------------------------------------------------------------
        # Check Outgoing shipment status and done move quantity.
        # ----------------------------------------------------------------------

        # check outgoing shipment status.
        self.assertEqual(picking_out.state, 'done', 'All moves state must be done.')
        # check outgoing shipment total moves and and its state.
        self.assertEqual(len(picking_out.move_lines), 5, 'done move should be 5')
        for move in picking_out.move_lines:
            self.assertEqual(move.state, 'done', 'All moves state must be done.')
        back_order_out = self.PickingObj.search([('backorder_id', '=', picking_out.id)])
        # Check back order created or not.
        self.assertEqual(len(back_order_out), 1, 'Back order should be created.')
        # Check total move lines of back order.
        self.assertEqual(len(back_order_out.move_lines), 2, 'Back order should have 2 move lines.') 
        # Check back order should be created with 8 quantity of product A.
        product_a_qty = self.MoveObj.search([('product_id', '=', self.productA.id), ('picking_id', '=', back_order_out.id)], limit=1).product_uom_qty
        self.assertEqual(product_a_qty, 8.0, 'Back order should have 8 quantity of product A.')
        # Check back order should be created with 4 quantity of product D.
        product_d_qty = self.MoveObj.search([('product_id', '=', self.productD.id), ('picking_id', '=', back_order_out.id)], limit=1).product_uom_qty
        self.assertEqual(product_d_qty, 4.0, 'Back order should have 8 quantity of product D.')
        
        #-----------------------------------------------------------------------
        # Check quant and quantity available of product A, B, C, D 
        #-----------------------------------------------------------------------

        # Check quant and available quantity for product A
        product_a_quant = self.StockQuantObj.search([('product_id', '=', self.productA.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.qty for quant in product_a_quant]
        self.assertEqual(sum(total_qty), 2.0, 'Total stock location quantity for product A should be 2.')
        self.assertEqual(self.productA.qty_available , 2.0, 'Product A should have 2 quantity available.')
        # Check quant and available quantity for product B
        product_b_quant = self.StockQuantObj.search([('product_id', '=', self.productB.id), ('location_id', '=', self.stock_location)])
        self.assertFalse(product_b_quant, 'No quant should found as outgoing shipment took everything out of stock.')
        self.assertEqual(self.productB.qty_available , 0.0, 'Product B should have zero quantity available.')
        # Check quant and available quantity for product C
        product_c_quant = self.StockQuantObj.search([('product_id', '=', self.productC.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.qty for quant in product_c_quant]
        self.assertEqual(sum(total_qty), 2.0, 'Total stock location quantity for product C should be 2.')
        self.assertEqual(self.productC.qty_available , 2.0, 'Product C should have 2 quantity available.')
        # Check quant and available quantity for product D
        product_d_quant = self.StockQuantObj.search([('product_id', '=', self.productD.id), ('location_id', '=', self.stock_location)], limit=1)
        self.assertEqual(product_d_quant.qty, 1.0, 'Total stock location quantity for product D should be 1.')
        self.assertEqual(self.productD.qty_available , 1.0, 'Product D should have 1 quantity available.')
        
        #-----------------------------------------------------------------------
        # Back Order of Incoming shipment 
        #-----------------------------------------------------------------------
      
        lot3_productC = LotObj.create({'name': 'Lot 3', 'product_id': self.productC.id})
        lot4_productC = LotObj.create({'name': 'Lot 4', 'product_id': self.productC.id})
        lot5_productC = LotObj.create({'name': 'Lot 5', 'product_id': self.productC.id})
        lot6_productC = LotObj.create({'name': 'Lot 6', 'product_id': self.productC.id})
        lot1_productD = LotObj.create({'name': 'Lot 1', 'product_id': self.productD.id})
        lot2_productD = LotObj.create({'name': 'Lot 2', 'product_id': self.productD.id})

        # Confirm back order of incoming shipment.
        back_order_in.action_confirm()
        self.assertEqual(back_order_in.state, 'assigned', 'Back order of incoming shipment state should be assigned.')
        for move in back_order_in.move_lines:
            self.assertEqual(move.state, 'assigned', 'Move state must be assigned.')

        # Partial picking 
        back_order_in.do_prepare_partial()
        pack_prod_d = self.StockPackObj.search([('product_id', '=', self.productD.id), ('picking_id', '=', back_order_in.id)])
        self.assertEqual(len(pack_prod_d), 1, 'Back order should have 1 pack of product D.')
        pack_prod_d.write({'product_qty': 4, 'lot_id': lot1_productD.id})
        self.StockPackObj.create({
                    'product_id': self.productD.id, 
                    'product_qty': 4,
                    'product_uom_id': self.productD.uom_id.id,
                    'location_id': self.supplier_location,
                    'location_dest_id': self.stock_location,
                    'picking_id': back_order_in.id,
                    'lot_id':  lot2_productD.id})
        pack_prod_c = self.StockPackObj.search([('product_id', '=', self.productC.id), ('picking_id', '=', back_order_in.id)], limit=1).write({'product_qty': 1, 'lot_id': lot3_productC.id})
        self.StockPackObj.create({
                    'product_id': self.productC.id, 
                    'product_qty': 1,
                    'product_uom_id': self.productC.uom_id.id,
                    'location_id': self.supplier_location,
                    'location_dest_id': self.stock_location, 
                    'picking_id': back_order_in.id,
                    'lot_id': lot4_productC.id})
        self.StockPackObj.create({
                    'product_id': self.productC.id, 
                    'product_qty': 2,
                    'product_uom_id': self.productC.uom_id.id,
                    'location_id': self.supplier_location,
                    'location_dest_id': self.stock_location, 
                    'picking_id': back_order_in.id,
                    'lot_id': lot5_productC.id})
        self.StockPackObj.create({
                    'product_id': self.productC.id, 
                    'product_qty': 2,
                    'product_uom_id': self.productC.uom_id.id,
                    'location_id': self.supplier_location,
                    'location_dest_id': self.stock_location, 
                    'picking_id': back_order_in.id,
                    'lot_id': lot6_productC.id})
        self.StockPackObj.create({
                    'product_id': self.productA.id, 
                    'product_qty': 10,
                    'product_uom_id': self.productA.uom_id.id,
                    'location_id': self.supplier_location,
                    'location_dest_id': self.stock_location, 
                    'picking_id': back_order_in.id})
        back_order_in.do_transfer()
        # Check total no of move lines. 
        self.assertEqual(len(back_order_in.move_lines), 6, 'Done moves must be 6.')
        # Check incoming shipment state must be 'Done'. 
        self.assertEqual(back_order_in.state, 'done', 'Back order of incoming shipment state should be done.')
        # Check incoming shipment move lines state must be 'Done'.
        for move in back_order_in.move_lines:
            self.assertEqual(move.state, 'done', 'All move line state should be done.')
        # Check product A done quantity must be 10
        product_a_moves = self.MoveObj.search([('product_id', '=', self.productA.id), ('picking_id', '=', back_order_in.id)]) 
        self.assertEqual(product_a_moves.product_uom_qty, 10, 'Product A should have 10 done quantity.')
        # Check product C done quantity must be 3.0, 1.0, 2.0 
        product_c_moves = self.MoveObj.search([('product_id', '=', self.productC.id), ('picking_id', '=', back_order_in.id)]) 
        c_done_qty  = [move.product_uom_qty for move in product_c_moves]
        self.assertEqual(set(c_done_qty), set([3.0, 1.0, 2.0]), 'Product C should have (3.0, 1.0, 2.0) done quantity.')
        # Check product D done quantity must be 5.0 and 3.0
        product_d_moves = self.MoveObj.search([('product_id', '=', self.productD.id), ('picking_id', '=', back_order_in.id)]) 
        d_done_qty  = [move.product_uom_qty for move in product_d_moves]
        self.assertEqual(set(d_done_qty), set([3.0, 5.0]), 'Product D should have 3 and 5 done quantity.')
        # Check no back order is created.  
        self.assertFalse(self.PickingObj.search([('backorder_id', '=', back_order_in.id)]), "Should not create any back order.")

        #-----------------------------------------------------------------------
        # Check quant and quantity available of product A, B, C, D 
        #-----------------------------------------------------------------------

        # Check quant and available quantity for product A
        product_a_quant = self.StockQuantObj.search([('product_id', '=', self.productA.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.qty for quant in product_a_quant]
        self.assertEqual(sum(total_qty), 12.0, 'Total stock location quantity for product A should be 12.')
        self.assertEqual(self.productA.qty_available , 12.0, 'Product A should have 12 quantity available.')
        # Check quant and available quantity for product B
        product_b_quant = self.StockQuantObj.search([('product_id', '=', self.productB.id), ('location_id', '=', self.stock_location)])
        self.assertFalse(product_b_quant, 'No quant should found as outgoing shipment took everything out of stock')
        self.assertEqual(self.productB.qty_available , 0.0, 'Product B should have zero quantity available.')
        # Check quant and available quantity for product C
        product_c_quant = self.StockQuantObj.search([('product_id', '=', self.productC.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.qty for quant in product_c_quant]
        self.assertEqual(sum(total_qty), 8.0, 'Total stock location quantity for product C should be 8.')
        self.assertEqual(self.productC.qty_available , 8.0, 'Product C should have 8 quantity available')
        # Check quant and available quantity for product D
        product_d_quant = self.StockQuantObj.search([('product_id', '=', self.productD.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.qty for quant in product_d_quant]
        self.assertEqual(sum(total_qty), 9.0, 'Total stock location quantity for product D should be 9.')
        self.assertEqual(self.productD.qty_available , 9.0, 'Product D should have 9 quantity available.')
        
        #-----------------------------------------------------------------------
        # Back order of Outgoing shipment
        # ----------------------------------------------------------------------

        back_order_out.do_prepare_partial()
        back_order_out.do_transfer()
        
        
        
            
            
        
        
        
        
        

        
        
        
        
                
        
        
        
        

        



        
        
        

        
    
        
        
        
        
        
            
        
        

             
          
       

        
     


