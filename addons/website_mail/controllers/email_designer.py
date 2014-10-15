# -*- coding: utf-8 -*-

import io
from urllib import urlencode
import werkzeug.wrappers
from PIL import Image, ImageFont, ImageDraw

from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.tools.mail import html_sanitize


class WebsiteEmailDesigner(http.Controller):

    @http.route('/website_mail/email_designer', type='http', auth="user", website=True)
    def index(self, model, res_id, template_model=None, **kw):
        if not model or not model in request.registry or not res_id:
            return request.redirect('/')
        model_cols = request.registry[model]._all_columns
        if 'body' not in model_cols and 'body_html' not in model_cols or \
           'email' not in model_cols and 'email_from' not in model_cols or \
           'name' not in model_cols and 'subject' not in model_cols:
            return request.redirect('/')
        res_id = int(res_id)
        obj_ids = request.registry[model].exists(request.cr, request.uid, [res_id], context=request.context)
        if not obj_ids:
            return request.redirect('/')
        # try to find fields to display / edit -> as t-field is static, we have to limit
        # the available fields to a given subset
        email_from_field = 'email'
        if 'email_from' in model_cols:
            email_from_field = 'email_from'
        subject_field = 'name'
        if 'subject' in model_cols:
            subject_field = 'subject'
        body_field = 'body'
        if 'body_html' in model_cols:
            body_field = 'body_html'

        cr, uid, context = request.cr, request.uid, request.context
        record = request.registry[model].browse(cr, uid, res_id, context=context)

        values = {
            'record': record,
            'templates': None,
            'model': model,
            'res_id': res_id,
            'email_from_field': email_from_field,
            'subject_field': subject_field,
            'body_field': body_field,
        }

        if getattr(record, body_field) or kw.get('theme_id'):
            values['mode'] = 'email_designer'
        else:
            if kw.get('enable_editor'):
                kw.pop('enable_editor')
                fragments = dict(model=model, res_id=res_id, **kw)
                if template_model:
                    fragments['template_model'] = template_model
                return request.redirect('/website_mail/email_designer?%s' % urlencode(fragments))
            values['mode'] = 'email_template'

        tmpl_obj = request.registry['email.template']
        if template_model:
            tids = tmpl_obj.search(cr, uid, [('model', '=', template_model)], context=context)
        else:
            tids = tmpl_obj.search(cr, uid, [], context=context)
        templates = tmpl_obj.browse(cr, uid, tids, context=context)
        values['templates'] = templates
        values['html_sanitize'] = html_sanitize

        return request.website.render("website_mail.email_designer", values)

    @http.route(['/website_mail/snippets','/website_mail/snippets/<snippet_xml_id>'], type='json', auth="user", website=True)
    def snippets(self, snippet_xml_id='website_mail.email_designer_default_snippets'):
        return request.website._render(snippet_xml_id)

    @http.route(['/website_mail/set_template_theme'], type='json', auth="user", website=True)
    def set_template_theme(self,**post):
        cr, uid, context = request.cr, request.uid, request.context
        if post.get('model') and post.get('res_id'):
            request.registry[post['model']].write(cr, uid, int(post['res_id']), {'theme_xml_id': post.get('snippet_xml_id')})
        return {}

    @http.route([
        '/fa_to_img/<icon>',
        '/fa_to_img/<icon>/<color>',
        '/fa_to_img/<icon>/<color>/<int:size>',
        '/fa_to_img/<icon>/<color>/<int:size>/<int:alpha>',
        ], auth="public", website=True)
    def export_icon_to_png(self, icon, color='#000', size=100, alpha=255):
        if color.startswith('rgba'):
            color = color.replace('rgba','rgb')
            color = ','.join(color.split(',')[:-1])+')'
        image = Image.new("RGBA", (size, size), color=(0,0,0,0))
        draw = ImageDraw.Draw(image)
        addons_path = http.addons_manifest['web']['addons_path']
        font = ImageFont.truetype(addons_path+'/web/static/lib/fontawesome/fonts/fontawesome-webfont.ttf', (size*92)/100) # Initialize font

        width,height = draw.textsize(icon, font=font)# Determine the dimensions of the icon
        draw.text(((size - width) / 2, (size - height) / 2), icon, font=font, fill=color)
        bbox = image.getbbox() # Get bounding box

        imagemask = Image.new("L", (size, size), 0) # Create an alpha mask
        drawmask = ImageDraw.Draw(imagemask)

        drawmask.text(((size - width) / 2, (size - height) / 2), icon, font=font, fill=alpha) # Draw the icon on the mask

        iconimage = Image.new("RGBA", (size,size), color) # Create a solid color image and apply the mask
        iconimage.putalpha(imagemask)
        if bbox:
            iconimage = iconimage.crop(bbox)
        borderw = int((size - (bbox[2] - bbox[0])) / 2)
        borderh = int((size - (bbox[3] - bbox[1])) / 2)

        outimage = Image.new("RGBA", (size, size), (0,0,0,0)) # Create output image
        outimage.paste(iconimage, (borderw,borderh))
        output = io.BytesIO()
        outimage.save(output, format="PNG")
        response = werkzeug.wrappers.Response()
        response.mimetype = 'image/png'
        response.data = output.getvalue()
        return response
