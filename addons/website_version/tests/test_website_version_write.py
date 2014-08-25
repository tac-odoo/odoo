from openerp.addons.website_version.tests.test_website_version_base import TestWebsiteVersionBase

class TestWebsiteVersionWrite(TestProjectBase):

    def test_write_with_right_context(self):
        """ Testing Write with right context """
        cr, uid, master_view_id, self.view_0_0_0_0_id, snapshot_id, vals= self.cr, self.uid, self.master_view_id, self.view_0_0_0_0_id self.snapshot_id, self.vals

        self.ir_ui_view.write(self, cr, uid, [master_view_id], vals, context={'snapshot_id':snapshot_id})
        view_0_0_0_0 = self.browse(self, cr, uid, [view_0_0_0_0_id], context={'snapshot_id':snapshot_id})[0]
        self.assertEqual(view_0_0_0_0.arch, vals['arch'], 'website_version: write: website_version must write (write test) on the homepage_0_0_0_0 which is in the snapshot_0_0_0_0')

    def test_write_without_context(self):
        """ Testing Write without context """
        cr, uid, master_view_id, self.view_0_0_0_0_id, snapshot_id, vals= self.cr, self.uid, self.master_view_id, self.view_0_0_0_0_id self.snapshot_id, self.vals

        self.ir_ui_view.write(self, cr, uid, [master_view_id], vals, context=None)
        view_master = self.browse(self, cr, uid, [master_view_id], context=None)[0]
        self.assertEqual(view_master.arch, vals['arch'], 'website_version: write: website_version must write (write test) on the homepage which is in master')

    def test_write_with_wrong_context(self):
    	""" Testing Write with wrong context """
    	cr, uid, master_view_id, self.view_0_0_0_0_id, snapshot_id, vals= self.cr, self.uid, self.master_view_id, self.view_0_0_0_0_id self.snapshot_id, self.vals

        self.ir_ui_view.write(self, cr, uid, [master_view_id], vals, context={'snapshot_id':1234})
        view_master = self.browse(self, cr, uid, [master_view_id], context=None)[0]
        self.assertEqual(view_master.arch, vals['arch'], 'website_version: write: website_version must write (write test) on the homepage which is in master')