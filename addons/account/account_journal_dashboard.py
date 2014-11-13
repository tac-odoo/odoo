import json
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from openerp import models, api, _, fields

class account_invoice(models.Model):
    _inherit = "account.invoice"

    @api.multi
    def _prepare_where_clause_dashboard(self, journal_id):
        journal_id_clause_operator = '='
        company_id = self.env['account.journal'].browse(journal_id).company_id.id
        fiscalyear_id = self.env['account.journal'].find_fiscalyear(company_id)
        where_clause = "journal_id = %s AND company_id = %s" % (journal_id, company_id)
        fiscalyear_id = set(fiscalyear.id for fiscalyear in fiscalyear_id)
        if fiscalyear_id:
            where_clause += " AND period_id in \
                            (SELECT account_period.id \
                            FROM account_period \
                            WHERE fiscalyear_id in (%s))" % ','.join(map(str, filter(None, fiscalyear_id)))
        return where_clause

    @api.multi
    def _get_remaining_payment_stats(self, journal_id):
        where_clause = self._prepare_where_clause_dashboard(journal_id)
        self._cr.execute("SELECT date_due, sum(residual)\
                    FROM account_invoice\
                    WHERE %s\
                    AND state = 'open'\
                    GROUP BY date_due" % where_clause)
        residual_values = self._cr.fetchall()
        todo_payment_amount = overdue_amount_today = overdue_amount_month = 0

        overdue_month_end_date = date.today() + relativedelta(day=1, months=+1, days=-1)
        for date_due, overdue_invoice_amount in residual_values:
            todo_payment_amount +=  overdue_invoice_amount
            due_date = datetime.strptime(date_due,"%Y-%m-%d").date()
            if due_date <= date.today():
                overdue_amount_today += overdue_invoice_amount
            if due_date <= overdue_month_end_date:
                overdue_amount_month += overdue_invoice_amount
        res = {
            'overdue_invoice_amount' : overdue_amount_today,
            'overdue_invoice_amount_month': overdue_amount_month,
            'todo_payment_amount': todo_payment_amount
        }
        return res

    @api.multi
    def get_stats(self, journal_id):
        where_clause = self._prepare_where_clause_dashboard(journal_id)
        # query will return sum for all open and paid invoice based on period id
        self._cr.execute("SELECT state, sum(amount_total)\
                    FROM account_invoice\
                    WHERE %s\
                    GROUP BY state" % (where_clause))
        invoice_stats = self._cr.fetchall()
        # query will return sum of all draft invoices which has no period_id
        self._cr.execute("SELECT sum(amount_total)\
                    FROM account_invoice\
                    WHERE state in ('draft', 'proforma', 'proforma2')\
                    AND journal_id = %s\
                    GROUP BY state" % (journal_id))

        res = {'draft_invoice_amount': 0, 'open_invoice_amount': 0}
        for amount in self._cr.fetchall():
            res['draft_invoice_amount'] = amount
        for state, amount_total in invoice_stats:
            if state == 'open':   
                res['open_invoice_amount'] = amount_total
        remaining_payment_stats = self._get_remaining_payment_stats(journal_id)
        res.update(remaining_payment_stats)
        return res

class account_journal(models.Model):
    _inherit = "account.journal"

    @api.multi
    def find_fiscalyear(self, company_id):
        context = self._context
        fiscalyear_obj = self.env['account.fiscalyear']
        if context.get('current_year'):
            dt = fields.Date.context_today(self)
            fiscalyear_id = fiscalyear_obj.search([('date_start', '<=' ,dt),('date_stop', '>=', dt),('company_id', '=', company_id)], context=context)
        else:
            fiscalyear_id = fiscalyear_obj.search([])
        if not fiscalyear_id:
            fiscalyear_id = [self.env['account.fiscalyear'].find()]
            fiscalyear_id = self.env['account.fiscalyear'].browse(fiscalyear_id)
        return fiscalyear_id

    @api.one
    def _kanban_dashboard(self):
        self.kanban_dashboard = json.dumps(self.get_journal_dashboard_datas())

    @api.one
    def _kanban_graph(self):
        self.kanban_graph = self._prepare_graph_data()

    kanban_dashboard = fields.Text(compute='_kanban_dashboard')
    kanban_graph = fields.Text(compute='_kanban_graph')

    @api.multi
    def get_journal_dashboard_datas(self):
        balance, date = self._get_last_statement()
        values = self.env['account.invoice'].get_stats(self.id)
        currency_symbol = self.company_id.currency_id.symbol
        if self.currency:
            currency_symbol = self.currency.symbol
        fiscalyear_id = self.find_fiscalyear(self.company_id.id)
        total_reconcile_amount = self.env['account.move.line'].search([('journal_id', '=', self.id), ('period_id.fiscalyear_id', 'in', fiscalyear_id.ids), ('reconcile_partial_id','!=',False)])

        values.update({
            'currency_symbol' : currency_symbol,
            'last_statement_amount' : balance,
            'last_statement_date' : date,
            'total_reconcile_amount' : len(total_reconcile_amount),
            'credit_account_name': self.default_credit_account_id.name,
            'credit_account_balance' : self.default_credit_account_id.balance,
        })
        return values

    @api.multi
    def _get_last_statement(self):
        context = self._context
        balance = 0
        date = 'None'
        statement_obj = self.env['account.bank.statement']
        date_format = self.env['res.lang'].search_read([('code','=', context.get('lang', 'en_US'))], ['date_format'], context=context)[0]['date_format']
        statement_ids = statement_obj.search([('journal_id', '=', self.id)], order='create_date desc', limit=1, context=context)
        #Get last bank statement amount and date.
        if statement_ids:
            statement = statement_obj.browse(statement_ids.ids)
            if statement.journal_id.type == 'cash':
                balance = statement.balance_end
            elif statement.journal_id.type == 'bank':
                balance = statement.balance_end_real
            date = datetime.strptime(str(statement.date), '%Y-%m-%d').date().strftime(date_format)
        return (balance , date)

    @api.multi
    def _prepare_graph_data(self):
        res = False
        #Prepare data to show graph in kanban of journals which will be called from the _kanban_graph method
        if self.type in ['general','situation']:
            return res
        elif self.type in ['cash','bank']:
            res = json.dumps(self._get_moves_per_day())
        elif self.type in ['sale']:
            res = json.dumps(self._get_moves_2_months())
        else:
            res = json.dumps(self._get_moves_per_month())
        return res

    @api.multi
    def _get_moves_per_month(self):
        total = {}
        fiscalyear_obj = self.env['account.fiscalyear']
        fiscalyear_id = self.find_fiscalyear(self.company_id.id)
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        state = ['draft','posted']
        """
            Get amount of moves related to the particular journals per month
            left join on account_move if we want only posted entries then we can use.
            query will return sum of line.debit and month for related sale,purchase,sale_refund,purchase_refund type journal based on period id
        """
        self._cr.execute("SELECT to_char(line.date, 'MM') as month, SUM(line.debit) as amount\
                    FROM account_move_line AS line LEFT JOIN account_move AS move ON line.move_id=move.id\
                    WHERE line.journal_id = %s AND line.period_id in (SELECT account_period.id from account_period WHERE fiscalyear_id in %s) \
                    AND move.state in %s\
                    GROUP BY to_char(line.date, 'MM') \
                    ORDER BY to_char(line.date, 'MM')", (self.id, tuple(fiscalyear_id.ids), tuple(state)))
        values = []
        for month, amount in self._cr.fetchall():
            values.append({
                'x': months[int(month) - 1],
                'y': amount
            })
        data = {
            'values': [],
            'bar': True,
            'color': '#ff7f0e',
        }
        for month in months:
            amount = 0
            for value in values:
                if month == value['x']:
                    amount = value['y']
            data['values'].append({'x': month, 'y': amount})
        return [data]

    @api.multi
    def _get_moves_per_day(self):
        context = self._context
        data = {'values': [], 'color': '#ff7f0e'}
        date_format = self.env['res.lang'].search_read([('code', '=', context.get('lang', 'en_US'))],['date_format'], context=context)[0]['date_format']
        move_date = date.today()-timedelta(days=14)
        fiscalyear_id = self.find_fiscalyear(self.company_id.id)
        """
            Get total transactions per day for related journals
            left join on account_move if we want only posted entries then we can use.
            query will return sum of line.debit and line.date for related cash and bank type journal based on period id
        """
        self._cr.execute("SELECT SUM(line.debit), line.date\
                         FROM account_move_line AS line LEFT JOIN account_move AS move ON line.move_id=move.id\
                         WHERE line.journal_id = %s AND line.period_id in (SELECT account_period.id from account_period WHERE account_period.fiscalyear_id in %s) \
                         AND line.date >= %s\
                         GROUP BY line.date \
                         ORDER BY line.date",(self.id, tuple(fiscalyear_id.ids), move_date))
        for value in self._cr.dictfetchall():
            date_value = datetime.strptime(str(value['date']), '%Y-%m-%d').date().strftime(date_format)
            data['values'].append({
                'x': date_value,
                'y': value['sum']
            })
        if not data['values']:
            data['values'].append({
                'x': datetime.strptime(str(date.today()), '%Y-%m-%d').date().strftime(date_format),
                'y': 0
            })
        return [data]

    @api.multi
    def _get_moves_2_months(self):
        context = self._context
        data_this_month = {'values': [], 'key': 'Current Month', 'color': '#ff7f0e', 'show_legend': True}
        data_last_month = {'values': [], 'key': 'Last Month', 'color': '#2ca02c', 'show_legend': True}
        first_of_this_month = date(day=1, month=date.today().month, year=date.today().year)
        previous_month = first_of_this_month - timedelta(days=1)
        previous_month_date = date(day=1, month=previous_month.month, year=previous_month.year)
        """
            Get amount of moves related to the particular journals per month
            left join on account_move if we want only posted entries then we can use.
            query will return sum of line.debit and month for related sale,purchase,sale_refund,purchase_refund type journal based on period id
        """
        self._cr.execute("SELECT to_char(line.date, 'dd') as day, to_char(line.date,'MM') as month, SUM(line.debit) as amount, line.journal_id\
                    FROM account_move_line AS line LEFT JOIN account_move AS move ON line.move_id=move.id\
                    WHERE line.journal_id = %s \
                    AND move.state = 'posted' AND line.date >= %s\
                    GROUP BY day, month, line.journal_id \
                    ORDER BY day, month, line.journal_id", (self.id, previous_month_date))

        total_amount_this_month = 0
        total_amount_last_month = 0
        this_month = {}
        last_month = {}
        for value in self._cr.dictfetchall():
            if int(value['month']) == first_of_this_month.month:
                if (value['journal_id'] == self.id):
                    total_amount_this_month += value['amount']
                else:
                    total_amount_this_month -= value['amount']
                this_month[int(value['day'])] = total_amount_this_month
            else:
                if (value['journal_id'] == self.id):
                    total_amount_last_month += value['amount']
                else:
                    total_amount_last_month -= value['amount']
                last_month[int(value['day'])] = total_amount_last_month

        temp_amount_curmonth = 0
        temp_amount_lastmonth = 0
        for i in range(1,32):
            if i <= date.today().day:
                if this_month.get(i, False):
                    temp_amount_curmonth = this_month.get(i)
                    data_this_month['values'].append({
                        'x': i,
                        'y': temp_amount_curmonth,
                        })
                else:
                    data_this_month['values'].append({
                        'x': i,
                        'y': temp_amount_curmonth,
                        })
            if len(last_month) != 0:
                if last_month.get(i, False):
                    temp_amount_lastmonth = last_month.get(i)
                    data_last_month['values'].append({
                        'x': i,
                        'y': temp_amount_lastmonth,
                        })
                else:
                    data_last_month['values'].append({
                        'x': i,
                        'y': temp_amount_lastmonth,
                        })
        return [data_this_month, data_last_month]

    @api.multi
    def open_action(self):
        """return action based on type for related journals"""
        action_name = self._context.get('action_name', False)
        if not action_name:
            if self.type == 'bank':
                action_name = 'action_bank_statement_tree'
            elif self.type == 'cash':
                action_name = 'action_view_bank_statement_tree'
            elif self.type == 'sale':
                action_name = 'action_invoice_tree1'
            elif self.type == 'purchase':
                action_name = 'action_invoice_tree2'

        _journal_invoice_type_map = {
            'sale': 'out_invoice',
            'purchase': 'in_invoice',
            'bank': 'bank',
            'cash': 'cash'
        }
        invoice_type = _journal_invoice_type_map[self.type]

        ctx = self._context.copy()
        ctx.update({
            'journal_type': self.type,
            'default_journal_id': self.id,
            'search_default_journal_id': self.id,
            'default_type': invoice_type,
            'type': invoice_type
        })
        domain = [('journal_id.type', '=', self.type),('journal_id', '=', self.id)]
        ir_model_obj = self.pool['ir.model.data']
        model, action_id = ir_model_obj.get_object_reference(self._cr, self._uid, 'account', action_name)
        action = self.pool[model].read(self._cr, self._uid, action_id, context=self._context)
        action['context'] = ctx
        action['domain'] = domain
        return action

    @api.multi
    def add_remove_journal_favorite(self):
        """set or remove a journal from favorite kanban view"""
        self.write({'dashboard_star': False if self.dashboard_star else True,})
