# -*- encoding: utf-8 -*-

import time
from lxml import etree
from datetime import datetime
from xml.sax.saxutils import escape

from openerp import tools
from openerp import models, fields, api, _


class lunch_order(models.Model):
    """
    lunch order (contains one or more lunch order line(s))
    """
    _name = 'lunch.order'
    _description = 'Lunch Order'
    _order = 'date desc'

    @api.multi
    def add_preference(self, pref_id):
        """
        create a new order line based on the preference selected (pref_id)
        """
        assert len(self.ids) == 1
        orderline_ref = self.env['lunch.order.line']
        pref = orderline_ref.browse(pref_id)
        new_order_line = {
            'date': self.date,
            'user_id': self.env.uid,
            'product_id': pref.product_id.id,
            'note': pref.note,
            'order_id': self.id,
            'price': pref.product_id.price,
            'supplier': pref.product_id.supplier.id
        }
        return orderline_ref.create(new_order_line)

    @api.model
    def can_display_alert(self, alert):
        """
        This method check if the alert can be displayed today
        """
        if alert.alter_type == 'specific':
            #the alert is only activated on a specific day
            return alert.specific_day == time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
        elif alert.alter_type == 'week':
            #the alert is activated during some days of the week
            return alert[datetime.now().strftime('%A').lower()]
        return True  # alter_type == 'days' (every day)

    @api.multi
    def _default_alerts_get(self):
        """
        get the alerts to display on the order form
        """
        alert_ref = self.env['lunch.alert']
        alert_msg = []
        for alert in alert_ref.search([]):
            # check if the address must be displayed today
            if self.can_display_alert(alert):
                #display the address only during its active time
                self_in_tz = self.with_context(tz=('UTC'))
                mynow = fields.Datetime.context_timestamp(self_in_tz, datetime.now())
                hour_to = int(alert.active_to)
                min_to = int((alert.active_to - hour_to) * 60)
                to_alert = datetime.strptime(str(hour_to) + ":" + str(min_to), "%H:%M")
                hour_from = int(alert.active_from)
                min_from = int((alert.active_from - hour_from) * 60)
                from_alert = datetime.strptime(str(hour_from) + ":" + str(min_from), "%H:%M")
                if mynow.time() >= from_alert.time() and mynow.time() <= to_alert.time():
                    alert_msg.append(alert.message)
        return '\n'.join(alert_msg)

    @api.onchange('order_line_ids')
    def onchange_price(self):
        """
        Onchange methode that refresh the total price of order
        """
        order_line_ids = []
        order_line_ids = self.resolve_2many_commands("order_line_ids", self.order_line_ids.ids, ["price"])
        if order_line_ids:
            tot = 0.0
            for prod in order_line_ids:
                if 'product_id' in prod:
                    tot += self.env["lunch.product"].browse(prod['product_id']).price
                else:
                    tot += prod['price']
            self.total = tot

    def __getattr__(self, attr):
        """
        this method catch unexisting method call and if it starts with
        add_preference_'n' we execute the add_preference method with
        'n' as parameter
        """
        if attr.startswith('add_preference_'):
            pref_id = int(attr[15:])

            def specific_function(cr, uid, ids, context=None):
                return self.add_preference(cr, uid, ids, pref_id, context=context)
            return specific_function
        return super(lunch_order, self).__getattr__(attr)

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=True):
        """
        Add preferences in the form view of order.line
        """
        res = super(lunch_order, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=True)
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            preferences = self.order_line_ids.search([('user_id', '=', self.env.uid)], order='id desc')
            xml_start = etree.Element("div")
            # If there are no preference (it's the first time for the user)
            if len(preferences) == 0:
                # create Elements
                xml_no_pref_1 = etree.Element("div")
                xml_no_pref_1.set('class', 'oe_inline oe_lunch_intro')
                xml_no_pref_2 = etree.Element("h3")
                xml_no_pref_2.text = _("This is the first time you order a meal")
                xml_no_pref_3 = etree.Element("p")
                xml_no_pref_3.set('class', 'oe_grey')
                xml_no_pref_3.text = _("Select a product and put your order comments on the note.")
                xml_no_pref_4 = etree.Element("p")
                xml_no_pref_4.set('class', 'oe_grey')
                xml_no_pref_4.text = _("Your favorite meals will be created based on your last orders.")
                xml_no_pref_5 = etree.Element("p")
                xml_no_pref_5.set('class', 'oe_grey')
                xml_no_pref_5.text = _("Don't forget the alerts displayed in the reddish area")
                #structure Elements
                xml_start.append(xml_no_pref_1)
                xml_no_pref_1.append(xml_no_pref_2)
                xml_no_pref_1.append(xml_no_pref_3)
                xml_no_pref_1.append(xml_no_pref_4)
                xml_no_pref_1.append(xml_no_pref_5)
            #Else: the user already have preferences so we display them
            else:
                categories = {}  #store the different categories of products in preference
                for pref in preferences:
                    #For each preference
                    categories.setdefault(pref.product_id.category_id.name, {})
                    #if this product has already been added to the categories dictionnary
                    if pref.product_id.id in categories[pref.product_id.category_id.name]:
                        #we check if for the same product the note has already been added
                        if pref.note not in categories[pref.product_id.category_id.name][pref.product_id.id]:
                            #if it's not the case then we add this to preferences
                            categories[pref.product_id.category_id.name][pref.product_id.id][pref.note] = pref
                    #if this product is not in the dictionnay, we add it
                    else:
                        categories[pref.product_id.category_id.name][pref.product_id.id] = {}
                        categories[pref.product_id.category_id.name][pref.product_id.id][pref.note] = pref

                #For each preferences that we get, we will create the XML structure
                for key, value in categories.items():
                    xml_pref_1 = etree.Element("div")
                    xml_pref_1.set('class', 'oe_lunch_30pc')
                    xml_pref_2 = etree.Element("h2")
                    xml_pref_2.text = key
                    xml_pref_1.append(xml_pref_2)
                    i = 0
                    value = value.values()
                    #TODO: sorted_values is used for a quick and dirty hack in order to display the 5 last orders of each categories.
                    #It would be better to fetch only the 5 items to display instead of fetching everything then sorting them in order to keep only the 5 last.
                    #NB: The note could also be ignored + we could fetch the preferences on the most ordered products instead of the last ones...
                    sorted_values = {}
                    for val in value:
                        for elmt in val.values():
                            sorted_values[elmt.id] = elmt
                    for key, pref in sorted(sorted_values.iteritems(), key=lambda (k, v): (k, v), reverse=True):
                        #We only show 5 preferences per category (or it will be too long)
                        if i == 5:
                            break
                        i += 1
                        xml_pref_3 = etree.Element("div")
                        xml_pref_3.set('class', 'oe_lunch_vignette')
                        xml_pref_1.append(xml_pref_3)

                        xml_pref_4 = etree.Element("span")
                        xml_pref_4.set('class', 'oe_lunch_button')
                        xml_pref_3.append(xml_pref_4)

                        xml_pref_5 = etree.Element("button")
                        xml_pref_5.set('name', "add_preference_"+str(pref.id))
                        xml_pref_5.set('class', 'oe_link oe_i oe_button_plus')
                        xml_pref_5.set('type', 'object')
                        xml_pref_5.set('string', '+')
                        xml_pref_4.append(xml_pref_5)

                        xml_pref_6 = etree.Element("button")
                        xml_pref_6.set('name', "add_preference_"+str(pref.id))
                        xml_pref_6.set('class', 'oe_link oe_button_add')
                        xml_pref_6.set('type', 'object')
                        xml_pref_6.set('string', _("Add"))
                        xml_pref_4.append(xml_pref_6)

                        xml_pref_7 = etree.Element("div")
                        xml_pref_7.set('class', 'oe_group_text_button')
                        xml_pref_3.append(xml_pref_7)

                        xml_pref_8 = etree.Element("div")
                        xml_pref_8.set('class', 'oe_lunch_text')
                        xml_pref_8.text = escape(pref.product_id.name)+str(" ")
                        xml_pref_7.append(xml_pref_8)

                        price = pref.product_id.price or 0.0
                        cur = self.env.user.company_id.currency_id.name or ''
                        xml_pref_9 = etree.Element("span")
                        xml_pref_9.set('class', 'oe_tag')
                        xml_pref_9.text = str(price)+str(" ")+cur
                        xml_pref_8.append(xml_pref_9)

                        xml_pref_10 = etree.Element("div")
                        xml_pref_10.set('class', 'oe_grey')
                        xml_pref_10.text = escape(pref.note or '')
                        xml_pref_3.append(xml_pref_10)

                        xml_start.append(xml_pref_1)

            first_node = doc.xpath("//div[@name='preferences']")
            if first_node and len(first_node) > 0:
                first_node[0].append(xml_start)
            res['arch'] = etree.tostring(doc)
        return res

    user_id = fields.Many2one('res.users', 'User Name', required=True, readonly=True, states={'new': [('readonly', False)]}, default=lambda self: self.env.uid)
    date = fields.Date('Date', required=True, readonly=True, states={'new': [('readonly', False)]}, default=fields.Date.context_today)
    order_line_ids = fields.One2many('lunch.order.line', 'order_id', 'Products',
                                      ondelete="cascade", readonly=True, states={'new': [('readonly', False)]},
                                      copy=True)
    total = fields.Float(compute='_price_get', string="Total", store=True)

    @api.multi
    @api.depends('order_line_ids.product_id', 'order_line_ids.order_id')
    def _price_get(self):
        """
        get and sum the order lines' price
        """
        for order in self:
            order.total = sum(order_line.product_id.price for order_line in order.order_line_ids)

    state = fields.Selection([('new', 'New'), \
                                ('confirmed', 'Confirmed'), \
                                ('cancelled', 'Cancelled'), \
                                ('partially', 'Partially Confirmed')] \
                            , 'Status', readonly=True, select=True, copy=False, default='new')
    alerts = fields.Text(compute='_alerts_get', string="Alerts", default=_default_alerts_get)

    @api.multi
    def _alerts_get(self):
        """
        get the alerts to display on the order form
        """
        for order in self:
            if order.state == 'new':
                order.alerts = self._default_alerts_get()

    @api.multi
    def name_get(self):
        res = []
        for elmt in self:
            res.append((elmt.id, "%s %s" % (_('Lunch Order'), elmt.id)))
        return res


class lunch_order_line(models.Model):
    """
    lunch order line: one lunch order can have many order lines
    """
    _name = 'lunch.order.line'
    _description = 'lunch order line'

    @api.onchange('product_id', 'price')
    def onchange_price(self):
        self.price = self.product_id.price if self.product_id else 0.0

    @api.multi
    def order(self):
        """
        The order_line is ordered to the supplier but isn't received yet
        """
        # when call from wizard we can't get self.ids , need to browse using `active_ids`
        order_lines = self.ids and self or self.browse(self._context.get('active_ids'))
        for order_line in order_lines:
            order_line.state = 'ordered'
        return order_lines._update_order_lines()

    @api.multi
    def confirm(self):
        """
        confirm one or more order line, update order status and create new cashmove
        """
        order_lines = self.ids and self or self.browse(self._context.get('active_ids'))
        cashmove_ref = self.env['lunch.cashmove']
        for order_line in order_lines:
            if order_line.state != 'confirmed':
                values = {
                    'user_id': order_line.user_id.id,
                    'amount': -order_line.price,
                    'description': order_line.product_id.name,
                    'order_id': order_line.id,
                    'state': 'order',
                    'date': order_line.date,
                }
                cashmove_ref.create(values)
                order_line.state = 'confirmed'
        return self._update_order_lines()

    @api.multi
    def _update_order_lines(self):
        """
        Update the state of lunch.order based on its orderlines
        """
        orders = []
        for order_line in self:
            orders.append(order_line.order_id)
        for order in set(orders):
            isconfirmed = True
            for orderline in order.order_line_ids:
                if orderline.state == 'new':
                    isconfirmed = False
                if orderline.state == 'cancelled':
                    isconfirmed = False
                    order.state = 'partially'
            if isconfirmed:
                order.state = 'confirmed'
        return {}

    @api.multi
    def cancel(self):
        """
        cancel one or more order.line, update order status and unlink existing cashmoves
        """
        order_lines = self.ids and self or self.browse(self._context.get('active_ids'))
        for order_line in order_lines:
            order_line.state = 'cancelled'
            order_line.cashmove.unlink()
        return order_lines._update_order_lines()

    name = fields.Char(string='name', related='product_id.name', readonly=True)
    order_id = fields.Many2one('lunch.order', 'Order', ondelete='cascade')
    product_id = fields.Many2one('lunch.product', 'Product', required=True)
    date = fields.Date(string='Date', related='order_id.date', readonly=True, store=True)
    supplier = fields.Many2one('res.partner', string='Supplier', related='product_id.supplier', readonly=True, store=True)
    user_id = fields.Many2one('res.users', string='User', related='order_id.user_id', readonly=True, store=True)
    note = fields.Text('Note')
    price = fields.Float("Price")
    state = fields.Selection([('new', 'New'), \
                                ('confirmed', 'Received'), \
                                ('ordered', 'Ordered'),  \
                                ('cancelled', 'Cancelled')], \
                            'Status', readonly=True, select=True , default='new')
    cashmove = fields.One2many('lunch.cashmove', 'order_id', 'Cash Move', ondelete='cascade')


class lunch_product(models.Model):
    """
    lunch product
    """
    _name = 'lunch.product'
    _description = 'lunch product'

    name = fields.Char('Product', required=True)
    category_id = fields.Many2one('lunch.product.category', 'Category', required=True)
    description = fields.Text('Description', size=256)
    price = fields.Float('Price', digits=(16, 2))  #TODO: use decimal precision of 'Account', move it from product to decimal_precision
    supplier = fields.Many2one('res.partner', 'Supplier')


class lunch_product_category(models.Model):
    """
    lunch product category
    """
    _name = 'lunch.product.category'
    _description = 'lunch product category'

    name = fields.Char('Category', required=True)  #such as PIZZA, SANDWICH, PASTA, CHINESE, BURGER, ...


class lunch_cashmove(models.Model):
    """
    lunch cashmove => order or payment
    """
    _name = 'lunch.cashmove'
    _description = 'lunch cashmove'

    user_id = fields.Many2one('res.users', 'User Name', required=True, default=lambda self: self.env.uid)
    date = fields.Date('Date', required=True, default=fields.Date.context_today)
    amount = fields.Float('Amount', required=True)  #depending on the kind of cashmove, the amount will be positive or negative
    description = fields.Text('Description')  #the description can be an order or a payment
    order_id = fields.Many2one('lunch.order.line', 'Order', ondelete='cascade')
    state = fields.Selection([('order', 'Order'), ('payment', 'Payment')], 'Is an order or a Payment', default='payment')


class lunch_alert(models.Model):
    """
    lunch alert
    """
    _name = 'lunch.alert'
    _description = 'Lunch Alert'

    message = fields.Text('Message', size=256, required=True)
    alter_type = fields.Selection([('specific', 'Specific Day'), \
                                ('week', 'Every Week'), \
                                ('days', 'Every Day')], \
                            string='Recurrency', required=True, select=True, default='specific')
    specific_day = fields.Date('Day', default=fields.Date.context_today)
    monday = fields.Boolean('Monday')
    tuesday = fields.Boolean('Tuesday')
    wednesday = fields.Boolean('Wednesday')
    thursday = fields.Boolean('Thursday')
    friday = fields.Boolean('Friday')
    saturday = fields.Boolean('Saturday')
    sunday = fields.Boolean('Sunday')
    active_from = fields.Float('Between', required=True, default=7)
    active_to = fields.Float('And', required=True, default=23)
