from openerp.addons.web import http
from openerp.addons.web.http import request
from datetime import datetime, timedelta, date
from math import ceil

def read_data(date):
    model = request.registry['hr.analytic.timesheet']
    return model.search_read(request.cr, request.uid, [('date','=', datetime.now().date())] if date == "" else [('date','=', date)])

def get_project():
    model = request.registry['hr.analytic.timesheet']
    return model.search_read(request.cr, request.uid, [],['account_id'])

def get_data(project_id, date):
    model = request.registry['hr.analytic.timesheet']
    return model.browse(request.cr, request.uid, model.search(request.cr, request.uid, [('account_id','=',project_id),('date','=',date)])) 

def get_day_and_total(date):
    dictonary, grand_total = [], 0
    for date in list(get_week(date)):
        count = sum([float(_date['unit_amount']) for _date in read_data(str(date))])
        grand_total = grand_total + count
        dictonary.append({'dates' : date,'count' : count})
    dictonary.append({'dates' : '', 'grand_total' : grand_total})
    return dictonary

def get_week(date):
    day_idx = (date.weekday() + 1) % 7
    date = date - timedelta(days = day_idx)
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
            'data' : read_data(""),
            'date_list' : get_day_and_total(now)})

    @http.route('/employeework/dateview', type='http', auth="user", website=True, multilang=True)
    def employeework_dateview(self, active, current_date):
        date_list = get_day_and_total(datetime.strptime(current_date,"%Y-%m-%d"))
        return request.website.render('employeework.home',{
            'active': active,
            'current_date' : datetime.strptime(current_date,"%Y-%m-%d"),
            'data' : read_data(current_date),
            'date_list' : date_list})

    @http.route('/employeework/weekview', type='http', auth="user", website=True, multilang=True)
    def employeework_weekview(self, active, current_date):
        current_date = datetime.strptime(current_date,"%Y-%m-%d")
        start_end_date = list(get_week(current_date))
        date_list = get_day_and_total(current_date)

        print date_list[0]['dates']

        project_list = {}
        for prj in get_project():
            project_list.update({prj['account_id'][0] : prj['account_id'][1]})

        row_total = {}
        for i in start_end_date:
            row_total.update({i.strftime("%Y-%m-%d") : 0})

        lst = []
        for prj in project_list.keys():
            unit_amount=[]
            prj_detail = {'project_id' : prj, 'project_name' : project_list[prj], 'duration' : unit_amount}
            for dt in list(get_week(current_date)):
                date = dt.strftime("%Y-%m-%d")
                total = sum([float(r.unit_amount) for r in get_data(prj, date)])
                row_total[date] = row_total[date] + total
                unit_amount.insert(len(unit_amount), total)
                prj_detail['duration'] = unit_amount
                prj_detail.update({'total' : sum(unit_amount)})
            lst.append(prj_detail)

        sort_list = [row_total[i] for i in sorted(row_total.keys())]

        return request.website.render('employeework.home',{
            'start_date' : start_end_date[0],
            'end_date' : start_end_date[6],
            'active': active,
            'week_data' : lst,
            'current_date' : current_date,
            'date_list' : date_list,
            'row_total' : sort_list})

    @http.route('/employeework/editdata', type='http', auth="user", website=True, multilang=True)
    def employeework_editdata(self, hour, date_index, project_id, current_date):
        current_date = datetime.strptime(current_date,"%Y-%m-%d")
        
        date_list = get_day_and_total(current_date)
        date = date_list[int(date_index) - 1]['dates']

        model = request.registry['hr.analytic.timesheet']
        data = get_data(int(project_id), date.strftime("%Y-%m-%d"))

        lst = [rec.id for rec in data]
        dict_data = {'name' : 'Demo','journal_id' : request.uid, 'unit_amount' : hour, 'date' : date, 'account_id' : project_id}
        if len(lst)==0:
            i = model.create(request.cr, request.uid, dict_data)
        else:
            i = model.write(request.cr, request.uid, lst, dict_data)

        del_data = model.search(request.cr, request.uid, [('unit_amount','=',0)])
        model.unlink(request.cr, request.uid, del_data)
        return ''