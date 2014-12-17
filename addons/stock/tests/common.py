from openerp.tests import common

class TestStockCommon(common.TransactionCase):

    def setUp(self):
        super(TestStockCommon, self).setUp()

        self.ProductObj = self.env['product.product']
        self.PartnerObj = self.env['res.partner']
        self.ModelDataObj = self.env['ir.model.data']
        self.StockPackObj = self.env['stock.pack.operation']
        self.StockQuantObj = self.env['stock.quant']
        self.PickingObj = self.env['stock.picking']
        self.MoveObj = self.env['stock.move']
        
        # Model Data
        self.partner_agrolite_id = self.ModelDataObj.xmlid_to_res_id('base.res_partner_2')
        self.partner_delta_id = self.ModelDataObj.xmlid_to_res_id('base.res_partner_4')
        self.picking_type_in = self.ModelDataObj.xmlid_to_res_id('stock.picking_type_in')
        self.picking_type_out = self.ModelDataObj.xmlid_to_res_id('stock.picking_type_out')
        self.supplier_location = self.ModelDataObj.xmlid_to_res_id('stock.stock_location_suppliers')
        self.stock_location =    self.ModelDataObj.xmlid_to_res_id('stock.stock_location_stock') 
        self.customer_location = self.ModelDataObj.xmlid_to_res_id('stock.stock_location_customers')
       
        # Product Created A, B, C, D
        self.productA = self.ProductObj.create({'name':'Product A'})
        self.productB = self.ProductObj.create({'name':'Product B'})
        self.productC = self.ProductObj.create({'name':'Product C'})
        self.productD = self.ProductObj.create({'name':'Product D'})

        
        
        

