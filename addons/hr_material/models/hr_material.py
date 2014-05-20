from lxml import etree

from openerp import models, fields, api, _
from openerp.exceptions import except_orm
from openerp.tools import html2plaintext

class maintenance_request_stage(models.Model):
    """Stages for Kanban view of Maintenance Request"""

    _name = 'maintenance.request.stage'
    _description = 'Maintenance Request Stage'
    _order = 'sequence asc'

    name = fields.Char('Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=1)
    fold = fields.Boolean('Folded in Kanban View')

    _sql_constraints = [
        ('positive_sequence', 'CHECK(sequence >= 0)', 'Sequence number MUST be a natural')
    ]

class hr_material_category(models.Model):
    _name = 'hr.material.category'
    _inherits = {"mail.alias": "alias_id"}
    _inherit = ['mail.thread']
    _description = 'Material Category'

    @api.one
    def _count(self):
        self.material_count = len(self.material_ids)
        self.maintenance_count = len(self.maintenance_ids)

    name = fields.Char('Category Name', required=True, translate=True)
    user_id = fields.Many2one('res.users', 'Responsible', track_visibility='onchange', default = lambda self: self.env.uid)
    color = fields.Integer('Color Index')
    note = fields.Text('Comments', translate=True)
    material_ids = fields.One2many('hr.material', 'category_id', string='Materials', copy=False)
    material_count = fields.Integer(compute='_count', string="Material")
    maintenance_ids = fields.One2many('hr.material.maintenance_request', 'category_id', copy=False, domain=[('stage_id.fold', '=', False)])
    maintenance_count = fields.Integer(compute='_count', string="Maintenance")
    alias_id = fields.Many2one('mail.alias', 'Alias', ondelete="restrict", required=True,
        help="Email alias for this material category. New emails will automatically "
             "create new maintenance request for this material category.")

    @api.model
    def create(self, vals):
        self = self.with_context(alias_model_name='hr.material.maintenance_request', alias_parent_model_name=self._name)
        category_id = super(hr_material_category, self).create(vals)
        category_id.alias_id.write({'alias_parent_thread_id': category_id.id, 'alias_defaults': {'category_id': category_id.id}})
        return category_id

    @api.multi
    def unlink(self):
        alias_ids = []
        for category in self:
            if category.material_ids or category.maintenance_ids:
                raise except_orm(_('Invalid Action!'),
                                     _('You cannot delete a Material Category containing Material/Maintenance Request. You can either delete all the material/maintenance which belongs to in this category and then delete the material category.'))
            elif category.alias_id:
                alias_ids.append(category.alias_id.id)
        res = super(hr_material_category, self).unlink()
        self.env['mail.alias'].browse(alias_ids).unlink()
        return res



class hr_material(models.Model):
    _name = 'hr.material'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = 'Material'
    _track = {
        'employee_id': {
            'hr_material.mt_mat_assign': lambda self, cr, uid, obj, ctx = None: obj.employee_id,
        },
        'department_id': {
            'hr_material.mt_mat_assign': lambda self, cr, uid, obj, ctx = None: obj.department_id,
        },
    }

    @api.one
    def _maintenance_count(self):
        self.maintenance_count = len(self.maintenance_ids)

    name = fields.Char('Name', required=True, translate=True)
    user_id = fields.Many2one('res.users', string='Technician', track_visibility='onchange')
    employee_id = fields.Many2one('hr.employee', string='Assigned to Employee', track_visibility='onchange')
    department_id = fields.Many2one('hr.department',
        string='Assigned to Department',
        track_visibility='onchange')
    category_id = fields.Many2one('hr.material.category', string='Category', track_visibility='onchange')
    partner_id = fields.Many2one('res.partner', string='Supplier', domain="[('supplier', '=', 1)]")
    model = fields.Char('Model')
    serial_no = fields.Char('Serial Number', copy=False)
    assign_date = fields.Date('Assigned Date', track_visibility='onchange')
    cost = fields.Float('Cost')
    note = fields.Text('Note', translate=True)
    color = fields.Integer('Color Index')
    scrap_date = fields.Date('Scrap Date')
    material_assign_to = fields.Selection(
        [('employee', 'By Employee'), ('department', 'By Department')],
        string='Assigned to',
        help='By Employee: Material assigned to individual Employee, By Department: Material assigned to group of employees in department',
        required=True,
        default='employee')
    maintenance_ids = fields.One2many('hr.material.maintenance_request', 'material_id', domain=[('stage_id.fold', '=', False)])
    maintenance_count = fields.Integer(compute='_maintenance_count', string="Maintenance")


    _sql_constraints = [
        ('serial_no', 'unique(serial_no)', "The serial number of this material must be unique !"),
    ]


    @api.model
    def create(self, vals):
        if 'employee_id' in vals or 'department_id' in vals:
            if vals.get('employee_id') or vals.get('department_id'):
                vals['assign_date'] = fields.Date.context_today(self)
        material = super(hr_material, self).create(vals)
        # subscribe employee or department manager when material assign to him.
        if material.employee_id and material.employee_id.user_id:
            material.message_subscribe_users(user_ids=[material.employee_id.user_id.id])
        if material.department_id and material.department_id.manager_id and material.department_id.manager_id.user_id:
            material.message_subscribe_users(user_ids=[material.department_id.manager_id.user_id.id])
        return material

    @api.multi
    def write(self, vals):
        # subscribe employee or department manager when material assign to employee or department.
        if vals.get('employee_id'):
            user_id = self.env['hr.employee'].browse(vals['employee_id'])['user_id']
            if user_id:
                self.message_subscribe_users(user_ids=[user_id.id])
        if vals.get('department_id'):
            department = self.env['hr.department'].browse(vals['department_id'])
            if department and department.manager_id and department.manager_id.user_id:
                self.message_subscribe_users(user_ids=[department.manager_id.user_id.id])

        return super(hr_material, self).write(vals)

    @api.onchange('material_assign_to')
    def _onchange_material_assign_to(self):
        if self.material_assign_to == 'employee':
            self.department_id = False
        if self.material_assign_to == 'department':
            self.employee_id = False

    @api.onchange('category_id')
    def _onchange_category_id(self):
        self.user_id = self.category_id.user_id.id


class hr_material_maintenance_request(models.Model):
    _name = 'hr.material.maintenance_request'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = 'Maintenance Request'
    _track = {
        'stage_id': {
            'hr_material.mt_req_created': lambda self, cr, uid, obj, ctx = None: obj.stage_id and obj.stage_id.sequence <= 1,
            'hr_material.mt_req_status': lambda self, cr, uid, obj, ctx = None: obj.stage_id and obj.stage_id.sequence > 1,
        } }

    @api.one
    def _employee_get(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1).id

    @api.one
    def _default_stage(self):
        return self.env['maintenance.request.stage'].search([], limit=1).id

    name = fields.Char('Subjects', required=True, translate=True)
    description = fields.Text('Description')
    request_date = fields.Date('Request Date',
        track_visibility='onchange',
        default=fields.Date.context_today)
    employee_id = fields.Many2one('hr.employee', string='Employee', default=_employee_get)
    department_id = fields.Many2one('hr.department', string='Department')
    category_id = fields.Many2one('hr.material.category', string='Category')
    material_id = fields.Many2one('hr.material', string='Material')
    user_id = fields.Many2one('res.users', string='Assigned to', track_visibility='onchange')
    stage_id = fields.Many2one('maintenance.request.stage',
        string='Stage', ondelete='set null',
        track_visibility='onchange',
        default=_default_stage,
        )
    priority = fields.Selection(
        [('0', 'Very Low'), ('1', 'Low'), ('2', 'Normal'), ('3', 'High'), ('4', 'Very High'),],
        string='Priority', select=True)
    color = fields.Integer('Color Index')
    close_date = fields.Date('Close Date')

    @api.v7
    def _read_group_stage_ids(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context=None):
        """ Read group customization in order to display all the stages in the
        kanban view, even if they are empty """
        stage_obj = self.pool.get('maintenance.request.stage')
        order = stage_obj._order
        access_rights_uid = access_rights_uid or uid

        if read_group_order == 'stage_id desc':
            order = '%s desc' % order

        stage_ids = stage_obj._search(cr, uid, [], order=order, access_rights_uid=access_rights_uid, context=context)
        result = stage_obj.name_get(cr, access_rights_uid, stage_ids, context=context)

        # restore order of the search
        result.sort(lambda x, y: cmp(stage_ids.index(x[0]), stage_ids.index(y[0])))

        fold = {}
        for stage in stage_obj.browse(cr, access_rights_uid, stage_ids, context=context):
            fold[stage.id] = stage.fold or False
        return result, fold

    _group_by_full = {
        'stage_id': _read_group_stage_ids
    }

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        # override of fields_view_get in order to remove the clickable attribute from stage when user is not HRmanager
        res = super(hr_material_maintenance_request, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if not self.env['res.users'].has_group('base.group_hr_manager'):
            if view_type == 'form':
                doc = etree.XML(res['arch'])
                for node in doc.xpath("//field[@name='stage_id']"):
                    if node.attrib['clickable']: del node.attrib['clickable']
                res['arch'] = etree.tostring(doc)
        return res

    @api.model
    def message_new(self, msg, custom_values=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        if custom_values is None:
            custom_values = {}
        if 'category_id' in custom_values:
            custom_values['user_id'] = self.env['hr.material.category'].browse(custom_values['category_id'])['user_id']
        desc = html2plaintext(msg.get('body')) if msg.get('body') else ''

        defaults = {
            'name':  msg.get('subject') or _("No Subject"),
            'description': desc,
            'employee_id': False,
        }
        defaults.update(custom_values)
        return super(hr_material_maintenance_request, self).message_new(msg, custom_values=defaults)

    @api.model
    def create(self, vals):
        # context: no_log, because subtype already handle this
        self = self.with_context(mail_create_nolog=True)
        return super(hr_material_maintenance_request, self).create(vals)

    @api.one
    def set_priority(self, priority, *args):
        """Set priority
        """
        return self.write({'priority' : priority})

    @api.onchange('employee_id', 'department_id')
    def onchange_department_or_employee_id(self):
        domain = []
        if self.department_id:
            domain = [('department_id', '=', self.department_id.id)]
        if self.employee_id and self.department_id:
            domain = ['|'] + domain
        if self.employee_id:
            domain = domain + [('employee_id', '=', self.employee_id.id)]
        return {'domain': {'material_id': domain}}

    @api.onchange('material_id')
    def onchange_material_id(self):
        if not self.material_id:
            return False
        self.user_id = self.material_id.user_id.id
        self.category_id = self.material_id.category_id

    @api.onchange('category_id')
    def onchange_category_id(self):
        if not self.category_id:
            return False
        self.user_id = self.category_id.user_id.id

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
