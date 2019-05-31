import enum
import logging
import pathlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import sqlite3
from sqlite3 import Cursor

from gnewcash.account import Account
from gnewcash.commodity import Commodity
from gnewcash.file_formats.base import BaseFileFormat, BaseFileReader, BaseFileWriter
from gnewcash.gnucash_file import Book, GnuCashFile
from gnewcash.slots import Slot
from gnewcash.transaction import Transaction, TransactionManager

SQLITE_SLOT_TYPE_MAPPING = {
    1: 'integer',
    2: 'double',
    3: 'numeric',
    4: 'string',
    5: 'guid',
    9: 'guid',
    10: 'gdate'
}


class DBAction(enum.Enum):
    """Enumeration class for record operations in databases."""
    INSERT = 1
    UPDATE = 2

    @staticmethod
    def get_db_action(sqlite_cursor: Cursor, table_name: str, column_name: str, row_identifier: Any) -> 'DBAction':
        """
        Helper method for determining the appropriate operation on a SQL table.

        :param sqlite_cursor: Open cursor to a SQLite database.
        :type sqlite_cursor: sqlite3.Cursor
        :param table_name: SQLite table name
        :type table_name: str
        :param column_name: Column to be used for existence check
        :type column_name: str
        :param row_identifier: Unique identifier for the row
        :type row_identifier: Any
        :return: Appropriate action based on record existence
        :rtype: DBAction
        """
        sql = 'SELECT 1 FROM {} WHERE {} = ?'.format(table_name, column_name)
        sqlite_cursor.execute(sql, (row_identifier,))

        record = sqlite_cursor.fetchone()
        if record is None:
            return DBAction.INSERT
        return DBAction.UPDATE


class GnuCashSQLiteReader(BaseFileReader):
    """Class containing the logic for loading SQlite files."""
    LOGGER = logging.getLogger()

    @classmethod
    def load(cls, *args: Any, source_file: str = '', sort_transactions: bool = True, **kwargs: Any) -> GnuCashFile:
        built_file: GnuCashFile = GnuCashFile()
        built_file.file_name = source_file

        source_path: pathlib.Path = pathlib.Path(source_file)
        if not source_path.exists():
            cls.LOGGER.warning('Could not find %s', source_file)
            return built_file

        sqlite_handle = sqlite3.connect(source_file)
        cursor = sqlite_handle.cursor()
        built_file.books = cls.create_books_from_sqlite(cursor, sort_transactions)
        return built_file

    @classmethod
    def create_books_from_sqlite(cls, sqlite_cursor: Cursor, sort_transactions: bool) -> List[Book]:
        """
        Creates Book objects from the GnuCash SQLite database.

        :param sqlite_cursor: Open cursor to the SQLite database
        :type sqlite_cursor: sqlite3.Cursor
        :param sort_transactions: Flag for if transactions should be sorted by date_posted when reading from SQLite
        :type sort_transactions: bool
        :param transaction_class: Class to use when initializing transactions
        :type transaction_class: type
        :return: Book objects from SQLite
        :rtype: list[Book]
        """
        new_books = []
        books = cls.get_sqlite_table_data(sqlite_cursor, 'books')
        for book in books:
            new_book = Book()
            new_book.guid = book['guid']
            new_book.root_account = cls.create_account_from_sqlite(sqlite_cursor, book['root_account_guid'])
            new_book.template_root_account = cls.create_account_from_sqlite(sqlite_cursor, book['root_template_guid'])

            new_book.slots = cls.create_slots_from_sqlite(sqlite_cursor, book['guid'])

            new_book.commodities = cls.create_commodity_from_sqlite(sqlite_cursor)

            transaction_manager = TransactionManager()
            transaction_manager.disable_sort = not sort_transactions
            template_transactions = []
            template_account_guids = tuple(new_book.template_root_account.get_account_guids())

            for transaction in Transaction.from_sqlite(sqlite_cursor, new_book.root_account,
                                                       new_book.template_root_account):
                transaction_account_guids = [x.account.guid for x in transaction.splits]
                if any(map(lambda x, tag=template_account_guids: x in tag, transaction_account_guids)):
                    template_transactions.append(transaction)
                else:
                    transaction_manager.add(transaction)

            new_book.transactions = transaction_manager
            new_book.template_transactions = template_transactions

            for scheduled_transaction in ScheduledTransaction.from_sqlite(sqlite_cursor,
                                                                          new_book.template_root_account):
                new_book.scheduled_transactions.append(scheduled_transaction)

            new_book.budgets = Budget.from_sqlite(sqlite_cursor)

            new_books.append(new_book)
        return new_books

    @classmethod
    def create_account_from_sqlite(cls, sqlite_cursor: Cursor, account_id: str) -> Account:
        """
         Creates an Account object from the GnuCash SQLite database.

         :param sqlite_cursor: Open cursor to the GnuCash SQLite database.
         :type sqlite_cursor: sqlite3.Cursor
         :param account_id: ID of the account to load from the SQLite database
         :type account_id: str
         :return: Account object from SQLite
         :rtype: Account
         """
        account_data_items = cls.get_sqlite_table_data(sqlite_cursor, 'accounts', 'guid = ?', (account_id,))
        if not account_data_items:
            raise RuntimeError('Could not find account {} in the SQLite database'.format(account_id))
        account_data, = account_data_items
        new_account = Account()
        new_account.guid = account_data['guid']
        new_account.name = account_data['name']
        new_account.type = account_data['account_type']
        new_account.code = account_data['code']
        new_account.description = account_data['description']
        if account_data['hidden'] is not None and account_data['hidden'] == 1:
            new_account.hidden = True
        if account_data['placeholder'] is not None and account_data['placeholder'] == 1:
            new_account.placeholder = True
        new_account.slots = Slot.from_sqlite(sqlite_cursor, account_data['guid'])

        new_account.commodity = cls.create_commodity_from_sqlite(sqlite_cursor, account_data['commodity_guid'])
        new_account.commodity_scu = account_data['commodity_scu']
        # TODO: non_std_scu

        for subaccount in cls.get_sqlite_table_data(sqlite_cursor, 'accounts', 'parent_guid = ?', (account_id,)):
            new_account.children.append(cls.create_account_from_sqlite(sqlite_cursor, subaccount['guid']))

        return new_account

    @classmethod
    def create_slots_from_sqlite(cls, sqlite_cursor: Cursor, object_id: str) -> List[Slot]:
        """
        Creates Slot objects from the GnuCash SQLite database.

        :param sqlite_cursor: Open cursor to the SQLite database
        :type sqlite_cursor: sqlite3.Cursor
        :param object_id: ID of the object that the slot belongs to
        :type object_id: str
        :return: Slot objects from SQLite
        :rtype: list[Slot]
        """
        slot_info = cls.get_sqlite_table_data(sqlite_cursor, 'slots', 'obj_guid = ?', (object_id,))
        new_slots = []
        for slot in slot_info:
            slot_type = SQLITE_SLOT_TYPE_MAPPING[slot['slot_type']]
            slot_name = slot['name']
            if slot_type == 'guid':
                slot_value = slot['guid_val']
            elif slot_type == 'string':
                slot_value = slot['string_val']
            elif slot_type == 'gdate':
                slot_value = datetime.strptime(slot['gdate_val'], '%Y%m%d')
            else:
                raise NotImplementedError('Slot type {} is not implemented.'.format(slot['slot_type']))
            new_slot = Slot(slot_name, slot_value, slot_type)
            new_slots.append(new_slot)
        return new_slots

    @classmethod
    def create_commodity_from_sqlite(cls, sqlite_cursor: Cursor, commodity_guid: str = None) \
            -> Union[Commodity, List[Commodity]]:
        """
        Creates a Commodity object from the GnuCash SQLite database.

        :param sqlite_cursor: Open cursor to the SQLite database
        :type sqlite_cursor: sqlite3.Cursor
        :param commodity_guid: Commodity to pull from the database. None pulls all commodities.
        :type commodity_guid: str
        :return: Commodity object(s) from SQLite
        :rtype: Commodity or list[Commodity]
        """
        if commodity_guid is None:
            commodity_data = cls.get_sqlite_table_data(sqlite_cursor, 'commodities')
        else:
            commodity_data = cls.get_sqlite_table_data(sqlite_cursor, 'commodities', 'guid = ?', (commodity_guid,))

        new_commodities = []
        for commodity in commodity_data:
            commodity_id = commodity['mnemonic']
            space = commodity['namespace']

            new_commodity = Commodity(commodity_id, space)
            new_commodity.guid = commodity['guid']
            new_commodity.get_quotes = commodity['quote_flag'] == 1
            new_commodity.quote_source = commodity['quote_source']
            new_commodity.quote_tz = commodity['quote_tz']
            new_commodity.name = commodity['fullname']
            new_commodity.xcode = commodity['cusip']
            new_commodity.fraction = commodity['fraction']
            new_commodities.append(new_commodity)

        if commodity_guid is None:
            return new_commodities
        return new_commodities[0]

    @classmethod
    def get_sqlite_table_data(cls, sqlite_cursor: Cursor, table_name: str, where_condition: Optional[str] = None,
                              where_parameters: Optional[Tuple[Any]] = None) -> List[Dict[str, Any]]:
        """
        Helper method for retrieving data from a SQLite table.

        :param sqlite_cursor: Open cursor to a SQLite database.
        :type sqlite_cursor: sqlite3.Cursor
        :param table_name: SQLite table name
        :type table_name: str
        :param where_condition: SQL WHERE condition for the query (if any)
        :type where_condition: str
        :param where_parameters: SQL WHERE parameters for the query (if any)
        :type where_parameters: tuple
        :return: List of dictionaries (keys being the column names) for each row in the SQLite table
        :rtype: list[dict[str, Any]]
        """
        sql = 'SELECT * FROM {}'.format(table_name)
        if where_condition is not None:
            sql += ' WHERE ' + where_condition
        if where_parameters is not None:
            sqlite_cursor.execute(sql, where_parameters)
        else:
            sqlite_cursor.execute(sql)
        column_names = [column[0] for column in sqlite_cursor.description]
        rows = []
        for row in sqlite_cursor.fetchall():
            row_data = dict(zip(column_names, row))
            rows.append(row_data)
        return rows


class GnuCashSQLiteWriter(BaseFileWriter):
    """Class containing the logic for saving SQlite files."""
    @classmethod
    def dump(cls, *args: Any, **kwargs: Any) -> None:
        pass


    @classmethod
    def create_sqlite_schema(cls, sqlite_cursor: sqlite3.Cursor) -> None:
        """
        Creates the SQLite schema using the provided SQLite cursor.

        :param sqlite_cursor: Open cursor to a SQLite database.
        :type sqlite_cursor: sqlite3.Cursor
        """
        # Note: To update the GnuCash schema, connect to an existing GnuCash SQLite file and run ".schema".
        # Make sure to remove sqlite_sequence from the schema statements
        with open(os.path.join(os.path.dirname(__file__), 'sqlite_schema.sql')) as schema_file:
            for line in schema_file.readlines():
                sqlite_cursor.execute(line)



class SqliteFileFormat(GnuCashSQLiteReader, GnuCashSQLiteWriter, BaseFileFormat):
    """Class containing the logic for loading and saving SQlite files."""
