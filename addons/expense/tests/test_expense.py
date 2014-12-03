from openerp.tests.common import TransactionCase

class TestExpense(TransactionCase):

    def setUp(self):
        super(TestExpense, self).setUp()
        
    def test_expense(self):
        expense = self.env['expense']
        expense_sheet = self.env['expense.sheet']
        
        currency_EUR = self.env['ir.model.data'].xmlid_to_res_id('base.EUR')
        employee_parker = self.env['ir.model.data'].xmlid_to_res_id('hr.employee_fp')
        product_air_ticket = self.env['ir.model.data'].xmlid_to_res_id('expense.air_ticket')
        
        expense_line = expense.create({
            'name': 'Car Travel Expenses',
            'employee_id': employee_parker,
            'product_id': product_air_ticket,
            'state': 'confirm'
        })

        sep_expenses = expense_sheet.create({
            'employee_id': employee_parker,
            'name': 'John Smith',
            'expense_id': expense_line.id,
        })
    
        
        #
        expense_line.expense_line_submit_to_approved_status()
        sep_expenses.expense_confirm()
        self.assertTrue((sep_expenses.state, 'confirm'),"Expense should be in Confirm state.")
        
        #
        sep_expenses.signal_workflow('expense_accept')
        self.assertTrue((sep_expenses.state, 'accepted'),"Expense should be in Approved state.")
        

