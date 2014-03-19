
from openerp.osv import osv, fields
import csv
import base64
import StringIO
from datetime import datetime
import pytz
from openerp import SUPERUSER_ID
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
from operator import itemgetter

class attendances_import(osv.osv):
	_name = 'attendances.import'
	_columns = {
		'name': fields.char('Name', size=64, required=True, readonly=True, states={'draft': [('readonly', False)]}),
		'create_date': fields.datetime('Create Date', readonly=True, select=True),
		'import_date': fields.datetime('Import Date', readonly=True,),
		'process_date': fields.datetime('Process Date', readonly=True,),
		'input_file': fields.binary('Import File', required=True),
		'attendance_line_ids': fields.one2many('attendances.import.line', 'hr_import_id', 'Attendance Lines'),
		'state': fields.selection([
					('draft', 'Draft'),
					('import', 'Imported'),
					('process', 'Processed')], 'State', readonly=True),
	}

	_defaults = {
		'state': 'draft'
	}

	def import_attendances(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		attendance_line_obj = self.pool.get('attendances.import.line')

		total_import = 0
		for line in self.browse(cr, uid, ids, context=context):
			lines = csv.reader(StringIO.StringIO(base64.b64decode(line.input_file)), quotechar=' ')
			header = lines.next()
			for ln in lines:
				line_value = dict(zip(header, ln))
				if line_value:
					user_date = datetime.strptime(line_value['CHECKTIME'], '%d/%m/%Y %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
					attendance_line_obj.create(cr, uid, {
						'hr_import_id': ids[0],
						'user': line_value['USERID'],
						'check_date': self.date_to_datetime(cr, uid, user_date),
						'machine': line_value['SENSORID'],
						'card_no': line_value['CardNo'],
					})

		self.write(cr, uid, ids, {'state': 'import', 'import_date': fields.datetime.now()}, context=context)

		return True

	def process_attendaces(self, cr, uid, ids, context=None):
		if context is None:
			context = {}

		attendance_obj = self.pool.get('hr.attendance')
		employee_obj = self.pool.get('hr.employee')
		import_line_obj = self.pool.get('attendances.import.line')

		super_employee_dict = {}

		employee_ids = employee_obj.search(cr, uid, [])
		for emp in employee_obj.browse(cr, uid, employee_ids, context=context):
			if emp.otherid:
				super_employee_dict = {}
				import_line_ids = import_line_obj.search(cr, uid, [('hr_import_id', 'in', ids), ('card_no', '=', emp.otherid)], order='check_date')
				for import_line in import_line_obj.browse(cr, uid, import_line_ids, context=context):
					res = {}
					if import_line.machine in ['101', '103']:
						res = {
							'employee_id': emp.id,
							'name': import_line.check_date,
							'action': 'sign_in',
						}
					elif import_line.machine in ['102', '104']:
						res = {
							'employee_id':  emp.id,
							'name': import_line.check_date,
							'action': 'sign_out',
						}
					if import_line.check_date:
						import_line_date = import_line.check_date.split()
						if len(import_line_date) > 1:
							check_date = import_line_date[0]
							if check_date in super_employee_dict:
								super_employee_dict[check_date].append(res)
							else:
								super_employee_dict.update({check_date: [res]})
			self.create_attendance(cr, uid, super_employee_dict, context=context)

		self.write(cr, uid, ids, {'state': 'process', 'process_date': fields.datetime.now()}, context=context)
		return True

	def date_to_datetime(self, cr, uid, userdate, context=None):
		user_date = datetime.strptime(userdate, DEFAULT_SERVER_DATETIME_FORMAT)
		if context and context.get('tz'):
		    tz_name = context['tz']
		else:
		    tz_name = self.pool.get('res.users').read(cr, SUPERUSER_ID, uid, ['tz'])['tz']
		if tz_name:
		    utc = pytz.timezone('UTC')
		    context_tz = pytz.timezone(tz_name)
		    user_datetime = user_date
		    local_timestamp = context_tz.localize(user_datetime, is_dst=False)
		    user_datetime = local_timestamp.astimezone(utc)
		    return user_datetime.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
		return user_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

	def create_attendance(self, cr, uid, super_employee_dict, context=None):
		ss = sorted(super_employee_dict)
		atten_obj = self.pool.get('hr.attendance')

		for key in ss:
			attendances_lst = sorted(super_employee_dict[key], key=itemgetter('name'))
			aa_lst = []

			for att in attendances_lst:
				if len(aa_lst) >= 1:
					last_att = aa_lst[-1]
					if last_att['action'] == att['action'] and last_att['action'] == 'sign_in':
						last_att.update({'name': att['name']})
					elif last_att['action'] == att['action'] and last_att['action'] == 'sign_out':
						continue
					else:
						aa_lst.append(att)
				else:
					if att['action'] == 'sign_in':
						aa_lst.append(att)

					elif att['action'] == 'sign_out':
						first_att = att.copy()
						first_att['action'] = 'sign_in'
						first_date = (datetime.strptime(att['name'], '%Y-%m-%d %H:%M:%S') - relativedelta(minutes = 1)).strftime('%Y-%m-%d %H:%M:%S')
						first_att['name'] = first_date
						aa_lst.insert(0, first_att)
						aa_lst.append(att)

			if len(aa_lst) >= 1:
				check_last = aa_lst[-1]
				if check_last['action'] == 'sign_in':
					last_att = check_last.copy()
					last_date = (datetime.strptime(att['name'], '%Y-%m-%d %H:%M:%S') + relativedelta(minutes = 1)).strftime('%Y-%m-%d %H:%M:%S')
					last_att['action'] = 'sign_out'
					last_att['name'] = last_date
					aa_lst.append(last_att)

			for r in aa_lst:
				atten_obj.create(cr, uid, r)
		return True

attendances_import()

class attendances_import_line(osv.osv):
	_name = 'attendances.import.line'
	_columns = {
	    'hr_import_id': fields.many2one('attendances.import', 'Attendances Import', ondelete='cascade'),
		'user': fields.char('User', size=64),
		'check_date': fields.datetime('Check Time'),
		'machine': fields.char('Machine', size=64),
		'card_no': fields.char('Card Number', size=256)
	}

attendances_import_line()

