"""
.. module:: account
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""
import re
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_UP
from xml.etree import ElementTree
from collections import namedtuple

from gnewcash.commodity import Commodity
from gnewcash.guid_object import GuidObject
from gnewcash.slot import Slot


LoanStatus = namedtuple('LoanStatus', ['iterator_balance', 'iterator_date', 'interest', 'amount_to_capital'])


class AccountType:
    """
    Enumeration class to indicate the types of accounts available in GnuCash.
    """
    ROOT = 'ROOT'
    BANK = 'BANK'
    INCOME = 'INCOME'
    ASSET = 'ASSET'
    CREDIT = 'CREDIT'
    EXPENSE = 'EXPENSE'
    EQUITY = 'EQUITY'
    LIABILITY = 'LIABILITY'


class Account(GuidObject):
    """
    Represents an account in GnuCash.
    """
    def __init__(self):
        super(Account, self).__init__()
        self.name = ''
        self.type = None
        self.commodity_scu = None
        self.parent = None
        self.children = []
        self.commodity = None
        self.slots = []

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
        return self.guid == getattr(other, 'guid', None)

    def __hash__(self):
        return hash(self.guid)

    def get_starting_balance(self, transactions):
        """
        Retrieves the starting balance for the current account, given the list of transactions.

        :param transactions: List of transactions or TransactionManager
        :type transactions: list[Transaction] or TransactionManager
        :return: First transaction amount if the account has transactions, otherwise 0.
        :rtype: int or decimal.Decimal
        """
        account_transactions = [x for x in transactions if self in [y.account for y in x.splits if y.amount >= 0]]
        if account_transactions:
            first_transaction = account_transactions[0]
            amount = next(filter(lambda x: x.account == self and x.amount >= 0, first_transaction.splits)).amount
        else:
            amount = 0
        return amount

    def get_balance_at_date(self, transactions, date=None):
        """
        Retrieves the account balance for the current account at a certain date, given the list of transactions.
        If the provided date is None, it will retrieve the ending balance.

        :param transactions: List of transactions or TransactionManager
        :type transactions: list[Transaction] or TransactionManager
        :param date: Last date to consider when determining the account balance.
        :type date: datetime.datetime
        :return: Account balance at specified date (or ending balance) or 0, if no applicable transactions were found.
        :rtype: int or decimal.Decimal
        """
        balance = 0
        applicable_transactions = [x for x in transactions if self in map(lambda y: y.account, x.splits)]

        if date is not None:
            applicable_transactions = filter(lambda x: x.date_posted <= date, applicable_transactions)

        for transaction in applicable_transactions:
            if date is None or transaction.date_posted <= date:
                applicable_split = next(filter(lambda x: x.account == self, transaction.splits))
                amount = applicable_split.amount
                if self.type == AccountType.CREDIT:
                    amount = amount * -1
                balance += amount
        return balance

    def get_ending_balance(self, transactions):
        """
        Retrieves the ending balance for the current account, given the list of transactions.

        :param transactions: List of transactions or TransactionManager
        :type transactions: list[Transaction] or TransactionManager
        :return: Ending balance if the account has transactions, otherwise 0.
        :rtype: int or decimal.Decimal
        """
        return self.get_balance_at_date(transactions)

    def minimum_balance_past_date(self, transactions, start_date):
        """
        Gets the minimum balance for the account after a certain date, given the list of transactions.

        :param transactions: List of transactions or TransactionManager
        :type transactions: list[Transaction] or TransactionManager
        :param start_date: datetime object representing the date you want to find the minimum balance for.
        :type start_date: datetime.datetime
        :return: Tuple containing the minimum balance (element 0) and the date it's at that balance (element 1)
        :rtype: tuple
        """
        minimum_balance = None
        minimum_balance_date = None
        iterator_date = start_date
        end_date = max(map(lambda x: x.date_posted, transactions))
        while iterator_date < end_date:
            iterator_date += timedelta(days=1)
            current_balance = self.get_balance_at_date(transactions, iterator_date)
            if minimum_balance is None or current_balance < minimum_balance:
                minimum_balance, minimum_balance_date = current_balance, iterator_date
        if minimum_balance_date and minimum_balance_date > end_date:
            minimum_balance_date = end_date
        return minimum_balance, minimum_balance_date

    @property
    def as_xml(self):
        """
        Returns the current account configuration (and all of its child accounts) as GnuCash-compatible XML

        :return: Current account and children as XML
        :rtype: list[xml.etree.ElementTree.Element]
        :raises: ValueError if no commodity found.
        """
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

        if self.commodity_scu:
            ElementTree.SubElement(account_node, 'act:commodity-scu').text = str(self.commodity_scu)

        if self.slots:
            slots_node = ElementTree.SubElement(account_node, 'act:slots')
            for slot in self.slots:
                slots_node.append(slot.as_xml)

        if self.parent is not None:
            ElementTree.SubElement(account_node, 'act:parent', {'type': 'guid'}).text = self.parent.guid
        node_and_children.append(account_node)

        if self.children:
            for child in self.children:
                node_and_children += child.as_xml

        return node_and_children

    @classmethod
    def from_xml(cls, account_node, namespaces, account_objects):
        """
        Creates an Account object from the GnuCash XML

        :param account_node: XML node for the account
        :type account_node: ElementTree.Element
        :param namespaces: XML namespaces for GnuCash elements
        :type namespaces: dict[str, str]
        :param account_objects: Account objects already created from XML (used for assigning parent account)
        :type account_objects: list[Account]
        :return: Account object from XML
        :rtype: Account
        """

        account_object = cls()
        account_object.guid = account_node.find('act:id', namespaces).text
        account_object.name = account_node.find('act:name', namespaces).text
        account_object.type = account_node.find('act:type', namespaces).text

        commodity = account_node.find('act:commodity', namespaces)
        if commodity and commodity.find('cmdty:id', namespaces) is not None:
            account_object.commodity = Commodity.from_xml(commodity, namespaces)
        else:
            account_object.commodity = None

        commodity_scu = account_node.find('act:commodity-scu', namespaces)
        if commodity_scu is not None:
            account_object.commodity_scu = commodity_scu.text

        slots = account_node.find('act:slots', namespaces)
        if slots:
            for slot in slots.findall('slot', namespaces):
                account_object.slots.append(Slot.from_xml(slot, namespaces))

        parent = account_node.find('act:parent', namespaces)
        if parent is not None:
            account_object.parent = [x for x in account_objects if x.guid == parent.text][0]

        return account_object

    def as_dict(self, account_hierarchy=None, path_to_self='/'):
        """
        Retrieves the current account hierarchy as a dictionary.

        :param account_hierarchy: Existing account hierarchy. If None is provided, assumes a new dictionary.
        :type account_hierarchy: dict
        :param path_to_self: Dictionary key for the current account.
        :type path_to_self: str
        :return: Dictionary containing current account and all subaccounts.
        :rtype: dict
        """
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
        """
        Retrieves the dictionary entry based on account name.

        Only alpha-numeric and underscore characters allowed. Spaces and slashes (/) are converted to underscores.

        :return: String with the dictionary entry name.
        :rtype: str
        """
        non_alphanumeric_underscore = re.compile('[^a-zA-Z0-9_]')
        dict_entry_name = self.name
        dict_entry_name = dict_entry_name.replace(' ', '_')
        dict_entry_name = dict_entry_name.replace('/', '_')
        dict_entry_name = dict_entry_name.lower()
        dict_entry_name = re.sub(non_alphanumeric_underscore, '', dict_entry_name)
        return dict_entry_name

    def get_parent_commodity(self):
        """
        Retrieves the commodity for the account.

        If none is provided, it will look at it's parent (and ancestors recursively) to find it.

        :return: Commodity object, or None if no commodity was found in the ancestry chain.
        :rtype: Commodity
        """
        if self.commodity:
            return self.commodity
        if self.parent:
            return self.parent.get_parent_commodity()
        return None


class BankAccount(Account):
    """
    Shortcut class to create an account with the type set to AccountType.BANK
    """
    def __init__(self):
        super(BankAccount, self).__init__()
        self.type = AccountType.BANK


class IncomeAccount(Account):
    """
    Shortcut class to create an account with the type set to AccountType.INCOME
    """
    def __init__(self):
        super(IncomeAccount, self).__init__()
        self.type = AccountType.INCOME


class AssetAccount(Account):
    """
    Shortcut class to create an account with the type set to AccountType.ASSET
    """
    def __init__(self):
        super(AssetAccount, self).__init__()
        self.type = AccountType.ASSET


class CreditAccount(Account):
    """
    Shortcut class to create an account with the type set to AccountType.CREDIT
    """
    def __init__(self):
        super(CreditAccount, self).__init__()
        self.type = AccountType.CREDIT


class ExpenseAccount(Account):
    """
    Shortcut class to create an account with the type set to AccountType.EXPENSE
    """
    def __init__(self):
        super(ExpenseAccount, self).__init__()
        self.type = AccountType.EXPENSE


class EquityAccount(Account):
    """
    Shortcut class to create an account with the type set to AccountType.EQUITY
    """
    def __init__(self):
        super(EquityAccount, self).__init__()
        self.type = AccountType.EQUITY


class LiabilityAccount(Account):
    """
    Shortcut class to create an account with the type set to AccountType.LIABILITY
    """
    def __init__(self):
        super(LiabilityAccount, self).__init__()
        self.type = AccountType.LIABILITY


class InterestAccount:
    """
    Class used to calculate interest balances.
    """
    def __init__(self, starting_balance, starting_date, interest_percentage, payment_amount, *,
                 additional_payments=None, skip_payment_dates=None, interest_start_date=None,
                 subaccounts=None):
        """
        Class initializer.

        :param starting_balance: Starting balance for the interest account.
        :type starting_balance: decimal.Decimal
        :param starting_date: datetime object indicating the date of the starting balance.
        :type starting_date: datetime.datetime
        :param interest_percentage: Percentage to interest on the loan.
        :type interest_percentage: decimal.Decimal
        :param payment_amount: Payment amount on the loan.
        :type payment_amount: decimal.Decimal
        :param additional_payments: List of dictionaries containing an "amount" key for additional amount paid,
            and "payment_date" for the date the additional amount was paid.
        :type additional_payments: list[dict]
        :param skip_payment_dates: List of datetime objects that the loan payment should be skipped
        :type skip_payment_dates: list[datetime.datetime]
        :param interest_start_date: datetime object that interest starts on
        :type interest_start_date: datetime.datetime
        :param subaccounts: List of InterestAccount objects that are subaccounts of this InterestAccount
        :type subaccounts: list[InterestAccount]
        """
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
        """
        Retrieves the starting date for the account.

        If there are subaccounts specified, the minimum starting date of the subaccounts is used.

        :return: Minimum starting date, or current InterestAccount's starting date.
        :rtype: datetime.datetime
        """
        if self.subaccounts is None:
            return self.__starting_date
        return min([x.starting_date for x in self.subaccounts])

    @starting_date.setter
    def starting_date(self, new_starting_date):
        self.__starting_date = new_starting_date

    @property
    def interest_percentage(self):
        """
        Retrieves the interest percentage for the account.

        If there are subaccounts specified, the sum of the subaccounts' interest percentage is used.

        :return: Sum of interest percentages, or current InterestAccount object's percentage.
        :rtype: decimal.Decimal
        """
        if self.subaccounts is None:
            return self.__interest_percentage
        return sum([x.interest_percentage for x in self.subaccounts])

    @property
    def payment_amount(self):
        """
        Retrieves the payment amount for the account.

        If there are subaccounts specified, the sum of the subaccounts' payment amount is used.

        :return: Sum of the payment amounts, or current InterestAccount object's payment amount.
        :rtype: decimal.Decimal
        """
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
        """
        Retrieves the starting balance for the account.

        If there are subaccounts specified, the sum of the subaccounts' starting balance is used.

        :return: Sum of the starting balances, or current InterestAccount object's starting balance.
        :rtype: decimal.Decimal
        """
        if self.subaccounts is None:
            return self.__starting_balance
        return sum([x.starting_balance for x in self.subaccounts])

    @starting_balance.setter
    def starting_balance(self, new_starting_balance):
        self.__starting_balance = new_starting_balance

    def get_info_at_date(self, date):
        """
        Retrieves the loan info at a specified date for the current account, or all subaccounts (if specified)

        :param date: datetime object indicating the date you want the loan status of
        :type date: datetime.datetime
        :return: LoanStatus object
        :rtype: LoanStatus
        """
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
                interest = Decimal(interest_rate / 12 * iterator_balance).quantize(Decimal('.01'), rounding=ROUND_UP)
                amount_to_capital = self.payment_amount - interest
            else:
                interest = 0
                amount_to_capital = self.payment_amount
            new_balance = iterator_balance - amount_to_capital
            if new_balance < 0:
                new_balance = 0
            iterator_balance = new_balance

            if iterator_balance == 0:
                break

        # Zero out if we're still before the requested date (debt has been fully paid already)
        if iterator_date < date:
            iterator_balance = 0
            iterator_date = date
            interest = 0
            amount_to_capital = 0

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
        """
        Retrieves a list of tuples that show all payments for the loan plan.

        :param skip_additional_payments: Skips additional payments if True.
        :type skip_additional_payments: bool
        :return: List of tuples with the date (index 0), balance (index 1) and amount to capital (index 2)
        :rtype: list[tuple]
        """
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

            interest = Decimal(interest_rate / 12 * iterator_balance).quantize(Decimal('.01'), rounding=ROUND_UP)
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
