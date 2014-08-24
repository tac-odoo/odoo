from openerp.addons.website_version.tests.test_website_version_base import TestWebsiteVersionBase
from openerp.exceptions import AccessError
from openerp.tools import mute_logger



class TestWebsiteVersiontRead(TestProjectBase):

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_00_website_version_with_right_context(self):
        """ Testing Read with context """
        cr, uid, view_id, snapshot_id= self.cr, self.uid, self.view_id, self.snapshot_id


        # ProjectUser: set project as template -> raise

        result = self.ir_ui_view.read(self, cr, uid, [view_id], fields=None, context={'snapshot_id':snapshot_id}, load='_classic_read')
        arch = """<t name="Homepage" priority="29" t-name="website.homepage">
				  <t t-call="website.layout">
				    <div id="wrap" class="oe_structure oe_empty">
				      <div class="carousel slide mb32" id="myCarousel0" style="height: 320px;">
				        <ol class="carousel-indicators hidden">
				          <li class="active" data-slide-to="0" data-target="#myCarousel0"/>
				        </ol>
				        <div class="carousel-inner">
				          <div class="item image_text oe_img_bg active" style="background-image: url(http://0.0.0.0:8069/website/static/src/img/banner/mountains.jpg);">
				            <div class="container">
				              <div class="row content">
				                <div class="carousel-content col-md-6 col-sm-12">
				                  <h2>Snapshot 0.0.0.0</h2>
				                  <h3>Click to customize this text</h3>
				                  <p>
				                    <a class="btn btn-success btn-large" href="/page/website.contactus">Contact us</a>
				                  </p>
				                </div>
				                <span class="carousel-img col-md-6 hidden-sm hidden-xs"> </span>
				              </div>
				            </div>
				          </div>
				        </div>
				        <div class="carousel-control left hidden" data-slide="prev" data-target="#myCarousel0" href="#myCarousel0" style="width: 10%">
				          <i class="fa fa-chevron-left"/>
				        </div>
				        <div class="carousel-control right hidden" data-slide="next" data-target="#myCarousel0" href="#myCarousel0" style="width: 10%">
				          <i class="fa fa-chevron-right"/>
				        </div>
				      </div>
				    </div>
				  </t>
				</t>"""


        self.assertEqual(result[0]['arch'], arch, 'project: set_template: project tasks should have been set inactive')