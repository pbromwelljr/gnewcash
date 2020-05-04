"""
Module containing classes that read, manipulate, and write accounts.

.. module:: account
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""
import abc
import re
from datetime import datetime
from decimal import Decimal, ROUND_UP
from collections import namedtuple
from typing import List, Tuple, Dict, Optional, Union, Pattern

from gnewcash.commodity import Commodity
from gnewcash.enums import AccountType
from gnewcash.guid_object import GuidObject
from gnewcash.slot import SlottableObject


LoanStatus = namedtuple('LoanStatus', ['iterator_balance', 'iterator_date', 'interest', 'amount_to_capital'])
LoanExtraPayment = namedtuple('LoanExtraPayment', ['payment_date', 'payment_amount'])


class Account(GuidObject, SlottableObject):
    """Represents an account in GnuCash."""

    def __init__(self) -> None:
        super(Account, self).__init__()
        self.name: str = ''
        self.type: Optional[str] = None
        self.commodity_scu: Optional[str] = None
        self.__parent: Optional['Account'] = None
        self.children: List['Account'] = []
        self.commodity: Optional[Commodity] = None
        self.code: Optional[str] = None
        self.description: Optional[str] = None
        self.non_std_scu: Optional[int] = None

    def __str__(self) -> str:
        return '{} - {}'.format(self.name, self.type)

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other: object) -> bool:
        if not isinstance(object, Account):
            return NotImplemented
        return self.guid == getattr(other, 'guid', None)

    def __hash__(self) -> int:
        return hash(self.guid)

    def as_dict(self, account_hierarchy: Dict[str, 'Account'] = None, path_to_self: str = '/') -> Dict[str, 'Account']:
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
            account_hierarchy = {}
        account_hierarchy[path_to_self] = self
        for child in self.children:
            if path_to_self != '/':
                account_hierarchy = child.as_dict(account_hierarchy, path_to_self + '/' + child.dict_entry_name)
            else:
                account_hierarchy = child.as_dict(account_hierarchy, path_to_self + child.dict_entry_name)
        return account_hierarchy

    @property
    def dict_entry_name(self) -> str:
        """
        Retrieves the dictionary entry based on account name.

        Only alpha-numeric and underscore characters allowed. Spaces and slashes (/) are converted to underscores.

        :return: String with the dictionary entry name.
        :rtype: str
        """
        non_alphanumeric_underscore: Pattern = re.compile('[^a-zA-Z0-9_]')
        dict_entry_name: str = self.name
        dict_entry_name = dict_entry_name.replace(' ', '_')
        dict_entry_name = dict_entry_name.replace('/', '_')
        dict_entry_name = dict_entry_name.lower()
        dict_entry_name = re.sub(non_alphanumeric_underscore, '', dict_entry_name)
        return dict_entry_name

    def get_parent_commodity(self) -> Optional[Commodity]:
        """
        Retrieves the commodity for the account.

        If none is provided, it will look at it's parent (and ancestors recursively) to find it.

        :return: Commodity object, or None if no commodity was found in the ancestry chain.
        :rtype: NoneType|Commodity
        """
        if self.commodity:
            return self.commodity
        if self.parent:
            return self.parent.get_parent_commodity()
        return None

    def get_subaccount_by_id(self, subaccount_id: str) -> Optional['Account']:
        """
        Finds a subaccount by its guid field.

        :param subaccount_id: Subaccount guid to find
        :type subaccount_id: str
        :return: Account object for that guid or None if no account was found
        :rtype: NoneType|Account
        """
        if self.guid == subaccount_id:
            return self
        for subaccount in self.children:
            subaccount_result: Optional[Account] = subaccount.get_subaccount_by_id(subaccount_id)
            if subaccount_result is not None:
                return subaccount_result
        return None

    @property
    def parent(self) -> Optional['Account']:
        """
        Parent account of the current account.

        :return: Account's parent
        :rtype: NoneType|Account
        """
        return self.__parent

    @parent.setter
    def parent(self, value: 'Account') -> None:
        if value is not None:
            if self not in value.children:
                value.children.append(self)
        self.__parent = value

    @property
    def color(self) -> str:
        """
        Account color.

        :return: Account color as a string
        :rtype: str
        """
        return super(Account, self).get_slot_value('color')

    @color.setter
    def color(self, value: str) -> None:
        super(Account, self).set_slot_value('color', value, 'string')

    @property
    def notes(self) -> str:
        """
        User defined notes for the account.

        :return: User-defined notes
        :rtype: str
        """
        return super(Account, self).get_slot_value('notes')

    @notes.setter
    def notes(self, value: str) -> None:
        super(Account, self).set_slot_value('notes', value, 'string')

    @property
    def hidden(self) -> bool:
        """
        Hidden flag for the account.

        :return: True if account is marked hidden, otherwise False.
        :rtype: bool
        """
        return super(Account, self).get_slot_value('hidden') == 'true'

    @hidden.setter
    def hidden(self, value: bool) -> None:
        super(Account, self).set_slot_value_bool('hidden', value, 'string')

    @property
    def placeholder(self) -> bool:
        """
        Placeholder flag for the account.

        :return: True if the account is a placeholder, otherwise False
        :rtype: bool
        """
        return super(Account, self).get_slot_value('placeholder') == 'true'

    @placeholder.setter
    def placeholder(self, value: bool) -> None:
        super(Account, self).set_slot_value_bool('placeholder', value, 'string')

    def get_account_guids(self, account_guids: Optional[List[str]] = None) -> List[str]:
        """
        Gets a flat list of account GUIDs under the current account.

        :param account_guids: Running list of account GUIDs (should be None on first call)
        :type account_guids: list[str]
        :return: List of account GUIDs under the current account
        :rtype: list[str]
        """
        if account_guids is None:
            account_guids = []
        account_guids.append(self.guid)
        for sub_account in self.children:
            account_guids = sub_account.get_account_guids(account_guids)
        return account_guids


class BankAccount(Account):
    """Shortcut class to create an account with the type set to AccountType.BANK."""

    def __init__(self) -> None:
        super(BankAccount, self).__init__()
        self.type = AccountType.BANK


class IncomeAccount(Account):
    """Shortcut class to create an account with the type set to AccountType.INCOME."""

    def __init__(self) -> None:
        super(IncomeAccount, self).__init__()
        self.type = AccountType.INCOME


class AssetAccount(Account):
    """Shortcut class to create an account with the type set to AccountType.ASSET."""

    def __init__(self) -> None:
        super(AssetAccount, self).__init__()
        self.type = AccountType.ASSET


class CreditAccount(Account):
    """Shortcut class to create an account with the type set to AccountType.CREDIT."""

    def __init__(self) -> None:
        super(CreditAccount, self).__init__()
        self.type = AccountType.CREDIT


class ExpenseAccount(Account):
    """Shortcut class to create an account with the type set to AccountType.EXPENSE."""

    def __init__(self) -> None:
        super(ExpenseAccount, self).__init__()
        self.type = AccountType.EXPENSE


class EquityAccount(Account):
    """Shortcut class to create an account with the type set to AccountType.EQUITY."""

    def __init__(self) -> None:
        super(EquityAccount, self).__init__()
        self.type = AccountType.EQUITY


class LiabilityAccount(Account):
    """Shortcut class to create an account with the type set to AccountType.LIABILITY."""

    def __init__(self) -> None:
        super(LiabilityAccount, self).__init__()
        self.type = AccountType.LIABILITY


class InterestAccountBase(abc.ABC):
    """Abstract class defining the API for Interest accounts."""

    @property
    @abc.abstractmethod
    def starting_date(self) -> datetime:
        """Abstract method for retrieving the starting date for the account."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def interest_percentage(self) -> Decimal:
        """Abstract method for retrieving the interest percentage for the account."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def payment_amount(self) -> Decimal:
        """Abstract method for retrieving the payment amount for the account."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def starting_balance(self) -> Decimal:
        """Abstract method for retrieving the starting balance for the account."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_info_at_date(self, date: datetime) -> LoanStatus:
        """
        Abstract method for retrieving the loan info at a specified date for the account.

        :param date: datetime object indicating the date you want the loan status of
        :type date: datetime.datetime
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_all_payments(self, skip_additional_payments: bool = False) -> List[Tuple[datetime, Decimal, Decimal]]:
        """
        Abstract method for retrieving all payments for the loan plan.

        :param skip_additional_payments: Skips additional payments if True.
        :type skip_additional_payments: bool
        """
        raise NotImplementedError


class InterestAccount(InterestAccountBase):
    """Class used to calculate interest balances."""

    def __init__(self, starting_balance: Decimal, starting_date: datetime, interest_percentage: Decimal,
                 payment_amount: Decimal,
                 additional_payments: Optional[List[LoanExtraPayment]] = None,
                 skip_payment_dates: Optional[List[datetime]] = None, interest_start_date: Optional[datetime] = None):
        """
        Class initializer.

        :param starting_balance: Starting balance for the interest account.
        :type starting_balance: decimal.Decimal|NoneType
        :param starting_date: datetime object indicating the date of the starting balance.
        :type starting_date: datetime.datetime|NoneType
        :param interest_percentage: Percentage to interest on the loan.
        :type interest_percentage: decimal.Decimal|NoneType
        :param payment_amount: Payment amount on the loan.
        :type payment_amount: decimal.Decimal|NoneType
        :param additional_payments: List of LoanExtraPayment objects indicating extra payments to the loan.
        :type additional_payments: list[LoanExtraPayment]|NoneType
        :param skip_payment_dates: List of datetime objects that the loan payment should be skipped
        :type skip_payment_dates: list[datetime.datetime]|NoneType
        :param interest_start_date: datetime object that interest starts on
        :type interest_start_date: datetime.datetime|NoneType
        """
        if additional_payments is None:
            additional_payments = []
        if skip_payment_dates is None:
            skip_payment_dates = []
        self.__starting_balance: Decimal = starting_balance
        self.__starting_date: datetime = starting_date
        self.__interest_percentage: Decimal = interest_percentage
        self.additional_payments: List[LoanExtraPayment] = additional_payments
        self.skip_payment_dates: List[datetime] = skip_payment_dates
        self.__payment_amount: Decimal = payment_amount
        self.interest_start_date: Optional[datetime] = interest_start_date

    def __str__(self) -> str:
        return '{} - {} - {}'.format(self.payment_amount, self.starting_balance, self.interest_percentage)

    def __repr__(self) -> str:
        return str(self)

    @property
    def starting_date(self) -> datetime:
        """
        Retrieves the starting date for the account.

        :return: Current InterestAccount's starting date.
        :rtype: datetime.datetime
        """
        return self.__starting_date

    @starting_date.setter
    def starting_date(self, new_starting_date: datetime) -> None:
        self.__starting_date = new_starting_date

    @property
    def interest_percentage(self) -> Decimal:
        """
        Retrieves the interest percentage for the account.

        :return: Current InterestAccount object's percentage.
        :rtype: decimal.Decimal
        """
        return self.__interest_percentage

    @interest_percentage.setter
    def interest_percentage(self, new_interest_percentage: Decimal) -> None:
        self.__interest_percentage = new_interest_percentage

    @property
    def payment_amount(self) -> Decimal:
        """
        Retrieves the payment amount for the account.

        :return: Current InterestAccount object's payment amount.
        :rtype: decimal.Decimal
        """
        return self.__payment_amount

    @payment_amount.setter
    def payment_amount(self, new_payment_amount: Decimal) -> None:
        self.__payment_amount = new_payment_amount

    @property
    def starting_balance(self) -> Decimal:
        """
        Retrieves the starting balance for the account.

        :return: Current InterestAccount object's starting balance.
        :rtype: decimal.Decimal
        """
        return self.__starting_balance

    @starting_balance.setter
    def starting_balance(self, new_starting_balance: Decimal) -> None:
        self.__starting_balance = new_starting_balance

    def get_info_at_date(self, date: datetime) -> LoanStatus:
        """
        Retrieves the loan info at a specified date for the current account.

        :param date: datetime object indicating the date you want the loan status of
        :type date: datetime.datetime
        :return: LoanStatus object
        :rtype: LoanStatus
        """
        iterator_date: datetime = self.starting_date
        iterator_balance: Decimal = self.starting_balance
        interest_rate: Decimal = self.interest_percentage
        if interest_rate > 1:
            interest_rate /= 100
        interest: Decimal = Decimal(0)
        amount_to_capital: Decimal = Decimal(0)
        while iterator_date < date:
            previous_date: datetime = iterator_date
            if iterator_date.month == 12:
                iterator_date = datetime(iterator_date.year + 1, 1, iterator_date.day, tzinfo=iterator_date.tzinfo)
            else:
                iterator_date = datetime(iterator_date.year, iterator_date.month + 1, iterator_date.day,
                                         tzinfo=iterator_date.tzinfo)
            applicable_extra_payments: List[LoanExtraPayment] = [
                x for x in self.additional_payments if previous_date < x.payment_date < iterator_date
            ]
            if applicable_extra_payments:
                for extra_payment in applicable_extra_payments:
                    iterator_balance -= extra_payment.payment_amount
            if iterator_date > date:
                break
            if iterator_date in self.skip_payment_dates:
                continue

            if self.interest_start_date is None or iterator_date >= self.interest_start_date:
                interest = Decimal(interest_rate / 12 * iterator_balance).quantize(Decimal('.01'), rounding=ROUND_UP)
                amount_to_capital = self.payment_amount - interest
            else:
                interest = Decimal(0)
                amount_to_capital = self.payment_amount
            new_balance = iterator_balance - amount_to_capital
            if new_balance < 0:
                new_balance = Decimal(0)
            iterator_balance = new_balance

            if iterator_balance == 0:
                break

        # Zero out if we're still before the requested date (debt has been fully paid already)
        if iterator_date < date:
            iterator_balance = Decimal(0)
            iterator_date = date
            interest = Decimal(0)
            amount_to_capital = Decimal(0)

        return LoanStatus(iterator_balance, iterator_date, interest, amount_to_capital)

    def get_all_payments(self, skip_additional_payments: bool = False) -> List[Tuple[datetime, Decimal, Decimal]]:
        """
        Retrieves a list of tuples that show all payments for the loan plan.

        :param skip_additional_payments: Skips additional payments if True.
        :type skip_additional_payments: bool
        :return: List of tuples with the date (index 0), balance (index 1) and amount to capital (index 2)
        :rtype: list[tuple]
        """
        iterator_date = self.starting_date
        iterator_balance = self.starting_balance
        interest_rate = self.interest_percentage
        payments = []
        if interest_rate > 1:
            interest_rate /= 100
        while iterator_balance > 0:
            previous_date = iterator_date
            if iterator_date.month == 12:
                iterator_date = datetime(iterator_date.year + 1, 1, iterator_date.day, tzinfo=iterator_date.tzinfo)
            else:
                iterator_date = datetime(iterator_date.year, iterator_date.month + 1, iterator_date.day,
                                         tzinfo=iterator_date.tzinfo)
            applicable_extra_payments = [x for x in self.additional_payments
                                         if previous_date < x.payment_date < iterator_date]
            if applicable_extra_payments and not skip_additional_payments:
                for extra_payment in applicable_extra_payments:
                    payments.append((extra_payment.payment_date, iterator_balance, extra_payment.payment_amount))
                    iterator_balance -= extra_payment.payment_amount
            if iterator_date in self.skip_payment_dates:
                continue

            if not self.interest_start_date or iterator_date > self.interest_start_date:
                interest = Decimal(interest_rate / 12 * iterator_balance).quantize(Decimal('.01'), rounding=ROUND_UP)
            else:
                interest = Decimal(0)
            amount_to_capital = self.payment_amount - interest
            payments.append((iterator_date, iterator_balance, amount_to_capital))
            new_balance = iterator_balance - amount_to_capital
            iterator_balance = new_balance
        return payments


InterestAccountBase.register(InterestAccount)


class InterestAccountWithSubaccounts(InterestAccountBase):
    """Class used to calculate interest balances based off of balances of subaccounts."""

    def __init__(self, subaccounts: List[InterestAccount],
                 additional_payments: Optional[List[Dict[str, Union[Decimal, datetime]]]] = None,
                 skip_payment_dates: Optional[List[datetime]] = None):
        """
        Class initializer.

        :param subaccounts: List of InterestAccount objects that are subaccounts of this InterestAccount
        :type subaccounts: list[InterestAccount]
        :param additional_payments: List of dictionaries containing an "amount" key for additional amount paid,
            and "payment_date" for the date the additional amount was paid.
        :type additional_payments: list[dict]|NoneType
        :param skip_payment_dates: List of datetime objects that the loan payment should be skipped
        :type skip_payment_dates: list[datetime.datetime]|NoneType
        """
        if additional_payments is None:
            additional_payments = []
        if skip_payment_dates is None:
            skip_payment_dates = []
        self.additional_payments: Optional[List[Dict[str, Union[Decimal, datetime]]]] = additional_payments
        self.skip_payment_dates: Optional[List[datetime]] = skip_payment_dates
        self.subaccounts: List[InterestAccount] = subaccounts

    @property
    def starting_date(self) -> datetime:
        """
        Retrieves the minimum starting date of the subaccounts.

        :return: Minimum starting date.
        :rtype: datetime.datetime
        """
        return min([x.starting_date for x in self.subaccounts])

    @property
    def interest_percentage(self) -> Decimal:
        """
        Retrieves the sum of the subaccounts' interest percentage.

        :return: Sum of interest percentages.
        :rtype: decimal.Decimal
        """
        return Decimal(sum([x.interest_percentage for x in self.subaccounts]))

    @property
    def payment_amount(self) -> Decimal:
        """
        Retrieves the sum of the subaccounts' payment amount.

        :return: Sum of the payment amounts.
        :rtype: decimal.Decimal
        """
        return Decimal(sum([x.payment_amount for x in self.subaccounts]))

    @property
    def starting_balance(self) -> Decimal:
        """
        Retrieves the sum of the subaccounts' starting balance.

        :return: Sum of the starting balances.
        :rtype: decimal.Decimal
        """
        return Decimal(sum([x.starting_balance for x in self.subaccounts]))

    def get_info_at_date(self, date: datetime) -> LoanStatus:
        """
        Retrieves the loan info at a specified date for all subaccounts.

        :param date: datetime object indicating the date you want the loan status of
        :type date: datetime.datetime
        :return: LoanStatus object
        :rtype: LoanStatus
        """
        iterator_balance: Decimal = Decimal(0)
        iterator_date: Optional[datetime] = None
        interest: Decimal = Decimal(0)
        amount_to_capital: Decimal = Decimal(0)
        for account in self.subaccounts:
            account_status = account.get_info_at_date(date)
            iterator_balance += account_status.iterator_balance
            iterator_date = account_status.iterator_date
            interest += account_status.interest
            amount_to_capital += account_status.amount_to_capital
        return LoanStatus(iterator_balance, iterator_date, interest, amount_to_capital)

    def get_all_payments(self, skip_additional_payments: bool = False) -> List[Tuple[datetime, Decimal, Decimal]]:
        """
        Retrieves a list of tuples that show all payments for the loan plan.

        :param skip_additional_payments: Skips additional payments if True.
        :type skip_additional_payments: bool
        :return: List of tuples with the date (index 0), balance (index 1) and amount to capital (index 2)
        :rtype: list[tuple]
        """
        all_payments: List[Tuple[datetime, Decimal, Decimal]] = []
        for account in self.subaccounts:
            subaccount_payments = account.get_all_payments(skip_additional_payments)
            if not all_payments:
                all_payments = subaccount_payments
            else:
                for index, (payment1, payment2) in enumerate(zip(all_payments, subaccount_payments)):
                    all_payments[index] = payment1[0], payment1[1] + payment2[1], payment1[2] + payment2[2]
        return all_payments


InterestAccountBase.register(InterestAccountWithSubaccounts)
