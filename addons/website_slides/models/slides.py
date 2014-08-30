# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import json

import urllib2
import requests

from openerp.tools.translate import _

from openerp.osv import fields, osv
from urlparse import urlparse,parse_qs
from openerp.addons.website.models.website import slug

class ir_attachment_tags(osv.osv):
    _name = 'ir.attachment.tag'
    _columns = {
        'name': fields.char('Name')
    }


class document_directory(osv.osv):
    _name = 'document.directory'
    _inherit = ['document.directory','mail.thread']

    _columns = {
        'website_published': fields.boolean('Publish', help="Publish on the website", copy=False),
        'description': fields.text('Website Description', tranalate=True),
        'website_description': fields.html('Website Description', tranalate=True),
        'slide_id': fields.many2one('ir.attachment', 'Custom Slide'),
        'promote': fields.selection([('donot','Do not Promote'), ('latest','Latest Published'), ('mostview','Most Viewed'), ('custom','User Defined')], string="Method")
    }

    _defaults = {
        'promote': 'donot'
    }

    def get_mostviewed(self, cr, uid, channel, context):
        attachment = self.pool.get('ir.attachment')
        
        famous = None
        if channel.promote == 'mostview':
            domain = [('website_published', '=', True), ('parent_id','=',channel.id)]
            famous_id = attachment._search(cr, uid, domain, limit=1, offset=0, order="slide_views desc", context=context)
            famous = attachment.browse(cr, uid, famous_id, context=context)
        elif channel.promote == 'latest':
            domain = [('website_published', '=', True), ('parent_id','=',channel.id)]
            famous_id = attachment._search(cr, uid, domain, limit=1, offset=0, order="write_date desc", context=context)
            famous = attachment.browse(cr, uid, famous_id, context=context)
        elif channel.promote == 'custom':
                famous = channel.slide_id

        return famous

class MailMessage(osv.Model):
    _inherit = 'mail.message'

    _columns = {
        'path': fields.char(
            'Discussion Path', select=1,
            help='Used to display messages in a paragraph-based chatter using a unique path;'),
    }


class ir_attachment(osv.osv):
    _name = 'ir.attachment'
    _inherit = ['ir.attachment','mail.thread']

    _order = "id desc"
    _columns = {
        'is_slide': fields.boolean('Is Slide'),
        'slide_type': fields.selection([('infographic','Infographic'), ('presentation', 'Presentation'), ('document', 'Document'), ('video', 'Video')], 'Type'),
        'tag_ids': fields.many2many('ir.attachment.tag', 'rel_attachments_tags', 'attachment_id', 'tag_id', 'Tags'),
        'image': fields.binary('Thumb'),
        'slide_views': fields.integer('Number of Views'),
        'youtube_id': fields.char(string="Youtube Video ID"),
        'website_published': fields.boolean(
            'Publish', help="Publish on the website", copy=False,
        ),
        'website_message_ids': fields.one2many(
            'mail.message', 'res_id',
            domain=lambda self: [
                '&', '&', ('model', '=', self._name), ('type', '=', 'comment'), ('path', '=', False)
            ],
            string='Website Messages',
            help="Website communication history",
        ),
        'website_description': fields.html('Website Description', tranalate=True),
        'likes': fields.integer('Likes'),
        'dislikes': fields.integer('Dislikes'),
    }

    def _get_share_url(self, cr, uid, slide, context):
        base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')
        shareurl = "%s/%s/%s/%s" % (base_url, slug(slide.parent_id), slide.slide_type, slug(slide))
        return shareurl

    def _get_embade_code(self, cr, uid, slide, context):
        base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')

        embedcode = False
        if slide.datas and not slide.youtube_id:
            embedcode = '<iframe  src="%s/website_slides/static/lib/pdfjs/web/viewer.html?file=%s#page="></iframe>' % (base_url, slide.url)
        if slide.youtube_id:
            embedcode = '<iframe src="//www.youtube.com/embed/%s?theme=light"></iframe>' % (slide.youtube_id)

        return embedcode

    def _get_slide_setting(self, cr, uid, context):
        return context.get('is_slide', False)

    def _get_slide_type(self, cr, uid, context):
        return context.get('slide_type', 'presentation')

    def _get_slide_views(self, cr, uid, context):
        return context.get('slide_views', 0)

    def get_default_channel(self, cr, uid, context):
        directory = self.pool.get('document.directory')
        vals = directory.search(cr, uid, [('name','=','Documents')])
        return vals

    _defaults = {
        'is_slide': _get_slide_setting,
        'slide_type':_get_slide_type,
        'slide_views':_get_slide_views,
        'likes': 0,
        'dislikes':0,
        'website_published':False
    }

    def set_viewed(self, cr, uid, ids, context=None):
        cr.execute("""UPDATE ir_attachment SET slide_views = slide_views+1 WHERE id IN %s""", (tuple(ids),))
        return True

    def trim_lines(self, cr, uid, description, *args):
        return '<br/>'.join(description.split('\n')[0:14])

    def notify_published(self, cr, uid, slide_id, context):
        base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')
        slide = self.browse(cr, uid, slide_id, context)

        if not slide.website_published:
            return False

        body = _(
            '<p>A new presentation <i>%s</i> has been published under %s channel. <a href="%s/channel/%s/%s/view/%s">Click here to access the presentation.</a></p>' %
            (slide.name, slide.parent_id.name, base_url, slug(slide.parent_id), slide.slide_type, slug(slide))
        )
        partner_ids = []
        for partner in slide.parent_id.message_follower_ids:
            partner_ids.append(partner.id)
        self.pool.get('document.directory').message_post(cr, uid, [slide.parent_id.id], subject=slide.name, body=body, subtype='website_slide.new_slides', partner_ids=partner_ids, context=context)

    def notify_request_to_approve(self, cr, uid, slide_id, context):
        base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')
        slide = self.browse(cr, uid, slide_id, context)

        body = _(
            '<p>A new presentation <i>%s</i> has been uplodated under %s channel andwaiting for your review. <a href="%s/channel/%s/%s/view/%s">Click here to review the presentation.</a></p>' %
            (slide.name, slide.parent_id.name, base_url, slug(slide.parent_id), slide.slide_type, slug(slide))
        )
        partner_ids = []
        for partner in slide.parent_id.message_follower_ids:
            partner_ids.append(partner.id)
        self.pool.get('document.directory').message_post(cr, uid, [slide.parent_id.id], subject=slide.name, body=body, subtype='website_slide.new_slides_validation', partner_ids=partner_ids, context=context)


    def write(self, cr, uid, ids, values, context=None):
        if values.get('url'):
            values = self.update_youtube(cr, uid, values, context)

        success = super(ir_attachment, self).write(cr, uid, ids, values, context)
        
        for slide_id in ids:
            self.notify_published(cr, uid, slide_id, context)
        return success

    def update_youtube(self, cr, uid, values, context=None):
        print 'XXXXXXXX : values', values
        values["youtube_id"] = self.extract_youtube_id(values['url'].strip())
        statistics = self.youtube_statistics(values["youtube_id"])
        if statistics:
            print 'XXXXXXXXXXX : statistics ', statistics
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

    def create(self, cr, uid, values, context=None):
        if values.get('is_slide'):
            if values.get('datas_fname'):
                values['url'] = "/website_slides/" + values['datas_fname']
            elif values.get('url'):
                values = self.update_youtube(cr, uid, values, context)

        values['website_published'] = False
        slide_id = super(ir_attachment, self).create(cr, uid, values, context)
        self.notify_request_to_approve(cr, uid, slide_id, context)
        self.notify_published(cr, uid, slide_id, context)
        return slide_id

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        ids = super(ir_attachment, self)._search(cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=False)
        return len(ids) if count else ids

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

    def youtube_statistics(self,video_id):
        request_url = "https://www.googleapis.com/youtube/v3/videos?id=%s&key=AIzaSyBKDzf7KjjZqwPWAME6JOeHzzBlq9nrpjk&part=snippet,statistics&fields=items(id,snippet,statistics)" % (video_id)
        try:
            req = urllib2.Request(request_url)
            content = urllib2.urlopen(req).read()
        except urllib2.HTTPError:
            return False
        return json.loads(content)
