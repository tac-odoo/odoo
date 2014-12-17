from openerp.tests.common import TransactionCase

class TestExpense(TransactionCase):

    def setUp(self):
        super(TestExpense, self).setUp()
        
    def test_expense(self):
        #use a ref
        currency_EUR = self.env.ref('base.EUR').id
        emp_administrator = self.env.ref('hr.employee').id
        product_air_ticket = self.env.ref('hr_expense.air_ticket').id
        employee_account = self.env.ref('account.a_pay').id
        
        expense = self.env['hr_expense.expense'].create({
            'name': 'Car Travel Expenses',
            'employee_id': emp_administrator,
            'product_id': product_air_ticket,
        })
        
        #write a exmployee account in expense sheet
        expense.write({'expense_id': self.env['hr_expense.sheet'].create({
            'employee_payable_account_id': employee_account}).id,
        })

        expense.expense_line_new_to_confirm_status()
        self.assertEquals(expense.state, 'confirm', "Expense should be in Confirm state.")
        
        #Check that Expense sheet state is 'draft'.
        self.assertEquals(expense.expense_id.state, 'draft', "Expense sheet should be in draft state.")
        
        #Check that Expense sheet state is 'draft'.
        expense.expense_id.signal_workflow('confirm')
        self.assertEquals(expense.expense_id.state, 'confirm', "Expense sheet should be in confirm state.")
        
        #I approve the expenses sheet.
        expense.expense_line_submit_to_approved_status()
        expense.expense_id.signal_workflow('validate')
        self.assertEquals(expense.expense_id.state, 'accepted', "Expense sheet should be in accepted state.")
        
        #Check receipt details.
        expense.expense_id.signal_workflow('done')
        self.assertEquals(expense.expense_id.state, 'done', "Expense sheet should be in done state.")
        
        #Duplicate the expenses and cancel duplicated.
        duplicate_expense = expense.expense_id.copy()
        duplicate_expense.expense_canceled()
        self.assertEquals(duplicate_expense.state, 'cancelled', "Expense sheet should be in cancel state.")
        