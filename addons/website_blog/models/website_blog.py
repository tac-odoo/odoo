# -*- coding: utf-8 -*-

from datetime import datetime
import lxml
import random

from openerp.addons.website.models.website import slug
from openerp import models, fields, api, tools, _


class Blog(models.Model):
    _name = 'blog.blog'
    _description = 'Blogs'
    _inherit = ['mail.thread', 'website.seo.metadata']
    _order = 'name'

    name = fields.Char(string='Blog Name', required=True)
    subtitle = fields.Char(string='Blog Subtitle')
    description = fields.Text(string='Description')

    @api.multi
    def all_tags(self, min_limit=1):
        req = """
            SELECT
                p.blog_id, count(*), r.blog_tag_id
            FROM
                blog_post_blog_tag_rel r
                    join blog_post p on r.blog_post_id=p.id
            WHERE
                p.blog_id in %s
            GROUP BY
                p.blog_id,
                r.blog_tag_id
            ORDER BY
                count(*) DESC
        """
        self._cr.execute(req, [tuple(self.ids)])
        tag_by_blog = {i: [] for i in self.ids}
        for blog_id, freq, tag_id in self._cr.fetchall():
            if freq >= min_limit:
                tag_by_blog[blog_id].append(tag_id)

        for blog_id in tag_by_blog:
            tag_by_blog[blog_id] = self.env['blog.tag'].browse(tag_by_blog[blog_id])
        return tag_by_blog


class BlogTag(models.Model):
    _name = 'blog.tag'
    _description = 'Blog Tag'
    _inherit = ['website.seo.metadata']
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    post_ids = fields.Many2many('blog.post', string="Posts")

class BlogPost(models.Model):
    _name = "blog.post"
    _description = "Blog Post"
    _inherit = ['mail.thread', 'website.seo.metadata']
    _order = 'id DESC'

    @api.multi
    @api.depends('visits')
    def _compute_ranking(self):
        #fix me Might be not worked properly due to Store=True and used now()
        for blog_post in self:
            if blog_post.visits:
                age = datetime.now() - datetime.strptime(blog_post.create_date, tools.DEFAULT_SERVER_DATETIME_FORMAT)
                blog_post.ranking = blog_post.visits * (0.5+random.random()) / max(3, age.days)

    name = fields.Char(string='Title', required=True, translate=True, default=_('Blog Post Title'))
    subtitle = fields.Char(string='Sub Title', translate=True, default=_('Subtitle'))
    author_id = fields.Many2one('res.partner', string='Author', default=lambda self:self.env.user.partner_id)
    background_image = fields.Binary(string='Background Image', oldname='content_image')
    blog_id = fields.Many2one(
        'blog.blog', string='Blog',
        required=True, ondelete='cascade'
    )
    tag_ids = fields.Many2many(
        'blog.tag', string='Tags'
    )
    content = fields.Html(string='Content', translate=True, sanitize=False)
    # website control
    website_published = fields.Boolean(
        string='Publish', help="Publish on the website", copy=False
    )
    website_message_ids = fields.One2many(
        'mail.message', 'res_id',
        domain=lambda self: [
            '&', '&', ('model', '=', self._name), ('type', '=', 'comment'), ('path', '=', False)
        ],
        string='Website Messages',
        help="Website communication history"
    )
    author_avatar = fields.Binary(related="author_id.image_small", string="Avatar")
    visits = fields.Integer(string='No of Views')
    ranking = fields.Float(compute='_compute_ranking', store=True, string='Ranking')

    @api.model
    def html_tag_nodes(self, html, attribute=None, tags=None):
        """ Processing of html content to tag paragraphs and set them an unique
        ID.
        :return result: (html, mappin), where html is the updated html with ID
                        and mapping is a list of (old_ID, new_ID), where old_ID
                        is None is the paragraph is a new one. """
        mapping = []
        if not html:
            return html, mapping
        if tags is None:
            tags = ['p']
        if attribute is None:
            attribute = 'data-unique-id'
        counter = 0

        # form a tree
        root = lxml.html.fragment_fromstring(html, create_parent='div')
        if not len(root) and root.text is None and root.tail is None:
            return html, mapping

        # check all nodes, replace :
        # - img src -> check URL
        # - a href -> check URL
        for node in root.iter():
            if not node.tag in tags:
                continue
            ancestor_tags = [parent.tag for parent in node.iterancestors()]
            if ancestor_tags:
                ancestor_tags.pop()
            ancestor_tags.append('counter_%s' % counter)
            new_attribute = '/'.join(reversed(ancestor_tags))
            old_attribute = node.get(attribute)
            node.set(attribute, new_attribute)
            mapping.append((old_attribute, counter))
            counter += 1

        html = lxml.html.tostring(root, pretty_print=False, method='html')
        # this is ugly, but lxml/etree tostring want to put everything in a 'div' that breaks the editor -> remove that
        if html.startswith('<div>') and html.endswith('</div>'):
            html = html[5:-6]
        return html, mapping

    @api.model
    def _postprocess_content(self, content=None):
        #(_postproces_content = _postprocess_content)
        if not content:
            return False
        content, mapping = self.html_tag_nodes(content, attribute='data-chatter-id', tags=['p'])
        for old_attribute, new_attribute in mapping:
            if not old_attribute:
                continue
            messages = self.env['mail.message'].sudo().search([('path', '=', old_attribute)])
            messages.write({'path': new_attribute})
        return content

    @api.multi
    def _check_for_publication(self, vals):
        if vals.get('website_published'):
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')
            for post in self:
                post.blog_id.message_post(
                    body='<p>%(post_publication)s <a href="%(base_url)s/blog/%(blog_slug)s/post/%(post_slug)s">%(post_link)s</a></p>' % {
                        'post_publication': _('A new post %s has been published on the %s blog.') % (post.name, post.blog_id.name),
                        'post_link': _('Click here to access the post.'),
                        'base_url': base_url,
                        'blog_slug': slug(post.blog_id),
                        'post_slug': slug(post),
                    },
                    subtype='website_blog.mt_blog_blog_published')
            return True
        return False

    @api.model
    def create(self, vals):
        if 'content' in vals:
            vals['content'] = self._postprocess_content(vals['content'])
        post = super(BlogPost, self.with_context(mail_create_nolog=True)).create(vals)
        post._check_for_publication(vals)
        return post

    @api.multi
    def write(self, vals):
        if 'content' in vals:
            vals['content'] = self._postprocess_content(vals['content'])
        result = super(BlogPost, self).write(vals)
        self._check_for_publication(vals)
        return result
