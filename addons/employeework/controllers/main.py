from openerp.addons.web import http
from openerp.addons.web.http import request
from datetime import datetime, timedelta, date
from math import ceil

def read_data(date, desc = ""):
    model = request.registry['hr.analytic.timesheet']
    if desc == "project":
        return model.search_read(request.cr, request.uid, [], ['account_id'])
    else:
        return model.search_read(request.cr, request.uid, [('date','=', date)])

def get_data(project_id, date):
    model = request.registry['hr.analytic.timesheet']
    return model.search_read(request.cr, request.uid, [('account_id','=',project_id),('date','=',date)], ['id','unit_amount'])

def get_diff(record_id):
    model = request.registry['hr.analytic.timesheet']
    date = model.search_read(request.cr, request.uid, [('id','=',int(record_id))], ['date_counter','unit_amount'])[0]
    diff = datetime.now() - datetime.strptime(date['date_counter'],"%Y-%m-%d %H:%M:%S.%f")
    mints = diff.seconds / 60
    hours = mints / 60
    final_diff = '<span class="hour">%dH</span> <span class="minute">%dM</span>' % (hours,mints)
    return str(final_diff)

def get_day_and_total(date):
    dictonary, grand_total = [], 0
    for date in list(get_week(date)):
        count = sum([float(_date['unit_amount']) for _date in read_data(date)])
        grand_total += count
        dictonary.append({'dates' : date,'count' : count})
    dictonary.append({'dates' : '', 'grand_total' : grand_total})
    return dictonary

#Get list of 7 days in week
def get_week(date):
    date -= timedelta(days = (date.weekday() + 1) % 7)
    for n in xrange(7):
        yield date
        date += timedelta(days=1)

class Employeework(http.Controller):

    @http.route('/employeework', type='http', auth="user", website=True, multilang=True)
    def employeework_home(self):
        now = datetime.now().date()
        return request.website.render('employeework.home',{
            'active': 'date',
            'current_date' : now,
            'data' : read_data(now),
            'date_list' : get_day_and_total(now),
            'get_diff': get_diff})

    @http.route('/employeework/dateview', type='http', auth="user", website=True, multilang=True)
    def employeework_dateview(self, active, current_date):
        date_list = get_day_and_total(datetime.strptime(current_date,"%Y-%m-%d"))
        return request.website.render('employeework.home',{
            'active': active,
            'current_date' : datetime.strptime(current_date,"%Y-%m-%d"),
            'data' : read_data(current_date),
            'date_list' : date_list,
            'get_diff': get_diff})

    @http.route('/employeework/weekview', type='http', auth="user", website=True, multilang=True)
    def employeework_weekview(self, active, current_date):
        current_date = datetime.strptime(current_date,"%Y-%m-%d")
        date_list = list(get_week(current_date))

        project_list = {prj['account_id'][0] : prj['account_id'][1] for prj in read_data('', 'project')}

        row_total = {i.strftime("%Y-%m-%d") : 0 for i in date_list}

        week_data = []
        for prj in project_list.keys():
            unit_amount=[]
            prj_detail = {'project_id' : prj, 'project_name' : project_list[prj], 'duration' : unit_amount}
            for dt in date_list:
                date = dt.strftime("%Y-%m-%d")
                total = sum([float(r['unit_amount']) for r in get_data(prj, date)])
                row_total[date] = row_total[date] + total
                unit_amount.append({'total' : total, 'date' : date})
                prj_detail['duration'] = unit_amount
                prj_detail.update({'total' : sum(t['total'] for t in unit_amount)})
            week_data.append(prj_detail)

        sort_list = [row_total[i] for i in sorted(row_total.keys())]

        return request.website.render('employeework.home',{
            'active': active,
            'week_data' : week_data,
            'current_date' : current_date,
            'date_list' : date_list,
            'row_total' : sort_list})

    @http.route('/employeework/editdata', type='http', auth="user", website=True, multilang=True)
    def employeework_editdata(self, hour, date, project_id):
        now = datetime.now().strftime("%H:%M:%S")

        model = request.registry['hr.analytic.timesheet']
        data = get_data(int(project_id), date)
        if len(data) == 0:
            model.create(request.cr, request.uid, {'name' : '/','journal_id' : request.uid, 'unit_amount' : hour, 'date' : date, 'account_id' : project_id})
        else:
            diff = float(hour) - float(sum([l['unit_amount'] for l in data]))
            slash = model.search_read(request.cr, request.uid, [('account_id','=',int(project_id)),('date','=',date),('name','=','/')],['id','unit_amount'])
            id_list = [l['id'] for l in slash]
            hour_list = sum([l['unit_amount'] for l in slash])
            if len(id_list) == 1:
                if(float(hour_list)+diff<0):
                    return now
                model.write(request.cr, request.uid, id_list, {'unit_amount' : float(hour_list)+diff})
            else:
                model.create(request.cr, request.uid, {'name' : '/','journal_id' : request.uid, 'unit_amount' : diff, 'date' : date, 'account_id' : project_id})
        return now

    @http.route('/employeework/addcounter', type='http', auth="user", website=True, multilang=True)
    def employeework_addcounter(self, record_id):
        model = request.registry['hr.analytic.timesheet']
        model.write(request.cr, request.uid, [int(record_id)], {'date_counter' : datetime.now()})

    @http.route('/employeework/removecounter', type='http', auth="user", website=True, multilang=True)
    def employeework_removecounter(self, record_id):
        model = request.registry['hr.analytic.timesheet']
        date = model.search_read(request.cr, request.uid, [('id','=',int(record_id))], ['date_counter','unit_amount'])[0]
        diff = datetime.now() - datetime.strptime(date['date_counter'],"%Y-%m-%d %H:%M:%S.%f")
        mints = diff.seconds / 60
        hours = mints / 60
        final_diff = float("%d.%d" % (hours,mints))
        model.write(request.cr, request.uid, [int(record_id)], {'unit_amount' : final_diff + float(date['unit_amount']), 'date_counter' : None})
        return str(final_diff)