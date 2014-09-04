# -*- coding: utf-8 -*-

import werkzeug
from urlparse import urlparse
import simplejson

from openerp import SUPERUSER_ID
from openerp.http import request

from openerp.addons.web import http

from openerp.addons.website.models.website import slug

class main(http.Controller):

    _slides_per_page = 12
    _slides_per_list = 20

    def _slides_message(self, user, attachment_id=0, **post):
        attachment = request.env['ir.attachment']
        partner_obj = request.env['res.partner']

        if request.uid != request.website.user_id.id:
            partner_ids = [user.partner_id.id]
        else:
            partner_ids = attachment.sudo()._find_partner_from_emails(0, [post.get('email')])
            if not partner_ids or not partner_ids[0]:
                partner_ids = [partner_obj.sudo().create({'name': post.get('name'), 'email': post.get('email')})]
        message_id = attachment.search([('id', '=', int(attachment_id))]).sudo().with_context(mail_create_nosubcribe=True).message_post(
            body=post.get('comment'),
            type='comment',
            subtype='mt_comment',
            author_id=partner_ids[0],
            path=post.get('path', False),
            )
        return message_id

    @http.route('/channel', type='http', auth="public", website=True)
    def channels(self, *args, **post):
        directory = request.env['document.directory']
        user = request.env.user
        channels = directory.search([('website_published','=', True)])
        
        if len(channels) <= 1:
            return request.redirect("/channel/%s" % channels.id)

        vals = {
            'channels': channels, 
            'user': user,
            'is_public_user': user.id == request.website.user_id.id
        }
        return request.website.render('website_slides.channels', vals)

    @http.route(['/channel/<model("document.directory"):channel>',
                '/channel/<model("document.directory"):channel>/<types>',
                '/channel/<model("document.directory"):channel>/<types>/tag/<tags>',
                '/channel/<model("document.directory"):channel>/page/<int:page>',
                '/channel/<model("document.directory"):channel>/<types>/page/<int:page>',
                '/channel/<model("document.directory"):channel>/<types>/tag/<tags>/page/<int:page>',
                   ], type='http', auth="public", website=True)
    def slides(self, channel=0, page=1, types='', tags='', sorting='creation', search=''):
        user = request.env.user
        attachment = request.env['ir.attachment']

        domain = [('is_slide','=','True'), ('parent_id','=',channel.id)]

        count_all = count_slide = count_video = count_document = count_infographic = 0
        attachment_ids = videos = slides = documents = infographics = []
        famous = None

        if request.env.user.id == request.website.user_id.id: 
            domain += [('website_published', '=', True)]
        
        all_count = attachment.search_count(domain)
        if channel: 
            domain += [('parent_id','=',channel.id)]

        if search: 
            domain += ['|', ('name', 'ilike', search), ('index_content', 'ilike', search)]

        if tags: 
            domain += [('tag_ids.name', '=', tags)]

        values = {
            'tags':tags,
            'channel': channel,
            'user': user,
            'is_public_user': user.id == request.website.user_id.id,
        }
        
        if types:
            domain += [('slide_type', '=', types)]

            if sorting == 'date':
                order = 'write_date desc'
            elif sorting == 'view':
                order = 'slide_views desc'
            elif sorting == 'vote':
                order = 'likes desc'
            else:
                sorting = 'creation'
                order = 'create_date desc'

            url = "/channel/%s" % (channel.id)
            if types:
                url = "/channel/%s/%s" % (channel.id, types)
            elif types and tags:
                url = "/channel/%s/%s/%s" % (channel.id, types, tags)

            url_args = {}
            if search:
                url_args['search'] = search
            if sorting:
                url_args['sorting'] = sorting

            pager_count = attachment.search_count(domain)
            pager = request.website.pager(url=url, total=pager_count, page=page,
                                          step=self._slides_per_page, scope=self._slides_per_page,
                                          url_args=url_args)
            
            attachment_ids = attachment.search(domain, limit=self._slides_per_page, offset=pager['offset'], order=order)
            
            values.update({
                'attachment_ids': attachment_ids,
                'all_count': pager_count,
                'pager': pager,
                'types': types,
                'sorting': sorting,
                'search': search
            })
        else:
            count_domain = domain + [('slide_type', '=', 'video')]
            videos = attachment.search(count_domain, limit=4, offset=0, order='create_date desc')
            lens = {'video': len(videos)}

            count_domain = domain + [('slide_type', '=', 'presentation')]
            slides = attachment.search(count_domain, limit=4, offset=0, order='create_date desc')
            lens.update({'presentation':len(slides)})

            count_domain = domain + [('slide_type', '=', 'document')]
            documents = attachment.search(count_domain, limit=4, offset=0, order='create_date desc')
            lens.update({'document':len(documents)})

            count_domain = domain + [('slide_type', '=', 'infographic')]
            infographics = attachment.search(count_domain, limit=4, offset=0, order='create_date desc')
            lens.update({'infographic':len(infographics)})

            famous = channel.get_mostviewed()
            values.update({
                'videos':videos,
                'slides':slides,
                'documents':documents,
                'infographics': infographics,
                'famous':famous
            })
            counts = attachment.read_group(domain, ['slide_type'], groupby='slide_type')
            countvals = {}
            for count in counts:
                countvals['count_'+count.get('slide_type')] = count.get('slide_type_count') - lens.get(count.get('slide_type'))
                count_all += count.get('slide_type_count')

            values.update(countvals)
            values.update({'count_all':count_all})

        return request.website.render('website_slides.home', values)

    @http.route([
                '/channel/<model("document.directory"):channel>/<types>/<model("ir.attachment"):slideview>',
                '/channel/<model("document.directory"):channel>/<types>/tag/<tags>/<model("ir.attachment"):slideview>'
                ], type='http', auth="public", website=True)
    def slide_view(self, channel, slideview, types='', sorting='', search='', tags=''):
        attachment = request.env['ir.attachment']
        user = request.env.user

        domain = [('is_slide','=',True), ('website_published', '=', True)]
        slideview.sudo().set_viewed()

        most_viewed_ids = attachment.search(domain, limit=self._slides_per_list, offset=0, order='slide_views desc')

        tags = slideview.tag_ids.ids
        if tags:
            domain += [('tag_ids', 'in', tags)]
        related_ids = attachment.search(domain, limit=self._slides_per_list, offset=0)

        comments = slideview.website_message_ids

        values= {
            'slideview':slideview,
            'most_viewed_ids':most_viewed_ids,
            'related_ids': related_ids,
            'comments': comments,
            'channel': slideview.parent_id,
            'user':user,
            'types':types,
            'is_public_user': user.id == request.website.user_id.id
        }
        return request.website.render('website_slides.slide_view', values)

    @http.route('/slides/comment/<model("ir.attachment"):slideview>', type='http', auth="public", methods=['POST'], website=True)
    def slides_comment(self, slideview, **post):
        attachment = request.env['ir.attachment']
        if post.get('comment'):
            user = request.env.user
            attachment = request.env['ir.attachment']
            attachment.check_access_rights('read')
            self._slides_message(user, slideview.id, **post)
        return werkzeug.utils.redirect(request.httprequest.referrer + "#discuss")

    @http.route('/slides/thumb/<int:document_id>', type='http', auth="public", website=True)
    def slide_thumb(self, document_id=0, **post):
        response = werkzeug.wrappers.Response()
        Website = request.env['website']
        return Website._image('ir.attachment', document_id, 'image', response)

    @http.route('/slides/get_tags', type='http', auth="public", methods=['GET'], website=True)
    def tag_read(self, **post):
        tags = request.env['ir.attachment.tag'].search_read([], ['name'])
        data = [tag['name'] for tag in tags]
        return simplejson.dumps(data)
    
    @http.route('/channel/<model("document.directory"):channel>/view/<model("ir.attachment"):slideview>/like', type='json', auth="public", website=True)
    def slide_like(self, channel, slideview, **post):
        if slideview.sudo().set_like():
            return slideview.likes

        return {'error': 'Error on wirte Data'}

    @http.route('/channel/<model("document.directory"):channel>/view/<model("ir.attachment"):slideview>/dislike', type='json', auth="public", website=True)
    def slide_dislike(self, channel, slideview, **post):
        if slideview.sudo().set_dislike():
            return slideview.dislikes

        return {'error': 'Error on wirte Data'}

    @http.route('/slides/get_channel', type='json', auth="public", website=True)
    def get_channel(self, **post):
        directory = request.env['document.directory']
        attachment = request.env['ir.attachment']
        channels = directory.name_search(name='', args=[('website_published','=', True)], operator='ilike', limit=100)
        res = []
        for channel in channels:
            res.append({'id': channel[0],
                        'name': channel[1]
                        })
        return res

    @http.route(['/slides/add_slide'], type='http', auth="user", methods=['POST'], website=True)
    def create_slide(self, *args, **post):
        Tag = request.env['ir.attachment.tag']
        tag_ids = []
        if post.get('tag_ids').strip('[]'):
            tags = post.get('tag_ids').strip('[]').replace('"', '').split(",")
            for tag in tags:
                tag_id = Tag.search([('name', '=', tag)])
                if tag_id:
                    tag_ids.append((4, tag_id[0]))
                else:
                    tag_ids.append((0, 0, {'name': tag}))
        post['tag_ids'] = tag_ids
        slide_obj = request.env['ir.attachment']

        _file_types = ['image/jpeg', 'image/png', 'image/jpg', 'image/gif']

        if post.get('mimetype') in _file_types:
            post['slide_type'] = 'infographic'
            post['image'] = post.get('datas')

        if post.get('url') and not post.get('datas', False):
            post['slide_type'] = 'video'
        elif post.get('mimetype') == 'application/pdf':
            height = post.get('height', 0)
            width = post.get('width', 0)

            if height > width:
                post['slide_type'] = 'document'
            else:
                post['slide_type'] = 'presentation'

            del post['height']
            del post['width']

        slide_id = slide_obj.create(post)
        return request.redirect("/channel/%s/%s/%s" % (post.get('parent_id'), post['slide_type'], slide_id.id))
