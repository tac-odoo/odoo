from openerp.addons.website_version.tests.test_website_version_base import TestWebsiteVersionBase

class TestWebsiteVersiontRead(TestProjectBase):

    def test_read_with_right_context(self):
        """ Testing Read with right context """
        cr, uid, master_view_id, snapshot_id, arch_0_0_0_0= self.cr, self.uid, self.master_view_id, self.snapshot_id, self.arch_0_0_0_0

        result = self.ir_ui_view.read(self, cr, uid, [master_view_id], fields=['arch'], context={'snapshot_id':snapshot_id}, load='_classic_read')
        self.assertEqual(result[0]['arch'], arch_0_0_0_0, 'website_version: read: website_version must read the homepage_0_0_0_0 which is in the snapshot_0_0_0_0')

    def test_read_without_context(self):
    	""" Testing Read without context """
    	cr, uid, master_view_id, arch_master = self.cr, self.uid, self.view_id, self.snapshot_id, self.arch_master

    	result = self.ir_ui_view.read(self, cr, uid, [master_view_id], fields=['arch'], context=None, load='_classic_read')
    	self.assertEqual(result[0]['arch'], arch_master, 'website_version: read: website_version must read the homepage which is in master')

    def test_read_with_wrong_context(self):
    	""" Testing Read with wrong context """
    	cr, uid, master_view_id, arch_master, wrong_snapshot_id = self.cr, self.uid, self.view_id, self.snapshot_id, self.arch_master, 1234

    	result = self.ir_ui_view.read(self, cr, uid, [master_view_id], fields=['arch'], context={'snapshot_id':wrong_snapshot_id}, load='_classic_read')
    	self.assertEqual(result[0]['arch'], arch_master, 'website_version: read: website_version must read the homepage which is in master')