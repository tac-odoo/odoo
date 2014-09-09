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

    @http.route('/slides', type='http', auth="public", website=True)
    def channels(self, *args, **post):
        directory = request.env['document.directory']
        user = request.env.user
        channels = directory.search([('website_published','=', True)])
        
        if len(channels) <= 1:
            return request.redirect("/slides/%s" % channels.id)

        vals = {
            'channels': channels, 
            'user': user,
            'is_public_user': user.id == request.website.user_id.id
        }
        return request.website.render('website_slides.channels', vals)


    @http.route(['/slides/<model("document.directory"):channel>/category/<model("ir.attachment.category"):category>',
                '/slides/<model("document.directory"):channel>/category/<model("ir.attachment.category"):category>/page/<int:page>'
                ], type='http', auth="public", website=True)
    def categories(self, channel, category, order='id', page=1):
        attachment = request.env['ir.attachment']

        domain = [('is_slide','=','True'), ('parent_id','=',channel.id), ('category_id','=',category.id)]

        url = "/slides/%s/category/%s" % (channel.id, category.id)
        pager_count = attachment.search_count(domain)
        pager = request.website.pager(url=url, total=pager_count, page=page,
                                      step=self._slides_per_page, scope=self._slides_per_page,
                                      url_args={})

        attachment_ids = attachment.search(domain, limit=self._slides_per_page, offset=pager['offset'], order=order)
        values = {
            'attachment_ids':attachment_ids,
            'pager': pager,
            'channel': channel,
            'category':category
        }
        return request.website.render('website_slides.category', values)


    @http.route(['/slides/<model("document.directory"):channel>',
                '/slides/<model("document.directory"):channel>/<types>',
                '/slides/<model("document.directory"):channel>/<types>/tag/<tags>',
                '/slides/<model("document.directory"):channel>/page/<int:page>',
                '/slides/<model("document.directory"):channel>/<types>/page/<int:page>',
                '/slides/<model("document.directory"):channel>/<types>/tag/<tags>/page/<int:page>',
                   ], type='http', auth="public", website=True)
    def slides(self, channel=0, page=1, types='', tags='', sorting='creation', search=''):
        user = request.env.user
        attachment = request.env['ir.attachment']
        category = request.env['ir.attachment.category']

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

        counts = attachment.read_group(domain, ['slide_type'], groupby='slide_type')
        countvals = {}
        for count in counts:
            countvals['count_'+count.get('slide_type')] = count.get('slide_type_count')
            count_all += count.get('slide_type_count')

        values.update(countvals)
        values.update({'count_all':count_all})
        
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

            url = "/slides/%s" % (channel.id)
            if types:
                url = "/slides/%s/%s" % (channel.id, types)
            elif types and tags:
                url = "/slides/%s/%s/%s" % (channel.id, types, tags)

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
            category_ids = category.search([('document_id','=',channel.id)])

            # count_domain = domain + [('slide_type', '=', 'video')]
            # videos = attachment.search(count_domain, limit=4, offset=0, order='create_date desc')
            # values['more_count_video'] = values.get('count_video', 0) - len(videos)

            # count_domain = domain + [('slide_type', '=', 'presentation')]
            # slides = attachment.search(count_domain, limit=4, offset=0, order='create_date desc')
            # values['more_count_presentation'] = values.get('count_presentation', 0) - len(slides)

            # count_domain = domain + [('slide_type', '=', 'document')]
            # documents = attachment.search(count_domain, limit=4, offset=0, order='create_date desc')
            # values['more_count_document'] = values.get('count_document', 0) - len(documents)

            # count_domain = domain + [('slide_type', '=', 'infographic')]
            # infographics = attachment.search(count_domain, limit=4, offset=0, order='create_date desc')
            # values['more_count_infographic'] = values.get('count_infographic', 0) - len(infographics)

            famous = channel.get_mostviewed()
            values.update({
                # 'videos':videos,
                # 'slides':slides,
                # 'documents':documents,
                # 'infographics': infographics,
                'category_ids':category_ids,
                'famous':famous
            })

        return request.website.render('website_slides.home', values)

    @http.route([
                '/slides/<model("document.directory"):channel>/<types>/<model("ir.attachment"):slideview>',
                '/slides/<model("document.directory"):channel>/<types>/tag/<tags>/<model("ir.attachment"):slideview>'
                ], type='http', auth="public", website=True)
    def slide_view(self, channel, slideview, types='', sorting='', search='', tags=''):
        attachment = request.env['ir.attachment']
        user = request.env.user

        domain = [('is_slide','=',True), ('website_published', '=', True)]
        slideview.sudo().set_viewed()

        most_viewed_ids = attachment._get_most_viewed_slides(self._slides_per_list)
        related_ids = attachment._get_related_slides(self._slides_per_list)

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

    @http.route('/slides/get_tags', type='http', auth="public", methods=['GET'], website=True)
    def tag_read(self, **post):
        tags = request.env['ir.attachment.tag'].search_read([], ['name'])
        data = [tag['name'] for tag in tags]
        return simplejson.dumps(data)
    
    @http.route('/slides/<model("document.directory"):channel>/view/<model("ir.attachment"):slideview>/like', type='json', auth="public", website=True)
    def slide_like(self, channel, slideview, **post):
        if slideview.sudo().set_like():
            return slideview.likes

        return {'error': 'Error on wirte Data'}

    @http.route('/slides/<model("document.directory"):channel>/view/<model("ir.attachment"):slideview>/dislike', type='json', auth="public", website=True)
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

    @http.route(['/slides/add_slide'], type='json', auth="user", methods=['POST'], website=True)
    def create_slide(self, *args, **post):
        Tag = request.env['ir.attachment.tag']
        tags = post.get('tag_ids')
        tag_ids = []
        for tag in tags:
            tag_id = Tag.search([('name', '=', tag)])
            if tag_id:
                tag_ids.append((4, tag_id[0].id))
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
        if request.env['ir.attachment'].search([('name','=',post['name']),('parent_id','=',post['parent_id'])]):
            return {'error':'Could not create presentation. Same presenatation title already exist in this channel. please rename tile and try again.'}

        slide_id = slide_obj.create(post)
        return {'url': "/slides/%s/%s/%s" % (post.get('parent_id'), post['slide_type'], slide_id.id)}

    @http.route('/slides/overlay/<model("ir.attachment"):slide>', type='json', auth="public", website=True)
    def get_next_slides(self, slide):
        slides_to_suggest = 9
        suggested_ids = slide._get_related_slides(slides_to_suggest)
        if len(suggested_ids) < slides_to_suggest:
            slides_to_suggest = slides_to_suggest - len(related_ids)
            suggested_ids += slide._get_most_viewed_slides(slides_to_suggest)

        vals = []
        for suggest in suggested_ids:
            val = {
                'img_src':'/website/image/ir.attachment/%s/image' % (suggest.id),
                'caption':suggest.name,
                'url':suggest._get_share_url()
            }
            vals.append(val)

        return vals

    @http.route('/slides/embed/<model("ir.attachment"):slide>', type='http', auth="public", website=True)
    def slides_embed(self, slide, page="1"):
        user = request.env.user
        values = {
           'slide':slide,
           'user':user,
           'channel':slide.parent_id,
           'page':page,
        }
        return request.website.render('website_slides.pdfembed', values)
