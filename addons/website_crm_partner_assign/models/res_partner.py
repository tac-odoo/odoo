# -*- coding: utf-8 -*-
from openerp.osv import osv, fields

class res_partner_grade(osv.osv):
    _name = 'res.partner.grade'
    _inherit = ['res.partner.grade', 'website.website_published.mixin']

    _defaults = {
        'website_published': True,
    }
