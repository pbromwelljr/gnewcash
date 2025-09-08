"""
Module containing classes that read, manipulate, and write GnuCash files, books, and budgets.

.. module:: gnucash_file
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""
import calendar
import pathlib
from collections.abc import Generator
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from fractions import Fraction
from logging import getLogger
from os import PathLike
from typing import Any, Optional, Union

from gnewcash.account import Account
from gnewcash.commodity import Commodity
from gnewcash.guid_object import GuidObject
from gnewcash.search import Query
from gnewcash.slot import Slot, SlottableObject
from gnewcash.transaction import (
    ScheduledTransaction, SimpleTransaction, SortingMethod, Transaction, TransactionManager
)


class GnuCashFile:
    """Class representing a GnuCash file on disk."""

    def __init__(self, books: Optional[list['Book']] = None) -> None:
        if not books:
            books = []
        self.books: list['Book'] = books
        self.file_name: Optional[str] = None

    def __str__(self) -> str:
        as_string: str = ''
        if self.file_name:
            as_string = self.file_name + ', '
        as_string += f'{len(self.books)} books'
        return as_string

    def __repr__(self) -> str:
        return str(self)

    @classmethod
    def read_file(
            cls,
            source_file: Union[str, PathLike],
            file_format: Any,
            sort_transactions: bool = True,
            sort_method: Optional[SortingMethod] = None,
    ) -> 'GnuCashFile':
        """
        Reads the specified .gnucash file and loads it into memory.

        :param source_file: Full or relative path to the .gnucash file.
        :type source_file: Union[str, PathLike]
        :param file_format: File format of the file being uploaded.
        :type file_format: BaseFileFormat subclass
        :param sort_transactions: Flag for if transactions should be sorted by date_posted when reading from XML
        :type sort_transactions: bool
        :param sort_method: SortingMethod class instance that determines the sort order for the transactions.
        :type sort_method: SortingMethod
        :return: New GnuCashFile object
        :rtype: GnuCashFile
        """
        source_file_path: pathlib.Path = pathlib.Path(source_file)
        logger = getLogger()
        built_file: 'GnuCashFile' = cls()
        built_file.file_name = source_file_path.name
        if not source_file_path.exists():
            logger.warning('Could not find %s', source_file)
            return built_file

        return file_format.load(
            source_file=source_file_path,
            sort_transactions=sort_transactions,
            sort_method=sort_method
        )

    def build_file(self, target_file: str, file_format: Any, prettify_xml: bool = False) -> None:
        """
        Writes the contents of the GnuCashFile object out to a .gnucash file on disk.

        :param target_file: Full or relative path to the target file
        :type target_file: str
        :param file_format: Class handling the writing of the GnuCash file. See 'file_formats' for more info.
        :type file_format: Any
        :param prettify_xml: Prettifies XML before writing to disk. Default False.
        :type prettify_xml: bool
        """
        return file_format.dump(self, target_file=target_file, prettify_xml=prettify_xml)

    def simplify_transactions(self) -> None:
        """Converts every transaction to a SimpleTransaction."""
        for book in self.books:
            for index, transaction in enumerate(book.transactions.transactions):
                book.transactions.transactions[index] = SimpleTransaction.from_transaction(transaction)

    def strip_transaction_timezones(self) -> None:
        """Removes timezone information from the date_posted and date_entered properties in every transaction."""
        for book in self.books:
            for transaction in book.transactions.transactions:
                if transaction.date_posted is not None and transaction.date_posted.tzinfo is not None:
                    transaction.date_posted = transaction.date_posted.replace(tzinfo=None)
                if transaction.date_entered is not None and transaction.date_entered.tzinfo is not None:
                    transaction.date_entered = transaction.date_entered.replace(tzinfo=None)


class Book(GuidObject, SlottableObject):
    """Represents a Book in GnuCash."""

    def __init__(
            self,
            root_account: Optional[Account] = None,
            transactions: Optional[TransactionManager] = None,
            commodities: Optional[list[Commodity]] = None,
            slots: Optional[list[Slot]] = None,
            template_root_account: Optional[Account] = None,
            template_transactions: Optional[list[Transaction]] = None,
            scheduled_transactions: Optional[list[ScheduledTransaction]] = None,
            budgets: Optional[list['Budget']] = None,
            guid: Optional[str] = None,
            sort_method: Optional[SortingMethod] = None,
    ) -> None:
        GuidObject.__init__(self, guid)
        SlottableObject.__init__(self, slots)

        self.root_account: Optional[Account] = root_account
        self.transactions: TransactionManager = transactions or TransactionManager(sort_method=sort_method)
        self.commodities: list[Commodity] = commodities or []
        self.template_root_account: Optional[Account] = template_root_account
        self.template_transactions: list[Transaction] = template_transactions or []
        self.scheduled_transactions: list[ScheduledTransaction] = scheduled_transactions or []
        self.budgets: list['Budget'] = budgets or []

    def get_account(self, *paths_to_account: str, **kwargs: Any) -> Optional[Account]:
        """
        Retrieves an account based on a path of account names.

        :param paths_to_account: Names of accounts that indicate the path
        :param kwargs: Keyword arguments.
        :type kwargs: dict
        :return: Account object if found, otherwise None
        :rtype: NoneType|Account

        Example: ``get_account('Assets', 'Current Assets', 'Checking Account')``

        **Keyword Arguments:**

        * ``current_level`` = Account to start searching from. If no account is provided, root account is assumed.
        """
        current_level: Optional[Account] = kwargs.get('current_level', self.root_account)
        if current_level is None:
            return None
        paths_to_account_list: list[str] = list(paths_to_account)
        next_level: str = paths_to_account_list.pop(0)
        for account in current_level.children:
            if account.name == next_level:
                if not paths_to_account_list:
                    return account
                return self.get_account(*paths_to_account_list, current_level=account)
        return None

    def get_account_balance(self, account: Account) -> Decimal:
        """
        Retrieves the balance for a specified account based on the transactions in the Book.

        :param account: Account object to retrieve the balance of.
        :type account: Account
        :return: Account balance if applicable transactions found, otherwise 0.
        :rtype: decimal.Decimal or int
        """
        return Decimal(self.transactions.query()
                                        .select_many(lambda t, i: t.splits)
                                        .where(lambda s: s.account == account)
                                        .select(lambda s, i: s.amount)
                                        .sum_())

    def get_all_accounts(self) -> Generator[Optional[Account], None, None]:
        """
        Returns a generator that retrieves all accounts, starting with the root account and going depth-first.

        :return:  A generator to a depth-first list of all accounts.
        :rtype: collections.Iterable[Account]
        """
        yield from self.__yield_account_recursive(self.root_account)

    @classmethod
    def __yield_account_recursive(
            cls,
            current_account: Optional[Account]
    ) -> Generator[Optional[Account], None, None]:
        yield current_account
        if current_account is not None:
            for child_account in current_account.children:
                yield from cls.__yield_account_recursive(child_account)

    def accounts_query(self) -> Query:
        """
        Get a new Query object to query accounts.

        :return: New Query object
        :rtype: Query
        """
        # We're converting the accounts to a list here so the account generator isn't fully consumed after the first
        # query. Not memory efficient, but will cause the LINQ-like library to operate properly.
        return Query(list(self.get_all_accounts()))

    def __str__(self) -> str:
        return f'{len(self.transactions)} transactions'

    def __repr__(self) -> str:
        return str(self)


class Budget(GuidObject, SlottableObject):
    """Class object representing a Budget in GnuCash."""

    def __init__(
            self,
            guid: Optional[str] = None,
            slots: Optional[list[Slot]] = None,
            name: Optional[str] = None,
            description: Optional[str] = None,
            period_count: Optional[int] = None,
            recurrence_multiplier: Optional[int] = None,
            recurrence_period_type: Optional['RecurrencePeriodType'] = None,
            recurrence_start: Optional[datetime] = None,
    ) -> None:
        GuidObject.__init__(self, guid)
        SlottableObject.__init__(self, slots)

        self.name: Optional[str] = name
        self.description: Optional[str] = description
        self.period_count: Optional[int] = period_count
        self.recurrence_multiplier: Optional[int] = recurrence_multiplier
        self.recurrence_period_type: Optional[RecurrencePeriodType] = recurrence_period_type
        self.recurrence_start: Optional[datetime] = recurrence_start

    def all_periods(self, account: Account, amount: Decimal, action: 'AllPeriodsActionType') -> None:
        """
        Applies an amount to a given account over all budget periods using the indicated action.

        :param account: Account that the amount should be applied for.
        :type account: Account
        :param amount: Amount for that account in a given period.
        :type amount: Decimal
        :param action: Action to take on each period (replace, add, or multiply).
        :type action: AllPeriodsActionType
        """
        if self.period_count is None:
            raise ValueError('"period_count" is required!')

        # Try to find an existing slot for this account.
        for slot in self.slots:
            if slot.key != account.guid:
                continue
            for period_slot in slot.value:
                existing_value_fraction = Fraction(period_slot.value)
                existing_value = (
                    Decimal(existing_value_fraction.numerator) / Decimal(existing_value_fraction.denominator)
                )
                if action == AllPeriodsActionType.REPLACE:
                    existing_value = amount
                elif action == AllPeriodsActionType.ADD:
                    existing_value += amount
                elif action == AllPeriodsActionType.MULTIPLY:
                    existing_value *= amount
                existing_value_fraction = Fraction(existing_value)
                period_slot.value = f'{existing_value_fraction.numerator}/{existing_value_fraction.denominator}'
            break
        else:
            # We couldn't find an existing slot, so let's make a new one.
            period_slots: list[Slot] = []
            if action == AllPeriodsActionType.MULTIPLY:
                amount = Decimal(0)  # Anything times zero is zero.

            fraction_amount = Fraction(amount)
            period_slot_value = f'{fraction_amount.numerator}/{fraction_amount.denominator}'

            for period_index in range(self.period_count):
                period_slots.append(Slot(key=period_index, value=period_slot_value, slot_type='numeric'))
            new_slot = Slot(key=account.guid, value=period_slots, slot_type='frame')
            self.slots.append(new_slot)

    def estimate(
            self,
            account: Account,
            transactions: TransactionManager,
            start_date: datetime,
            average: bool = False
    ) -> None:
        """
        Estimates the cost for each recurrence period, using the average if specified.

        :param account: Account that the amount should be applied for.
        :type account: Account
        :param transactions: TransactionManager of transactions to analyze.
        :type transactions: TransactionManager
        :param start_date: Date to start estimating from.
        :type start_date: datetime
        :param average: Should the average value across all periods be used? (default false)
        :type average: bool
        """
        period_amounts: list[Decimal] = []
        period_start_index: int = 0
        for period_start_date, period_end_date, period_index in self.__generate_recurrence_periods():
            if period_end_date < start_date:
                period_start_index = period_index
                continue
            account_transactions_sum = Decimal(
                transactions.query()
                .where(lambda t, start=period_start_date, end=period_end_date: start <= t.date_posted <= end)
                .select_many(lambda t, i: t.splits)
                .where(lambda s: s.account == account)
                .select(lambda s, i: s.amount)
                .sum_()
            )
            period_amounts.append(Decimal(account_transactions_sum))

        if average:
            average_amount = Decimal(Query(period_amounts).average())
            period_amounts = [average_amount] * len(period_amounts)

        for slot in self.slots:
            if slot.key != account.guid:
                continue
            for i, period_amount in enumerate(period_amounts):
                for period_slot in slot.value:
                    if period_slot.key != (period_start_index + i):
                        continue
                    period_amount_fraction = Fraction(period_amount)
                    period_slot.value = f'{period_amount_fraction.numerator}/{period_amount_fraction.denominator}'
                    break
            break
        else:
            # Make a new slot for the account
            period_slots: list[Slot] = []
            for i, period_amount in enumerate(period_amounts):
                fraction_amount = Fraction(period_amount)
                period_slot_value = f'{fraction_amount.numerator}/{fraction_amount.denominator}'
                period_slots.append(Slot(key=period_start_index + i,
                                         value=period_slot_value,
                                         slot_type='numeric'))

            new_slot = Slot(key=account.guid, value=period_slots, slot_type='frame')
            self.slots.append(new_slot)

    def __generate_recurrence_periods(self) -> Generator[tuple[datetime, datetime, int], None, None]:
        if self.recurrence_start is None:
            raise ValueError('"recurrence_start" is required!')
        if self.recurrence_multiplier is None:
            raise ValueError('"recurrence_multiplier" is required!')
        if self.period_count is None:
            raise ValueError('"period_count" is required!')

        anchor = self.recurrence_start
        one_day = timedelta(days=1)

        previous_end_date: Optional[datetime] = None
        for i in range(self.period_count):
            start_date: datetime
            if previous_end_date is None:
                start_date = anchor
            else:
                start_date = previous_end_date + one_day
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

            end_date = self.__add_period(anchor, (i + 1) * self.recurrence_multiplier)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999)
            if start_date.tzinfo is not None and end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=start_date.tzinfo)

            yield start_date, end_date, i
            previous_end_date = end_date

    def __add_period(self, start_date: datetime, count: int) -> datetime:
        if self.recurrence_period_type == RecurrencePeriodType.DAYS:
            return start_date + timedelta(days=count)
        if self.recurrence_period_type == RecurrencePeriodType.WEEKS:
            return start_date + timedelta(weeks=count)
        if self.recurrence_period_type == RecurrencePeriodType.MONTHS:
            return self.__add_months(start_date, count)
        if self.recurrence_period_type == RecurrencePeriodType.YEARS:
            return self.__add_years(start_date, count)
        return start_date

    @classmethod
    def __add_months(cls, date: datetime, months: int) -> datetime:
        year = date.year + (date.month - 1 + months) // 12
        month = (date.month - 1 + months) % 12 + 1
        day = min(date.day, calendar.monthrange(year, month)[1])
        return date.replace(year, month, day)

    @classmethod
    def __add_years(cls, date: datetime, years: int) -> datetime:
        day = date.day
        is_leap_year = (date.year % 4 == 0 and date.year % 100 != 0) or (date.year % 400 == 0)
        if date.month == 2 and date.day == 29 and not is_leap_year:
            day = 28
        return date.replace(year=date.year + years, month=date.month, day=day)

    def get_period_amount(self, account: Account, index: int) -> Optional[Decimal]:
        """
        Get the period amount of a specific account and index.

        This method iterates through the slots to find a match for the specified account's
        unique identifier (GUID) and the provided index. Upon locating a match, it converts
        the fraction amount of the matched subslot into a decimal and returns it.

        :param account: The account whose period amount is being retrieved.
        :type account: Account
        :param index: The index for which the period amount is being looked up.
        :type index: int
        :return: The period amount as a Decimal if the account and index match is found,
            otherwise None.
        :rtype: Optional[Decimal]
        """
        for slot in self.slots:
            if slot.key != account.guid:
                continue
            for subslot in slot.value:
                if subslot.key != index:
                    continue
                subslot_value = Fraction(subslot.value)
                return Decimal(subslot_value.numerator) / Decimal(subslot_value.denominator)
        return None

    def set_period_amount(self, account: Account, index: int, amount: Decimal) -> None:
        """
        Sets the amount for a specific period in a specific account.

        The amount is stored as a fraction in string representation. If the period or account does not already exist,
        it gets created.

        :param account: The account object where the period amount should be set.
        :type account: Account
        :param index: The index identifying the target period.
        :type index: int
        :param amount: The amount to be set for the specific period, as a Decimal.
        :type amount: Decimal
        :return: None
        :rtype: None
        :raises ValueError: If the "period_count" attribute is not set.
        """
        if self.period_count is None:
            raise ValueError('"period_count" is required!')

        amount_fraction = Fraction(amount)
        amount_fraction_string = f'{amount_fraction.numerator}/{amount_fraction.denominator}'

        for slot in self.slots:
            if slot.key != account.guid:
                continue
            for period_slot in slot.value:
                if period_slot.key != index:
                    continue
                period_slot.value = amount_fraction_string
                break
            else:
                slot.value.append(Slot(
                    key=index,
                    value=amount_fraction_string,
                    slot_type='numeric'
                ))
                break
        else:
            self.slots.append(
                Slot(
                    key=account.guid,
                    value=[Slot(
                        key=index,
                        value=amount_fraction_string,
                        slot_type='numeric'
                    )],
                    slot_type='frame'
                )
            )

    def get_period_index(self, date: datetime) -> Optional[int]:
        """
        Determines the index of the recurrence period that contains the specified date.

        This method iterates through generated recurrence periods and checks if the
        provided date falls between the start and end date of any period. If a match
        is found, the index of that period is returned. If no matching period is
        found, the method returns None.

        :param date: The date to evaluate against the recurrence periods.
        :type date: datetime
        :return: The index of the period containing the given date, or None if no
                 matching period is found.
        :rtype: Optional[int]
        """
        for start_date, end_date, index in self.__generate_recurrence_periods():
            if start_date <= date <= end_date:
                return index
        return None

    def get_budget_accounts(
            self,
            accounts: Union[list[Account], Generator[Account, None, None]]
    ) -> Generator[Account, None, None]:
        """
        Filters the given accounts to identify those that are associated with the budget.

        The method iterates through the provided list of accounts and determines if
        their GUIDs match with the keys of the existing slots. If a match is found,
        the account is added to the resulting list.

        :param accounts: A list or generator of Account objects to be filtered.
        :type accounts: Union[list[Account], Generator[Account, None, None]]
        :return: A list of Account objects that match against the budget accounts.
        :rtype: list[Account]
        """
        slot_account_guids = set(map(lambda slot: slot.key, self.slots))
        for account in accounts:
            if account.guid not in slot_account_guids:
                continue
            yield account

    def clear(self, account: Optional[Account] = None, index: Optional[int] = None) -> None:
        """
        Clear specific amounts or all slots in the budget.

        This method allows clearing data from the internal slots based on the given
        account and/or index parameters. If neither account nor index is provided,
        it will clear all slots. Otherwise, it will selectively remove entries
        matching the specified criteria.

        :param account: The account instance to clear slots from. If None, the operation
            is performed for all accounts.
        :type account: Optional[Account]
        :param index: The specific index in the slots of the account to clear. If None,
            all indices in the account are cleared.
        :type index: Optional[int]
        :return: None
        """
        if account is None and index is None:
            # Clear out everything
            self.slots = []
            return

        new_slots: list[Slot] = []
        for account_slot in self.slots:
            if account is not None and account.guid != account_slot.key:
                new_slots.append(account_slot)
                continue
            if index is None:
                continue

            new_period_slots: list[Slot] = []
            for period_slot in account_slot.value:
                if period_slot.key == index:
                    continue
                new_period_slots.append(period_slot)
            account_slot.value = new_period_slots

            if not account_slot.value:
                continue
            new_slots.append(account_slot)

        self.slots = new_slots


class RecurrencePeriodType(Enum):
    """Enumeration for the different recurrence period types."""

    DAYS = 'day'
    WEEKS = 'week'
    MONTHS = 'month'
    YEARS = 'year'


class AllPeriodsActionType(Enum):
    """Enumeration for different actions to apply a value to all budget periods."""

    REPLACE = 1
    ADD = 2
    MULTIPLY = 3
