from openerp.addons.website_version.tests.test_website_version_base import TestWebsiteVersionBase

class TestWebsiteVersionCopySnapshot(TestProjectBase):

    def test_copy_snapshot(self):
        """ Testing Snapshot_copy"""
        cr, uid, self.view_0_0_0_0_id, snapshot_id, website_id = self.cr, self.uid, self.view_0_0_0_0_id, self.snapshot_id, self.website_id

        new_snapshot_id = self.snapshot.create(cr, uid,{'name':'copy_snapshot_0_0_0_0', 'website_id':website_id}, context=context)
        self.ir_ui_view.copy_snapshot(cr, uid, snapshot_id,new_snapshot_id,context=context)
        new_snapshot = self.browse(self, cr, uid, [new_snapshot_id], context=None)[0]
        view_copy_snapshot=new_snapshot.view_ids[0]
        view_0_0_0_0 = self.browse(self, cr, uid, [view_0_0_0_0_id], context={'snapshot_id':snapshot_id})[0]
        self.assertEqual(view_copy_snapshot.arch, view_0_0_0_0.arch, 'website_version: copy_snapshot: website_version must have in snpashot_copy the same views then in snapshot_0_0_0_0')
