# -*- coding: utf-8 -*-

import datetime
import io
import json
import re
import urllib2
from PIL import Image
from urlparse import urlparse

from openerp import api, fields, models, _
from openerp.tools import image
from openerp.exceptions import Warning
from openerp.http import request
from openerp.addons.website.models.website import slug


class Channel(models.Model):
    """ A channel is a container of slides. It has group-based access configuration
    allowing to configure slide upload and access. Slides can be promoted in
    channels. """
    _name = 'slide.channel'
    _description = 'Channel for Slides'
    _inherit = ['mail.thread', 'website.seo.metadata']
    _order = 'sequence, id'
    _order_by_strategy = {
        'most_viewed': 'total_views desc',
        'most_voted': 'likes desc',
        'latest': 'date_published desc',
    }

    name = fields.Char('Name', translate=True, required=True)
    website_published = fields.Boolean('Published', help="Published on the website", copy=False)
    description = fields.Html('Description', translate=True)
    category_ids = fields.One2many('slide.category', 'channel_id', string="Categories")
    slide_ids = fields.One2many('slide.slide', 'channel_id', string="Slides")
    promote_strategy = fields.Selection([
        ('none', 'No Featured Presentation'),
        ('latest', 'Latest Published'),
        ('most_voted', 'Most Voted'),
        ('most_viewed', 'Most Viewed'),
        ('custom', 'Featured Presentation')],
        string="Featuring Policy", default='most_voted', required=True)
    custom_slide_id = fields.Many2one('slide.slide', string='Slide to use for Custom Promote Strategy')
    promoted_slide_id = fields.Many2one('slide.slide', string='Featured Slide', compute='_compute_promoted_slide_id', store=True)

    @api.depends('custom_slide_id', 'promote_strategy')
    def _compute_promoted_slide_id(self):
        for record in self:
            if record.promote_strategy == 'none':
                record.promoted_slide_id = False
            elif record.promote_strategy == 'custom':
                record.promoted_slide_id = record.custom_slide_id
            else:
                slides = self.env['slide.slide'].search(
                    [('website_published', '=', True), ('channel_id', '=', record.id)],
                    limit=1, order=self._order_by_strategy[record.promote_strategy])
                record.promoted_slide_id = slides and slides[0] or False

    nbr_presentations = fields.Integer('Number of Presentations', compute='_count_presentations', store=True)
    nbr_documents = fields.Integer('Number of Documents', compute='_count_presentations', store=True)
    nbr_videos = fields.Integer('Number of Videos', compute='_count_presentations', store=True)
    nbr_infographics = fields.Integer('Number of Infographics', compute='_count_presentations', store=True)
    total = fields.Integer(compute='_count_presentations', store=True)

    @api.depends('slide_ids.slide_type', 'slide_ids.website_published')
    def _count_presentations(self):
        result = dict.fromkeys(self.ids, dict())
        res = self.env['slide.slide'].read_group(
            [('website_published', '=', True), ('channel_id', 'in', self.ids)],
            ['channel_id', 'slide_type'], ['channel_id', 'slide_type'],
            lazy=False)
        for res_group in res:
            result[res_group['channel_id'][0]][res_group['slide_type']] = result[res_group['channel_id'][0]].get(res_group['slide_type'], 0) + res_group['__count']
        for record in self:
            record.nbr_presentations = result[record.id].get('presentation', 0)
            record.nbr_documents = result[record.id].get('document', 0)
            record.nbr_videos = result[record.id].get('video', 0)
            record.nbr_infographics = result[record.id].get('infographic', 0)
            record.total = record.nbr_presentations + record.nbr_documents + record.nbr_videos + record.nbr_infographics

    sequence = fields.Integer('Sequence')
    access_error_msg = fields.Html(
        'Error Message', help="Display message (html) when channel's content"
        "is not accessible for a user due to access rights")
    template_id = fields.Many2one(
        'email.template', 'Email Template',
        html="Email template use to send new presentation upload notification through email")
    visibility = fields.Selection([
        ('public', 'Public'), ('private', 'Hide Channel'),
        ('partial', 'Show channel but presentations based on groups')], default='public')
    group_ids = fields.Many2many(
        'res.groups', 'rel_channel_groups', 'channel_id', 'group_id',
        string='Channel Groups', help="Groups allowed to access this channel.")
    upload_group_ids = fields.Many2many(
        'res.groups', 'rel_upload_groups', 'channel_id', 'group_id',
        string='Upload Groups', help="Groups allowed to upload presentations.")

    @api.onchange('visibility')
    def change_visibility(self):
        if self.visibility == 'public':
            self.group_ids = False


class Category(models.Model):
    """ Channel contain various categories to manage it's slides by category """
    _name = 'slide.category'
    _description = "Slide Category"
    _order = "sequence, id"

    name = fields.Char('Name', translate=True, required=True)
    channel_id = fields.Many2one('slide.channel', string="Channel", required=True)
    sequence = fields.Integer(default=10)
    slide_ids = fields.One2many('slide.slide', 'category_id', string="Slides")
    nbr_presentations = fields.Integer("Number of Presentations", compute='_count_presentations', store=True)
    nbr_documents = fields.Integer("Number of Documents", compute='_count_presentations', store=True)
    nbr_videos = fields.Integer("Number of Videos", compute='_count_presentations', store=True)
    nbr_infographics = fields.Integer("Number of Infographics", compute='_count_presentations', store=True)
    total = fields.Integer(compute='_count_presentations', store=True)

    @api.depends('slide_ids.slide_type', 'slide_ids.website_published')
    def _count_presentations(self):
        result = dict.fromkeys(self.ids, dict())
        res = self.env['slide.slide'].read_group(
            [('website_published', '=', True), ('category_id', 'in', self.ids)],
            ['category_id', 'slide_type'], ['category_id', 'slide_type'],
            lazy=False)
        for res_group in res:
            result[res_group['category_id'][0]][res_group['slide_type']] = result[res_group['category_id'][0]].get(res_group['slide_type'], 0) + res_group['__count']
        for record in self:
            record.nbr_presentations = result[record.id].get('presentation', 0)
            record.nbr_documents = result[record.id].get('document', 0)
            record.nbr_videos = result[record.id].get('video', 0)
            record.nbr_infographics = result[record.id].get('infographic', 0)
            record.total = record.nbr_presentations + record.nbr_documents + record.nbr_videos + record.nbr_infographics


class EmbeddedSlide(models.Model):
    """ Embedding in third party websites. Track view count, generate statistics. """
    _name = 'slide.embed'
    _description = 'Embedded Slides View Counter'
    _rec_name = 'slide_id'

    slide_id = fields.Many2one('slide.slide', string="Presentation", required=True, select=1)
    url = fields.Char('Third Party Website Url', required=True)
    count_views = fields.Integer('# Views', default=1)

    def add_embed_url(self, slide_id, url):
        schema = urlparse(url)
        baseurl = schema.netloc
        embeds = self.search([('url', '=', baseurl), ('slide_id', '=', int(slide_id))], limit=1)
        if embeds:
            embeds.count_views += 1
        else:
            embeds = self.create({
                'slide_id': slide_id,
                'url': baseurl,
            })
        return embeds.count_view


class SlideTag(models.Model):
    """ Tag to search slides accross channels. """
    _name = 'slide.tag'
    _description = 'Slide Tag'

    name = fields.Char('Name')


class Slide(models.Model):
    """ This model represents actual presentations. Those must be one of four
    types:

     - Presentation (pdf presentations)
     - Document (pdf books or documents)
     - Infographic (images)
     - Video (youtube or google drive videos)

    Slide has various statistics like view count, embed count, like, dislikes """
    _name = 'slide.slide'
    _inherit = ['mail.thread', 'website.seo.metadata']
    _description = 'Slides'

    _PROMOTIONAL_FIELDS = [
        '__last_update', 'name', 'image_thumb', 'slide_type', 'total_views', 'category_id',
        'channel_id', 'description', 'website_published', 'tag_ids', 'write_date', 'create_date']  # ?

    # description
    name = fields.Char('Title', required=True)
    description = fields.Text('Description', translate=True)
    channel_id = fields.Many2one('slide.channel', string="Channel", required=True)
    category_id = fields.Many2one('slide.category', string="Category")
    tag_ids = fields.Many2many('slide.tag', 'rel_slide_tag', 'slide_id', 'tag_id', string='Tags')
    image = fields.Binary('Image')
    image_medium = fields.Binary('Medium', compute="_get_image", store=True)
    image_thumb = fields.Binary('Thumbnail', compute="_get_image", store=True)

    @api.depends('image')
    def _get_image(self):
        for record in self:
            if record.image:
                record.image_medium = image.crop_image(record.image, thumbnail_ratio=3)
                record.image_thumb = image.crop_image(record.image, thumbnail_ratio=4)

    # access
    download_security = fields.Selection([
        ('none', 'No One'), ('user', 'Authentified User Only'),
        ('public', 'Everyone')], string='Download Security')
    # content
    slide_type = fields.Selection([
        ('infographic', 'Infographic'), ('presentation', 'Presentation'),
        ('document', 'Document'), ('video', 'Video')],
        string='Type',
        help="Document type will be set automatically depending on the height and width, however you can change it manually.")
    index_content = fields.Text('Transcript')  # TDE ??
    datas = fields.Binary('Content')  # TDE ?? versus index content ?
    url = fields.Char('Document URL', help="Youtube or Google Document URL")
    document_id = fields.Char('Document Id', help="Youtube or Google Document ID")
    mime_type = fields.Char('Mime-type')

    @api.onchange('url')
    @api.multi
    def on_change_url(self):
        self.ensure_one()
        url = self.url
        if url:
            document, id = self._parse_document_url(url)
            if not document:
                raise Warning(_('Please enter valid youtube or google doc url'))

            vals = self.get_resource_detail({document: id})
            if not vals:
                raise Warning(_('Could not fetch data from url. Document or access right not available'))

            self.name = vals['name']
            self.image = vals['image']
            self.slide_type = vals['slide_type']
            self.document_id = id
            self.mime_type = vals.get('mime_type') or False
            self.index_content = vals.get('index_content') or ''
            self.datas = vals.get('datas') or ''
            self.description = vals.get('description') or ''

            self.youtube_views = vals.get('youtube_views') or 0
            self.likes = vals.get('likes') or 0
            self.dislikes = vals.get('dislikes') or 0

    # website
    website_published = fields.Boolean('Published', help="Published on the website", copy=False)
    date_published = fields.Datetime('Publish Date')
    website_message_ids = fields.One2many(
        'mail.message', 'res_id',
        domain=lambda self: [('model', '=', self._name), ('type', '=', 'comment')],
        string='Website Messages', help="Website communication history")
    likes = fields.Integer('Likes')
    dislikes = fields.Integer('Dislikes')
    # views
    embedcount_ids = fields.One2many('slide.embed', 'slide_id', string="Embed Count")
    slide_views = fields.Integer('# of Website Views')
    embed_views = fields.Integer('# of Embedded Views')
    youtube_views = fields.Integer('# of Youtube Views')
    total_views = fields.Integer("Total # Views", compute='_compute_total', store=True)

    @api.depends('slide_views', 'embed_views', 'youtube_views')
    def _compute_total(self):
        for record in self:
            record.total_views = record.slide_views + record.embed_views + record.youtube_views

    share_url = fields.Char('Share URL', compute='_get_share_url')

    def _get_share_url(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        for record in self:
            record.share_url = "%s/slides/slide/%s" % (base_url, slug(record))

    embed_code = fields.Text('Embed Code', compute='_get_embed_code')

    def _get_embed_code(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        for record in self:
            if record.datas and not record.document_id:
                record.embed_code = '<iframe src="%s/slides/embed/%s?page=1" allowFullScreen="true" height="%s" width="%s" frameborder="0"></iframe>' % (base_url, record.id, 315, 420)
            elif record.slide_type == 'video' and record.document_id:
                if not record.mime_type:
                    # embed youtube video
                    record.embed_code = '<iframe src="//www.youtube.com/embed/%s?theme=light" frameborder="0"></iframe>' % (record.document_id)
                else:
                    # embed google doc video
                    record.embed_code = '<embed src="https://video.google.com/get_player?ps=docs&partnerid=30&docid=%s" type="application/x-shockwave-flash"></embed>' % (record.document_id)
            else:
                record.embed_code = False

    @api.model
    def create(self, values):
        if not values.get('index_content'):
            values['index_content'] = values.get('description')

        if values.get('slide_type') == 'infographic':
            values['image'] = values['datas']

        if values.get('website_published'):
            values['date_published'] = datetime.datetime.now()

        slide_id = super(Slide, self).create(values)

        # notify channel manager to approve uploaded slide
        slide_id.notify_request_to_approve()

        # document, id = self._parse_document_url(post['url'])
        # if document:
        #     values = self.get_resource_detail({document: id})
        #     values['document_id'] = id
        # values.update(post)

        # notify all users who subscribed to channel
        slide_id.notify_published()
        return slide_id

    @api.multi
    def write(self, values):
        if values.get('website_published'):
            values['date_published'] = datetime.datetime.now()
        res = super(Slide, self).write(values)
        if values.get('website_published'):
            self.notify_published()
        return res

    def get_related_slides(self, limit=20):
        self.ensure_one()
        domain = [('website_published', '=', True), ('id', '!=', self.id)]
        if self.category_id:
            domain += [('category_id', '=', self.category_id.id)]
        return self.search(domain, limit=limit)

    def get_most_viewed_slides(self, limit=20):
        self.ensure_one()
        return self.search([('website_published', '=', True), ('id', '!=', self.id)], limit=limit, order='total_views desc')

    # def get_slide_detail(self):
    #     self.ensure_one()
    #     most_viewed_slides = self.get_most_viewed_slides(self._slides_per_list)
    #     related_slides = self.get_related_slides(self._slides_per_list)
    #     values = {
    #         'most_viewed_slides': most_viewed_slides,
    #         'related_slides': related_slides,
    #     }
    #     if self.channel_id.visibility == 'partial' and not self.channel_id.group_ids & request.env.user.groups_id:
    #         values.update({
    #             'private': True,
    #             'private_slide': self,
    #         })
    #         return values
    #     values.update({
    #         'channel': self.channel_id,
    #         'slide': self,
    #         'comments': self.website_message_ids,
    #     })
    #     return values

    # def get_mail_body(self, message=False):
        # base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        # template = self.env['email.template']
        # image_url = "%s/website/image/slide.slide/%s/image" % (base_url, self.id)

        # msg_context = {
        #     'message': message or _('%s has shared a %s with you !') % (self.env.user.name, self.slide_type),
        #     'image_url': image_url,
        #     'base_url': base_url
        # }
        # msg_context.update(self._context)
        # message_body = template.with_context(msg_context).render_template(self.channel_id.template_id.body_html, 'slide.slide', self.id)
        # return message_body

    def send_share_email(self, email):
        # self.env['email.template'].render_template()
        result = False
        # TDE FIXME: please use an email template and standard methods that are
        # not deprecated since 6.1

        # body = self.get_mail_body()
        # subject = _('%s has shared a %s with you !') % (self.env.user.name, self.slide_type)

        # if self.env.user.email:
        #     result = mail.email_send(email_from=self.env.user.email, email_to=[email], subject=subject, body=body, reply_to=self.env.user.email, subtype="html")

        return result

    def notify_published(self):
        if not self.website_published:
            return False

        if self.channel_id:
            base_url = self.pool['ir.config_parameter'].get_param(self._cr, self._uid, 'web.base.url')
            body = _(
                '<p>A new presentation <i>%s</i> has been published under %s channel. <a href="%s/slides/%s">Click here to access the presentation.</a></p>' %
                (self.name, self.channel_id.name, base_url, slug(self))
            )
            self.channel_id.message_post(subject=self.name, body=body, subtype='website_slides.new_slides')

    # As per channel access configuration (visibility)
    #   public  ==> no restriction on slides access
    #   private ==> restrict all slides of channel base on access group define on channel group_ids field
    #   partial ==> Show channel, but presentations based on groups means any user can see channel but not slide's content.
    #
    #   for private : implement using record rule
    #
    #   for partial: user can see channel, but channel gridview have slide detail so we have to implement
    #   partial field access mechanism for public user so he can have access
    #   of promotional field (name, view_count) of slides, but not all fields like data (actual pdf content)
    #   all fields should be accessible only for user group define on channel group_ids
    #
    # @api.model
    # def check_field_access_rights(self, operation, fields):
    #     fields = super(Slide, self).check_field_access_rights(operation, fields)
    #     if self.ids:
    #         # still read not perform so we can not access self.channel_id
    #         self.env.cr.execute('SELECT DISTINCT channel_id FROM ' + self._table + ' WHERE id IN %s', (tuple(self.ids),))
    #         channel_ids = [x[0] for x in self.env.cr.fetchall()]
    #         channels = self.env['slide.channel'].sudo().browse(channel_ids)
    #         promotional_field_only = False
    #         for channel in channels:
    #             if channel.visibility == 'partial' and not(channel.group_ids & self.env.user.groups_id):
    #                 promotional_field_only = True

    #         if promotional_field_only:
    #             fields = filter(lambda field: field in self._PROMOTIONAL_FIELDS, fields)
    #     return fields

    def notify_request_to_approve(self):
        if self.website_published:
            return False

        if self.channel_id:
            message = _("A new %s has been uploaded and waiting for publish on %s channel.") % (self.slide_type, self.channel_id.name)

            base_url = self.pool['ir.config_parameter'].get_param(self._cr, self._uid, 'web.base.url')

            body = _(
                '<p>A new presentation <i>%s</i> has been uploaded under %s channel andwaiting for your review. <a href="%s/slides/%s">Click here to review the presentation.</a></p>' %
                (self.name, self.channel_id.name, base_url, slug(self))
            )

            self.channel_id.message_post(subject=message, body=body, subtype='website_slides.new_slides_validation')

    def _parse_document_url(self, url):
        expr = re.compile(r'^.*((youtu.be/)|(v/)|(\/u\/\w\/)|(embed\/)|(watch\?))\??v?=?([^#\&\?]*).*')
        arg = expr.match(url)
        document_id = arg and arg.group(7) or False
        if document_id:
            return ('youtube', document_id)

        expr = re.compile(r'((^https://docs.google.com)|(^https://drive.google.com))(.*\/d\/)(.*)(.*\/)')
        arg = expr.match(url)
        document_id = arg and arg.group(5) or False
        if document_id:
            return ('google_doc', document_id)

        return (None, False)

    def get_resource_detail(self, document, only_preview_fields=False, part='snippet,statistics', fields='id,snippet,statistics'):
        vals = False
        key = 'AIzaSyBKDzf7KjjZqwPWAME6JOeHzzBlq9nrpjk'
        if document.get('google_doc'):
            request_url = "https://www.googleapis.com/drive/v2/files/%s?projection=BASIC&key=%s" % (document['google_doc'], key)
            values = self._get_external_data(request_url, type="json")
            if values:
                vals = self.parse_google_document(values, only_preview_fields)
            return vals

        if document.get('youtube'):
            apiurl = 'https://www.googleapis.com/youtube/v3/videos'
            request_url = "%s?id=%s&key=%s&part=%s&fields=items(%s)" % (apiurl, document['youtube'], key, part, fields)
            values = self._get_external_data(request_url, type="json")
            if values:
                vals = self.parse_youtube_statistics(values, only_preview_fields)
            return vals

    def _get_external_data(self, resource_url, type=False):
        values = False
        try:
            req = urllib2.Request(resource_url)
            content = urllib2.urlopen(req).read()
            if type == 'json':
                values = json.loads(content)
            elif type in ('image', 'pdf'):
                values = content.encode('base64')
            else:
                values = content
        except urllib2.HTTPError:
            pass
        return values

    def parse_google_document(self, values, only_preview_fields):
        def get_slide_type(vals):
            image = Image.open(io.BytesIO(vals['image'].decode('base64')))
            width, height = image.size
            if height > width:
                return 'document'
            else:
                return 'presentation'

        vals = {}
        if values:
            if only_preview_fields:
                vals.update({
                    'url_src': values['thumbnailLink'],
                    'title': values['title'],
                })
                return vals
            image_url = values['thumbnailLink'].replace('=s220', '')
            vals.update({
                'name': values['title'],
                'mime_type': values['mimeType'],
                'image': self._get_external_data(image_url, type='image')
            })

            if values['mimeType'].startswith('video/'):
                vals['slide_type'] = 'video'

            if values['mimeType'].startswith('image/'):
                vals['datas'] = vals['image']
                vals['slide_type'] = 'infographic'

            if values['mimeType'].startswith('application/vnd.google-apps'):
                vals['datas'] = self._get_external_data(values['exportLinks']['application/pdf'], type='pdf')

                vals['slide_type'] = get_slide_type(vals)

                if values.get('exportLinks').get('text/plain'):
                    vals['index_content'] = self._get_external_data(values['exportLinks']['text/plain'])
                if values.get('exportLinks').get('text/csv'):
                    vals['index_content'] = self._get_external_data(values['exportLinks']['text/csv'])

            if values['mimeType'] == 'application/pdf':
                # TODO: Google drive pdf docuement don't provide plain text (transcript).
                vals['datas'] = self._get_external_data(values['webContentLink'], type='pdf')
                vals['slide_type'] = get_slide_type(vals)

        return vals

    def parse_youtube_statistics(self, values, only_preview_fields):
        vals = {}
        if values:
            item = values['items'][0]

            if item.get('snippet'):
                if only_preview_fields:
                    vals.update({
                        'url_src': item['snippet']['thumbnails']['high']['url'],
                        'title': values['items'][0]['snippet']['title'],
                        'description': values['items'][0]['snippet']['description']
                    })
                    return vals

                vals.update({
                    'name': values['items'][0]['snippet']['title'],
                    'image': self._get_external_data(item['snippet']['thumbnails']['high']['url'], type='image'),
                    'slide_type': 'video',
                    'description': values['items'][0]['snippet']['description'],
                })

            if item.get('statistics'):
                vals.update({
                    'youtube_views': int(item['statistics']['viewCount']),
                    'likes': int(item['statistics']['likeCount']),
                    'dislikes': int(item['statistics']['dislikeCount'])
                })

        return vals
