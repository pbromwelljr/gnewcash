"""
Module containing classes that read, manipulate, and write GnuCash files, books, and budgets.

.. module:: gnucash_file
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""
import os.path
from datetime import datetime
from decimal import Decimal
from logging import getLogger
from typing import Any, Generator, List, Optional

from gnewcash.account import Account
from gnewcash.commodity import Commodity
from gnewcash.guid_object import GuidObject
from gnewcash.slot import Slot, SlottableObject
from gnewcash.transaction import (
    ScheduledTransaction, SimpleTransaction, SortingMethod, Split, Transaction, TransactionManager
)


class GnuCashFile:
    """Class representing a GnuCash file on disk."""

    def __init__(self, books: Optional[List['Book']] = None) -> None:
        if not books:
            books = []
        self.books: List['Book'] = books
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
            source_file: str,
            file_format: Any,
            sort_transactions: bool = True,
            sort_method: Optional[SortingMethod] = None,
    ) -> 'GnuCashFile':
        """
        Reads the specified .gnucash file and loads it into memory.

        :param source_file: Full or relative path to the .gnucash file.
        :type source_file: str
        :param sort_transactions: Flag for if transactions should be sorted by date_posted when reading from XML
        :type sort_transactions: bool
        :param file_format: File format of the file being uploaded.
        :type file_format: BaseFileFormat subclass
        :param sort_method: SortingMethod class instance that determines the sort order for the transactions.
        :type sort_method: SortingMethod
        :return: New GnuCashFile object
        :rtype: GnuCashFile
        """
        logger = getLogger()
        built_file: 'GnuCashFile' = cls()
        built_file.file_name = source_file
        if not os.path.exists(source_file):
            logger.warning('Could not find %s', source_file)
            return built_file

        return file_format.load(source_file=source_file, sort_transactions=sort_transactions, sort_method=sort_method)

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
            commodities: Optional[List[Commodity]] = None,
            slots: Optional[List[Slot]] = None,
            template_root_account: Optional[Account] = None,
            template_transactions: Optional[List[Transaction]] = None,
            scheduled_transactions: Optional[List[ScheduledTransaction]] = None,
            budgets: Optional[List['Budget']] = None,
            guid: Optional[str] = None,
            sort_method: Optional[SortingMethod] = None,
    ) -> None:
        GuidObject.__init__(self, guid)
        SlottableObject.__init__(self, slots)

        self.root_account: Optional[Account] = root_account
        self.transactions: TransactionManager = transactions or TransactionManager(sort_method=sort_method)
        self.commodities: List[Commodity] = commodities or []
        self.template_root_account: Optional[Account] = template_root_account
        self.template_transactions: List[Transaction] = template_transactions or []
        self.scheduled_transactions: List[ScheduledTransaction] = scheduled_transactions or []
        self.budgets: List['Budget'] = budgets or []

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
        current_level: Account = kwargs.get('current_level', self.root_account)
        paths_to_account_list: List[str] = list(paths_to_account)
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
        account_balance: Decimal = Decimal(0)
        account_transactions: List[Transaction] = list(filter(lambda x: account in [y.account for y in x.splits],
                                                              self.transactions))
        for transaction in account_transactions:
            split: Split = next(filter(lambda x: x.account == account, transaction.splits))
            account_balance += split.amount or Decimal(0)
        return account_balance

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

    def __str__(self) -> str:
        return f'{len(self.transactions)} transactions'

    def __repr__(self) -> str:
        return str(self)


class Budget(GuidObject, SlottableObject):
    """Class object representing a Budget in GnuCash."""

    def __init__(
            self,
            guid: Optional[str] = None,
            slots: Optional[List[Slot]] = None,
            name: Optional[str] = None,
            description: Optional[str] = None,
            period_count: Optional[int] = None,
            recurrence_multiplier: Optional[int] = None,
            recurrence_period_type: Optional[str] = None,
            recurrence_start: Optional[datetime] = None,
    ) -> None:
        GuidObject.__init__(self, guid)
        SlottableObject.__init__(self, slots)

        self.name: Optional[str] = name
        self.description: Optional[str] = description
        self.period_count: Optional[int] = period_count
        self.recurrence_multiplier: Optional[int] = recurrence_multiplier
        self.recurrence_period_type: Optional[str] = recurrence_period_type
        self.recurrence_start: Optional[datetime] = recurrence_start
