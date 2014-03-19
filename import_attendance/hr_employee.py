
from openerp.osv import osv, fields



class hr_employee(osv.osv):
    _inherit = 'hr.employee'
    _columns = {
        'excepted_total_time': fields.float('Excepted Total Time')
    }