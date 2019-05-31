"""
Module containing classes that read, manipulate, and write GnuCash files, books, and budgets.

.. module:: gnucash_file
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""

from datetime import datetime
from decimal import Decimal
import os.path
from logging import getLogger
import sqlite3
from typing import Optional, List, Tuple, Type, Any

from gnewcash.account import Account
from gnewcash.commodity import Commodity
from gnewcash.file_formats import DBAction
from gnewcash.guid_object import GuidObject
from gnewcash.slot import Slot, SlottableObject
from gnewcash.transaction import Transaction, TransactionManager, ScheduledTransaction, Split


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
        as_string += '{} books'.format(len(self.books))
        return as_string

    def __repr__(self) -> str:
        return str(self)

    @classmethod
    def read_file(cls, source_file: str, file_format: Any, sort_transactions: bool = True,
                  transaction_class: Type = None) -> 'GnuCashFile':
        """
        Reads the specified .gnucash file and loads it into memory.

        :param source_file: Full or relative path to the .gnucash file.
        :type source_file: str
        :param sort_transactions: Flag for if transactions should be sorted by date_posted when reading from XML
        :type sort_transactions: bool
        :param transaction_class: Class to use when initializing transactions
        :type transaction_class: type
        :param file_format: File format of the file being uploaded.
        If no format is provided, GNewCash will try to detect the file format,
        :type file_format: FileFormat
        :return: New GnuCashFile object
        :rtype: GnuCashFile
        """
        if transaction_class is None:
            transaction_class = Transaction
        logger = getLogger()
        built_file: 'GnuCashFile' = cls()
        built_file.file_name = source_file
        if not os.path.exists(source_file):
            logger.warning('Could not find %s', source_file)
            return built_file

        return file_format.load(source_file=source_file, sort_transactions=sort_transactions)

        # TODO: Move to SQLite reader
        # elif file_format == FileFormat.SQLITE:
        #     sqlite_handle = sqlite3.connect(source_file)
        #     cursor = sqlite_handle.cursor()
        #     built_file.books = Book.from_sqlite(cursor)

    def build_file(self, target_file: str, file_format: Any, prettify_xml: bool = False) -> None:
        """
        Writes the contents of the GnuCashFile object out to a .gnucash file on disk.

        :param target_file: Full or relative path to the target file
        :type target_file: str
        :param prettify_xml: Prettifies XML before writing to disk. Default False.
        :type prettify_xml: bool
        :param use_gzip: Use GZip compression when writing file to disk. Default False.
        :type use_gzip: bool
        """
        return file_format.dump(self, target_file=target_file, prettify_xml=prettify_xml)

        # TODO: Move to SQLite writer
        # elif file_format == FileFormat.SQLITE:
        #     create_schema = not os.path.exists(target_file)
        #     sqlite_handle = sqlite3.connect(target_file)
        #     cursor = sqlite_handle.cursor()
        #     if create_schema:
        #         self.create_sqlite_schema(cursor)
        #
        #     for book in self.books:
        #         book.to_sqlite(cursor)
        #
        #     raise NotImplementedError('SQLite support not implemented')


class Book(GuidObject, SlottableObject):
    """Represents a Book in GnuCash."""

    def __init__(self, root_account: Optional[Account] = None, transactions: Optional[TransactionManager] = None,
                 commodities: Optional[List[Commodity]] = None, slots: Optional[List[Slot]] = None,
                 template_root_account: Optional[Account] = None,
                 template_transactions: Optional[List[Transaction]] = None,
                 scheduled_transactions: Optional[List[ScheduledTransaction]] = None,
                 budgets: Optional[List['Budget']] = None) -> None:
        super(Book, self).__init__()
        self.root_account: Optional[Account] = root_account
        self.transactions: TransactionManager = transactions or TransactionManager()
        self.commodities: List[Commodity] = commodities or []
        self.slots: List[Slot] = slots or []
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

    def __str__(self) -> str:
        return '{} transactions'.format(len(self.transactions))

    def __repr__(self) -> str:
        return str(self)

    def to_sqlite(self, sqlite_handle: sqlite3.Cursor) -> None:
        book_db_action = self.get_db_action(sqlite_handle, 'books', 'guid', self.guid)
        if book_db_action == DBAction.INSERT:
            sqlite_handle.execute('INSERT INTO books (guid, root_account_guid, root_template_guid) VALUES (?, ?, ?)',
                                  (self.guid, self.root_account.guid, self.template_root_account.guid,))
        elif book_db_action == DBAction.UPDATE:
            sqlite_handle.execute('UPDATE books SET root_account_guid = ?, root_template_guid = ? WHERE guid = ?',
                                  (self.root_account.guid, self.template_root_account.guid, self.guid,))

        self.root_account.to_sqlite(sqlite_handle)
        self.template_root_account.to_sqlite(sqlite_handle)

        # TODO: Re-enable slots when slots are implemented
        # for slot in self.slots:
        #     slot.to_sqlite(sqlite_handle)

        for commodity in self.commodities:
            commodity.to_sqlite(sqlite_handle)

        # TODO: Implement the rest
        '''
        transaction_manager = TransactionManager()
        transaction_manager.disable_sort = not sort_transactions
        template_transactions = []
        template_account_guids = new_book.template_root_account.get_account_guids()

        for transaction in transaction_class.from_sqlite(sqlite_cursor, new_book.root_account,
                                                         new_book.template_root_account):
            transaction_account_guids = [x.account.guid for x in transaction.splits]
            if any(map(lambda x: x in template_account_guids, transaction_account_guids)):
                template_transactions.append(transaction)
            else:
                transaction_manager.add(transaction)

        new_book.transactions = transaction_manager
        new_book.template_transactions = template_transactions

        for scheduled_transaction in ScheduledTransaction.from_sqlite(sqlite_cursor,
                                                                      new_book.template_root_account):
            new_book.scheduled_transactions.append(scheduled_transaction)

        new_book.budgets = Budget.from_sqlite(sqlite_cursor)
        '''
        raise NotImplementedError


class Budget(GuidObject, SlottableObject):
    """Class object representing a Budget in GnuCash."""

    def __init__(self) -> None:
        super(Budget, self).__init__()
        self.name: Optional[str] = None
        self.description: Optional[str] = None
        self.period_count: Optional[int] = None
        self.recurrence_multiplier: Optional[int] = None
        self.recurrence_period_type: Optional[str] = None
        self.recurrence_start: Optional[datetime] = None

    @classmethod
    def from_sqlite(cls, sqlite_cursor: sqlite3.Cursor) -> List['Budget']:
        """
        Creates Budget objects from the GnuCash SQLite database.

        :param sqlite_cursor: Open cursor to the SQLite database
        :type sqlite_cursor: sqlite3.Cursor
        :return: Budget objects from SQLite
        :rtype: list[Budget]
        """
        budget_data = cls.get_sqlite_table_data(sqlite_cursor, 'budgets')
        new_budgets = []
        for budget in budget_data:
            new_budget = cls()
            new_budget.guid = budget['guid']
            new_budget.name = budget['name']
            new_budget.description = budget['description']
            new_budget.period_count = budget['num_periods']

            recurrence_data, = cls.get_sqlite_table_data(sqlite_cursor, 'recurrences', 'obj_guid = ?',
                                                         (new_budget.guid,))
            # TODO: Store recurrence ID
            new_budget.recurrence_multiplier = recurrence_data['recurrence_mult']
            new_budget.recurrence_period_type = recurrence_data['recurrence_period_type']
            new_budget.recurrence_start = datetime.strptime(recurrence_data['recurrence_period_start'],
                                                            '%Y%m%d')

            new_budget.slots = Slot.from_sqlite(sqlite_cursor, new_budget.guid)

            new_budgets.append(new_budget)
        return new_budgets

    def to_sqlite(self, sqlite_cursor: sqlite3.Cursor) -> None:
        db_action: DBAction = self.get_db_action(sqlite_cursor, 'budgets', 'guid', self.guid)
        sql: str = ''
        sql_args: Tuple = tuple()
        if db_action == DBAction.INSERT:
            sql = '''
INSERT INTO budgets(guid, name, description, num_periods)
VALUES (?, ?, ?, ?)'''.strip()
            sql_args = (self.guid, self.name, self.description, self.period_count)
            sqlite_cursor.execute(sql, sql_args)
        elif db_action == DBAction.UPDATE:
            sql = '''
UPDATE budgets
SET name = ?,
    description = ?,
    num_periods = ?
WHERE guid = ?'''.strip()
            sql_args = (self.name, self.description, self.period_count, self.guid)
            sqlite_cursor.execute(sql, sql_args)

        # TODO: Upsert recurrences
        # db_action = self.get_db_action(sqlite_cursor, 'recurrences', 'obj_guid', self.guid)
        # if db_action == DBAction.INSERT:

        # elif db_action == DBAction.UPDATE:

        # TODO: slots
