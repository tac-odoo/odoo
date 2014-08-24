from openerp.tests import common


class TestWebsiteVersionBase(common.TransactionCase):

	def setUp(self):
		super(TestWebsiteVersionBase, self).setUp()
        cr, uid = self.cr, self.uid

        # Usefull models
        self.ir_ui_view = self.registry('ir.ui.view')
        self.snapshot = self.registry('website_version.snapshot')
        self.website = self.registry('website')

        #Usefull objects
        master_view_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'website', 'homepage')
        self.master_view_id = master_view_ref and master_view_ref[1] or False
        self.arch_master=self.ir_ui_view.browse(cr, uid, [self.master_view_id], context=None)[0].arch
        snapshot_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'website_version', 'snapshot_0_0_0_0')
        self.snapshot_id = snapshot_ref and snapshot_ref[1] or False
        website_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'website_version', 'second_website')
        self.website_id = website_ref and website_ref[1] or False
        view_0_0_0_0_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'website_version', 'homepage_0_0_0_0')
        self.view_0_0_0_0_id = result_0_0_0_0_ref and result_0_0_0_0_ref[1] or False
        self.arch_0_0_0_0=self.ir_ui_view.browse(cr, uid, [self.view_0_0_0_0_id], context=None)[0].arch