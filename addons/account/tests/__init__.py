from . import test_tax
from . import test_search
from . import test_reconciliation
from . import test_account_move_closed_period

fast_suite = [
	test_tax,
	test_search,
	test_reconciliation,
	test_account_move_closed_period
]
