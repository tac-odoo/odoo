# -*- coding: utf-8 -*-

import json

from openerp import models, fields, api, _
import urllib2
import requests

from urlparse import urlparse,parse_qs
from openerp.addons.website.models.website import slug

class ir_attachment_tags(models.Model):
    _name = 'ir.attachment.tag'
    name = fields.Char()

class document_directory(models.Model):
    _name = 'document.directory'
    _inherit = ['document.directory','mail.thread']

    website_published = fields.Boolean(string='Publish', help="Publish on the website", copy=False)
    description = fields.Text(string='Website Description', tranalate=True)
    website_description = fields.Html('Website Description', tranalate=True)
    slide_id = fields.Many2one('ir.attachment', string='Custom Slide')
    promote = fields.Selection([('donot','Do not Promote'), ('latest','Latest Published'), ('mostview','Most Viewed'), ('custom','User Defined')], string="Method", default='donot')

    def get_mostviewed(self):
        attachment = self.env['ir.attachment']
        famous = None
        if self.promote == 'mostview':
            domain = [('website_published', '=', True), ('parent_id','=',self.id)]
            famous = attachment.search(domain, limit=1, offset=0, order="slide_views desc")
        elif self.promote == 'latest':
            domain = [('website_published', '=', True), ('parent_id','=',self.id)]
            famous = attachment.search(domain, limit=1, offset=0, order="write_date desc")
        elif self.promote == 'custom':
                famous = self.slide_id
        return famous

class MailMessage(models.Model):
    _inherit = 'mail.message'

    path = fields.Char(
            string='Discussion Path', select=1,
            help='Used to display messages in a paragraph-based chatter using a unique path;')
            
class ir_attachment(models.Model):
    _name = 'ir.attachment'
    _inherit = ['ir.attachment','mail.thread']
    _order = "id desc"

    is_slide = fields.Boolean(string='Is Slide')
    slide_type = fields.Selection([('infographic','Infographic'), ('presentation', 'Presentation'), ('document', 'Document'), ('video', 'Video')], string='Type')
    tag_ids = fields.Many2many('ir.attachment.tag', 'rel_attachments_tags', 'attachment_id', 'tag_id', string='Tags')
    image = fields.Binary('Thumb')
    slide_views = fields.Integer(string='Number of Views', default=0)
    youtube_id = fields.Char(string="Youtube Video ID")
    website_published = fields.Boolean(
        string='Publish', help="Publish on the website", copy=False,
    )
    website_message_ids = fields.One2many(
        'mail.message', 'res_id',
        domain=lambda self: [
            '&', '&', ('model', '=', self._name), ('type', '=', 'comment'), ('path', '=', False)
        ],
        string='Website Messages', default=False,
        help="Website communication history",
    )
    website_description = fields.Html('Website Description', tranalate=True)
    likes = fields.Integer(string='Likes', default=0)
    dislikes = fields.Integer(string='Dislikes', default=0)

    def _get_share_url(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        shareurl = "%s/%s/%s/%s" % (base_url, slug(self.parent_id), self.slide_type, slug(self))
        return shareurl
    
    def _get_embade_code(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        embedcode = False
        if self.datas and not self.youtube_id:
            embedcode = '<iframe  src="%s/website_slides/static/lib/pdfjs/web/viewer.html?file=%s#page="></iframe>' % (base_url, self.url)
        if self.youtube_id:
            embedcode = '<iframe src="//www.youtube.com/embed/%s?theme=light"></iframe>' % (self.youtube_id)
        return embedcode

    def set_viewed(self):
        self._cr.execute("""UPDATE ir_attachment SET slide_views = slide_views+1 WHERE id IN %s""", (self._ids,))
        return True

    def set_like(self):
        self._cr.execute("""UPDATE ir_attachment SET likes = likes+1 WHERE id IN %s""", (self._ids,))
        return True

    def set_dislike(self):
        self._cr.execute("""UPDATE ir_attachment SET dislikes = dislikes+1 WHERE id IN %s""", (self._ids,))
        return True

    def notify_published(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        if not self.website_published:
            return False

        body = _(
            '<p>A new presentation <i>%s</i> has been published under %s channel. <a href="%s/channel/%s/%s/view/%s">Click here to access the presentation.</a></p>' %
            (self.name, self.parent_id.name, base_url, slug(self.parent_id), self.slide_type, slug(self))
        )
        partner_ids = []
        for partner in self.parent_id.message_follower_ids:
            partner_ids.append(partner.id)
        self.parent_id.message_post(subject=self.name, body=body, subtype='website_slide.new_slides', partner_ids=partner_ids)

    def notify_request_to_approve(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')

        body = _(
            '<p>A new presentation <i>%s</i> has been uplodated under %s channel andwaiting for your review. <a href="%s/channel/%s/%s/view/%s">Click here to review the presentation.</a></p>' %
            (self.name, self.parent_id.name, base_url, slug(self.parent_id), self.slide_type, slug(self))
        )
        #Todo: fix me, search only people subscribe for new_slides_validation
        partner_ids = []
        for partner in self.parent_id.message_follower_ids:
            partner_ids.append(partner.id)
        self.parent_id.message_post(subject=self.name, body=body, subtype='website_slide.new_slides_validation', partner_ids=partner_ids)
    
    @api.multi
    def write(self, values):
        if values.get('url'):
            values = self.update_youtube(values)
        success = super(ir_attachment, self).write(values)
        for slide_id in self:
            self.notify_published()
        return success
    
    def update_youtube(self, values):
        values["youtube_id"] = self.extract_youtube_id(values['url'].strip())
        statistics = self.youtube_statistics(values["youtube_id"])
        if statistics:
            if statistics['items'][0].get('snippet') :
                if statistics['items'][0]['snippet'].get('thumbnails'):
                    image_url = statistics['items'][0]['snippet']['thumbnails']['medium']['url']
                    response = requests.get(image_url)
                    if response:
                        values['image'] = response.content.encode('base64')
                if statistics['items'][0]['snippet'].get('description'):
                        values['description'] = statistics['items'][0]['snippet'].get('description')
            if statistics['items'][0].get('statistics'):
                values['slide_views'] = statistics['items'][0]['statistics']['viewCount']
        return values
    
    @api.model
    def create(self, values):
        if values.get('is_slide'):
            if values.get('datas_fname'):
                values['url'] = "/website_slides/" + values['datas_fname']
            elif values.get('url'):
                values = self.update_youtube(values)

        values['website_published'] = False
        slide_id = super(ir_attachment, self).create(values)
        slide_id.notify_request_to_approve()
        slide_id.notify_published()
        return slide_id

    def extract_youtube_id(self, url):
        youtube_id = ""
        query = urlparse(url)
        if query.hostname == 'youtu.be':
            youtube_id = query.path[1:]
        elif query.hostname in ('www.youtube.com', 'youtube.com'):
            if query.path == '/watch':
                p = parse_qs(query.query)
                youtube_id = p['v'][0]
            elif query.path[:7] == '/embed/':
                youtube_id = query.path.split('/')[2]
            elif query.path[:3] == '/v/':
                youtube_id = query.path.split('/')[2]
        return youtube_id

    def youtube_statistics(self, video_id):
        request_url = "https://www.googleapis.com/youtube/v3/videos?id=%s&key=AIzaSyBKDzf7KjjZqwPWAME6JOeHzzBlq9nrpjk&part=snippet,statistics&fields=items(id,snippet,statistics)" % (video_id)
        try:
            req = urllib2.Request(request_url)
            content = urllib2.urlopen(req).read()
        except urllib2.HTTPError:
            return False
        return json.loads(content)