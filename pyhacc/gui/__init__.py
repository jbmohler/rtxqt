from .accounts import *
from .journals import *
from .transactions import *
from .widgets import *

from .roscoe import *

from . import monthly
from . import tranreports

class AccountingExtensions:
    def show_link_parented(self, state, parent, url):
        print(url, url.scheme())
        if url.scheme() != 'pyhacc':
            return False

        if url.path() == 'accounts/new':
            edit_account(state.session, 'new')
        elif url.path() == 'journals/new':
            edit_journal(state.session, 'new')
        elif url.path() == 'accounttypes/new':
            edit_account_type(state.session, 'new')
        elif url.path() == 'transactions/new':
            edit_transaction(state.session, 'new')
        elif url.path() == 'transactions/recent':
            view = view_recent_transactions(self, state.session)
            parent.adopt_tab(view, 'tran_recent', 'Recent Transactions')
        elif url.path() == 'reporting/monthly-status':
            win = monthly.Exporter(state)
            win.show()
        else:
            return False
        return True

    def get_menus(self):
        account_menu_schematic = [
                ('ClientURLMenuItem', ('New &Account', 'pyhacc:accounts/new', 'get_api_account_new')),
                ('ClientURLMenuItem', ('New &Journal', 'pyhacc:journals/new', 'get_api_journal_new')),
                ('ClientURLMenuItem', ('New Account &Type', 'pyhacc:accounttypes/new', 'get_api_accounttype_new')),
                ('SeparatorMenuItem', ()),
                ('ClientURLMenuItem', ('Test &Roscoe', 'pyhacc:roscoe/client-test', 'post_api_roscoe'))]
        yield ('&Accounts', account_menu_schematic)

        tran_menu_schematic = [
                ('ClientURLMenuItem', ('New &Transaction', 'pyhacc:transactions/new', 'get_api_transaction_new')),
                ('ClientURLMenuItem', ('&Recent Transactions', 'pyhacc:transactions/recent', 'get_api_transactions_list')),
                ('SeparatorMenuItem', ()),
                ('ClientURLMenuItem', ('Monthly &Status...', 'pyhacc:reporting/monthly-status', 'api_gledger_balance_sheet'))]
        yield ('&Transactions', tran_menu_schematic)

    def load_sidebar(self, state, name):
        pass

    def report_formats(self, state, name):
        if name == 'gl_summarize_by_type':
            return tranreports.AccountTypeGrouped()
        if name == 'gl_summarize_total':
            return tranreports.FullGrouped()
