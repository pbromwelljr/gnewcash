import re
from datetime import datetime, timedelta
from decimal import Decimal
from xml.etree import ElementTree
from collections import namedtuple

from gnewcash.guid_object import GuidObject


LoanStatus = namedtuple('LoanStatus', ['iterator_balance', 'iterator_date', 'interest', 'amount_to_capital'])


class AccountType:
    ROOT = 'ROOT'
    BANK = 'BANK'
    INCOME = 'INCOME'
    ASSET = 'ASSET'
    CREDIT = 'CREDIT'
    EXPENSE = 'EXPENSE'
    EQUITY = 'EQUITY'
    LIABILITY = 'LIABILITY'


class Account(GuidObject):
    def __init__(self):
        super(Account, self).__init__()
        self.name = ''
        self.type = None
        self.commodity_scu = 100
        self.parent = None
        self.children = []
        self.commodity = None

    def __str__(self):
        return '{} - {}'.format(self.name, self.type)

    def __repr__(self):
        return str(self)

    def __setattr__(self, key, value):
        if key == 'parent' and value is not None:
            if self not in value.children:
                value.children.append(self)
        self.__dict__[key] = value

    def __eq__(self, other):
        return self.guid == other.guid

    def __hash__(self):
        return hash(self.guid)

    def get_starting_balance(self, transactions):
        account_transactions = [x for x in transactions if x.to_account == self]
        if account_transactions:
            amount = account_transactions[0].amount
        else:
            amount = 0
        return amount

    def get_balance_at_date(self, transactions, date=None):
        balance = 0
        applicable_transactions = [x for x in transactions if self in [x.from_account, x.to_account]]

        if date is not None:
            applicable_transactions = filter(lambda x: x.date_posted <= date, applicable_transactions)

        for transaction in applicable_transactions:
            if date is None or transaction.date_posted <= date:
                amount = transaction.amount
                if self.type == AccountType.CREDIT:
                    amount = transaction.amount * -1
                if transaction.from_account == self:
                    balance -= abs(amount)
                elif transaction.to_account == self:
                    balance += abs(amount)
        return balance

    def get_ending_balance(self, transactions):
        return self.get_balance_at_date(transactions)

    def minimum_balance_past_date(self, transactions, start_date):
        minimum_balance = None
        minimum_balance_date = None
        iterator_date = start_date
        while iterator_date < datetime(start_date.year + 1, 1, 1):
            iterator_date += timedelta(days=1)
            current_balance = self.get_balance_at_date(transactions, iterator_date)
            if minimum_balance is None or current_balance < minimum_balance:
                minimum_balance, minimum_balance_date = current_balance, iterator_date
        return minimum_balance, minimum_balance_date

    @property
    def as_xml(self):
        node_and_children = list()
        account_node = ElementTree.Element('gnc:account', {'version': '2.0.0'})
        ElementTree.SubElement(account_node, 'act:name').text = self.name
        ElementTree.SubElement(account_node, 'act:id', {'type': 'guid'}).text = self.guid
        ElementTree.SubElement(account_node, 'act:type').text = self.type
        if self.commodity:
            account_node.append(self.commodity.as_short_xml('act:commodity'))
        else:
            parent_commodity = self.get_parent_commodity()
            if parent_commodity:
                account_node.append(parent_commodity.as_short_xml('act:commodity'))
            else:
                raise ValueError('No commodity found for account {} or any of its ancestors'.format(self.name))

        if self.parent is not None:
            ElementTree.SubElement(account_node, 'act:parent', {'type': 'guid'}).text = self.parent.guid
        node_and_children.append(account_node)

        if self.children:
            for child in self.children:
                node_and_children += child.as_xml

        return node_and_children

    def as_dict(self, account_hierarchy=None, path_to_self='/'):
        if account_hierarchy is None:
            account_hierarchy = dict()
        account_hierarchy[path_to_self] = self
        for child in self.children:
            if path_to_self != '/':
                account_hierarchy = child.as_dict(account_hierarchy, path_to_self + '/' + child.dict_entry_name)
            else:
                account_hierarchy = child.as_dict(account_hierarchy, path_to_self + child.dict_entry_name)
        return account_hierarchy

    @property
    def dict_entry_name(self):
        non_alphanumeric_underscore = re.compile('[^a-zA-Z0-9_]')
        dict_entry_name = self.name
        dict_entry_name = dict_entry_name.replace(' ', '_')
        dict_entry_name = dict_entry_name.replace('/', '_')
        dict_entry_name = dict_entry_name.lower()
        dict_entry_name = re.sub(non_alphanumeric_underscore, '', dict_entry_name)
        return dict_entry_name

    def get_parent_commodity(self):
        if self.commodity:
            return self.commodity
        elif self.parent:
            return self.parent.get_parent_commodity()
        return None


class BankAccount(Account):
    def __init__(self):
        super(BankAccount, self).__init__()
        self.type = AccountType.BANK


class IncomeAccount(Account):
    def __init__(self):
        super(IncomeAccount, self).__init__()
        self.type = AccountType.INCOME


class AssetAccount(Account):
    def __init__(self):
        super(AssetAccount, self).__init__()
        self.type = AccountType.ASSET


class CreditAccount(Account):
    def __init__(self):
        super(CreditAccount, self).__init__()
        self.type = AccountType.CREDIT


class ExpenseAccount(Account):
    def __init__(self):
        super(ExpenseAccount, self).__init__()
        self.type = AccountType.EXPENSE


class EquityAccount(Account):
    def __init__(self):
        super(EquityAccount, self).__init__()
        self.type = AccountType.EQUITY


class LiabilityAccount(Account):
    def __init__(self):
        super(LiabilityAccount, self).__init__()
        self.type = AccountType.LIABILITY


class InterestAccount:
    def __init__(self, starting_balance, starting_date, interest_percentage, payment_amount, *,
                 additional_payments=None, skip_payment_dates=None, interest_start_date=None,
                 subaccounts=None):
        if additional_payments is None:
            additional_payments = []
        if skip_payment_dates is None:
            skip_payment_dates = []
        self.__starting_balance = Decimal(starting_balance) if starting_balance else None
        self.__starting_date = starting_date
        self.__interest_percentage = Decimal(interest_percentage) if interest_percentage else None
        self.additional_payments = additional_payments
        for payment in additional_payments:
            payment['amount'] = Decimal(payment['amount'])
        self.skip_payment_dates = skip_payment_dates
        self.__payment_amount = Decimal(payment_amount) if payment_amount else None
        self.interest_start_date = interest_start_date
        self.subaccounts = subaccounts

    def __str__(self):
        return '{} - {} - {}'.format(self.payment_amount, self.starting_balance, self.interest_percentage)

    def __repr__(self):
        return str(self)

    @property
    def starting_date(self):
        if self.subaccounts is None:
            return self.__starting_date
        return min([x.starting_date for x in self.subaccounts])

    @starting_date.setter
    def starting_date(self, new_starting_date):
        self.__starting_date = new_starting_date

    @property
    def interest_percentage(self):
        if self.subaccounts is None:
            return self.__interest_percentage
        return sum([x.interest_percentage for x in self.subaccounts])

    @property
    def payment_amount(self):
        if self.subaccounts is None:
            return self.__payment_amount
        return sum([x.payment_amount for x in self.subaccounts])

    @payment_amount.setter
    def payment_amount(self, new_payment_amount):
        self.__payment_amount = new_payment_amount

    @interest_percentage.setter
    def interest_percentage(self, new_interest_percentage):
        self.__interest_percentage = new_interest_percentage

    @property
    def starting_balance(self):
        if self.subaccounts is None:
            return self.__starting_balance
        return sum([x.starting_balance for x in self.subaccounts])

    @starting_balance.setter
    def starting_balance(self, new_starting_balance):
        self.__starting_balance = new_starting_balance

    def get_info_at_date(self, date):
        if self.subaccounts is None:
            return self.__get_info_at_date_single_account(date)
        return self.__get_info_at_date_subaccounts(date)

    def __get_info_at_date_single_account(self, date):
        iterator_date = self.starting_date
        iterator_balance = self.starting_balance
        interest_rate = self.interest_percentage
        if interest_rate > 1:
            interest_rate /= 100
        interest = 0
        amount_to_capital = 0
        while iterator_date < date:
            previous_date = iterator_date
            if iterator_date.month == 12:
                iterator_date = datetime(iterator_date.year + 1, 1, iterator_date.day)
            else:
                iterator_date = datetime(iterator_date.year, iterator_date.month + 1, iterator_date.day)
            applicable_extra_payments = [x for x in self.additional_payments
                                         if previous_date < x['payment_date'] < iterator_date]
            if applicable_extra_payments:
                for extra_payment in applicable_extra_payments:
                    iterator_balance -= extra_payment['amount']
            if iterator_date > date:
                break
            if iterator_date in self.skip_payment_dates:
                continue

            if self.interest_start_date is None or iterator_date >= self.interest_start_date:
                interest = Decimal(interest_rate / 12 * iterator_balance)
                amount_to_capital = self.payment_amount - interest
                new_balance = iterator_balance - amount_to_capital
                iterator_balance = new_balance
            else:
                interest = 0
                amount_to_capital = self.payment_amount

        return LoanStatus(iterator_balance, iterator_date, interest, amount_to_capital)

    def __get_info_at_date_subaccounts(self, date):
        iterator_balance = 0
        iterator_date = None
        interest = 0
        amount_to_capital = 0
        for account in self.subaccounts:
            account_status = account.get_info_at_date(date)
            iterator_balance += account_status.iterator_balance
            iterator_date = account_status.iterator_date
            interest += account_status.interest
            amount_to_capital += account_status.amount_to_capital
        return LoanStatus(iterator_balance, iterator_date, interest, amount_to_capital)

    def get_all_payments(self, skip_additional_payments=False):
        if self.subaccounts is None:
            return self.__get_all_payments_single_account(skip_additional_payments)
        return self.__get_all_payments_subaccounts(skip_additional_payments)

    def __get_all_payments_single_account(self, skip_additional_payments=False):
        iterator_date = self.starting_date
        iterator_balance = self.starting_balance
        interest_rate = self.interest_percentage
        payments = list()
        if interest_rate > 1:
            interest_rate /= 100
        while iterator_balance > 0:
            previous_date = iterator_date
            if iterator_date.month == 12:
                iterator_date = datetime(iterator_date.year + 1, 1, iterator_date.day)
            else:
                iterator_date = datetime(iterator_date.year, iterator_date.month + 1, iterator_date.day)
            applicable_extra_payments = [x for x in self.additional_payments
                                         if previous_date < x['payment_date'] < iterator_date]
            if applicable_extra_payments and not skip_additional_payments:
                for extra_payment in applicable_extra_payments:
                    payments.append((extra_payment['payment_date'], iterator_balance, extra_payment['amount']))
                    iterator_balance -= extra_payment['amount']
            if iterator_date in self.skip_payment_dates:
                continue

            interest = Decimal(interest_rate / 12 * iterator_balance)
            amount_to_capital = self.payment_amount - interest
            payments.append((iterator_date, iterator_balance, amount_to_capital))
            new_balance = iterator_balance - amount_to_capital
            iterator_balance = new_balance
        return payments

    def __get_all_payments_subaccounts(self, skip_additional_payments=False):
        all_payments = []
        for account in self.subaccounts:
            subaccount_payments = account.get_all_payments(skip_additional_payments)
            if not all_payments:
                all_payments = subaccount_payments
            else:
                for index, (payment1, payment2) in enumerate(zip(all_payments, subaccount_payments)):
                    all_payments[index] = payment1[0], payment1[1] + payment2[1], payment1[2] + payment2[2]
        return all_payments
