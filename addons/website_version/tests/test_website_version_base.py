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
        view_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'website', 'homepage')
        self.view_id = view_ref and view_ref[1] or False
        snapshot_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'website_version', 'snapshot_0_0_0_0')
        self.snapshot_id = snapshot_ref and snapshot_ref[1] or False
        website_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'website_version', 'second_website')
        self.website_id = website_ref and website_ref[1] or False
        result_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'website_version', 'homepage_0_0_0_0')
        result_id = result_ref and result_ref[1] or False
        self.arch=self.ir_ui_view.browse(cr, uid, [result_id], context=None)[0].arch