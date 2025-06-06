"""
Module containing the logic for loading and saving SQLite files.

.. module:: xml
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""
import enum
import logging
import os.path
import pathlib
import sqlite3
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from gnewcash.account import Account
from gnewcash.commodity import Commodity
from gnewcash.file_formats.base import BaseFileFormat, BaseFileReader, BaseFileWriter
from gnewcash.gnucash_file import Book, Budget, GnuCashFile
from gnewcash.slot import Slot
from gnewcash.transaction import ScheduledTransaction, SortingMethod, Split, Transaction, TransactionManager

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
    def get_db_action(
            sqlite_cursor: sqlite3.Cursor,
            table_name: str,
            column_name: str,
            row_identifier: Any,
    ) -> 'DBAction':
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
        sql = f'SELECT 1 FROM {table_name} WHERE {column_name} = ?'
        sqlite_cursor.execute(sql, (row_identifier,))

        record = sqlite_cursor.fetchone()
        if record is None:
            return DBAction.INSERT
        return DBAction.UPDATE


class GnuCashSQLiteReader(BaseFileReader):
    """Class containing the logic for loading SQlite files."""

    LOGGER = logging.getLogger()

    @classmethod
    def load(cls,
             *args: Any,
             source_file: Optional[pathlib.Path] = None,
             sort_transactions: bool = True,
             sort_method: Optional[SortingMethod] = None,
             **kwargs: Any
             ) -> GnuCashFile:
        """
        Loads a GnuCash SQLite file from disk to memory.

        :param source_file: File to load from disk
        :type source_file: str
        :param sort_transactions: Should transactions be sorted
        :type sort_transactions: bool
        :param sort_method: SortMethod class instance that determines which sort method to use
        :type sort_method: SortingMethod
        :return: GnuCashFile object
        :rtype: GnuCashFile
        """
        built_file: GnuCashFile = GnuCashFile()
        if not source_file:
            cls.LOGGER.error('No file provided to load')
            return built_file
        if not source_file.exists():
            cls.LOGGER.warning('Could not find %s', source_file)
            return built_file

        built_file.file_name = source_file.name

        sqlite_connection = sqlite3.connect(source_file)
        cursor = sqlite_connection.cursor()
        built_file.books = cls.create_books_from_sqlite(cursor, sort_transactions, sort_method)
        cursor.close()
        sqlite_connection.close()
        return built_file

    @classmethod
    def create_books_from_sqlite(
            cls,
            sqlite_cursor: sqlite3.Cursor,
            sort_transactions: bool,
            sort_method: Optional[SortingMethod] = None,
    ) -> list[Book]:
        """
        Creates Book objects from the GnuCash SQLite database.

        :param sqlite_cursor: Open cursor to the SQLite database
        :type sqlite_cursor: sqlite3.Cursor
        :param sort_transactions: Flag for if transactions should be sorted by date_posted when reading from SQLite
        :type sort_transactions: bool
        :param sort_method: SortingMethod instance indicating which method in which we should sort the transactions.
        :type sort_method: SortingMethod
        :return: Book objects from SQLite
        :rtype: list[Book]
        """
        new_books = []
        books = cls.get_sqlite_table_data(sqlite_cursor, 'books')
        for book in books:
            new_book = Book(
                guid=book['guid'],
                root_account=cls.create_account_from_sqlite(sqlite_cursor, book['root_account_guid']),
                template_root_account=cls.create_account_from_sqlite(sqlite_cursor, book['root_template_guid']),
                slots=cls.create_slots_from_sqlite(sqlite_cursor, book['guid']),
                commodities=cls.create_commodities_from_sqlite(sqlite_cursor),
                sort_method=sort_method,
            )

            transaction_manager = TransactionManager(disable_sort=not sort_transactions, sort_method=sort_method)
            template_transactions = []
            template_account_guids: tuple[str, ...] = tuple()
            if new_book.template_root_account is not None:
                template_account_guids = tuple(new_book.template_root_account.get_account_guids())

            for transaction in cls.create_transactions_from_sqlite(sqlite_cursor, new_book.root_account,
                                                                   new_book.template_root_account):
                transaction_account_guids = [x.account.guid for x in transaction.splits if x.account is not None]
                if set(transaction_account_guids).intersection(set(template_account_guids)):
                    template_transactions.append(transaction)
                else:
                    transaction_manager.add(transaction)

            new_book.transactions = transaction_manager
            new_book.template_transactions = template_transactions

            for scheduled_transaction in cls.create_scheduled_transactions_from_sqlite(sqlite_cursor,
                                                                                       new_book.template_root_account):
                new_book.scheduled_transactions.append(scheduled_transaction)

            new_book.budgets = cls.create_budget_from_sqlite(sqlite_cursor)

            new_books.append(new_book)
        return new_books

    @classmethod
    def create_account_from_sqlite(cls, sqlite_cursor: sqlite3.Cursor, account_id: str) -> Account:
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
            raise RuntimeError(f'Could not find account {account_id} in the SQLite database')
        account_data = account_data_items[0]
        new_account = Account(
            guid=account_data['guid'],
            name=account_data['name'],
            account_type=account_data['account_type'],
            code=account_data['code'],
            description=account_data['description'],
            commodity_scu=account_data['commodity_scu'],
            non_std_scu=account_data['non_std_scu'],
        )
        if account_data['hidden'] is not None and account_data['hidden'] == 1:
            new_account.hidden = True
        if account_data['placeholder'] is not None and account_data['placeholder'] == 1:
            new_account.placeholder = True
        new_account.slots = cls.create_slots_from_sqlite(sqlite_cursor, account_data['guid'])

        if account_data['commodity_guid'] is not None:
            new_account.commodity = cls.create_commodity_from_sqlite(sqlite_cursor, account_data['commodity_guid'])

        for subaccount in cls.get_sqlite_table_data(sqlite_cursor, 'accounts', 'parent_guid = ?', (account_id,)):
            new_account.children.append(cls.create_account_from_sqlite(sqlite_cursor, subaccount['guid']))

        return new_account

    @classmethod
    def create_slots_from_sqlite(cls, sqlite_cursor: sqlite3.Cursor, object_id: str) -> list[Slot]:
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
            elif slot_type == 'numeric':
                slot_value = Decimal(slot['numeric_val_num']) / Decimal(slot['numeric_val_denom'])
            else:
                raise NotImplementedError(f'Slot type {slot["slot_type"]} is not implemented.')
            new_slot = Slot(slot_name, slot_value, slot_type)
            new_slot.sqlite_id = slot['id']
            new_slots.append(new_slot)
        return new_slots

    @classmethod
    def create_commodity_from_sqlite(cls, sqlite_cursor: sqlite3.Cursor, commodity_guid: str) -> Commodity:
        """
        Creates a Commodity object from the GnuCash SQLite database.

        :param sqlite_cursor: Open cursor to the SQLite database
        :type sqlite_cursor: sqlite3.Cursor
        :param commodity_guid: Commodity to pull from the database. None pulls all commodities.
        :type commodity_guid: str
        :return: Commodity object(s) from SQLite
        :rtype: Commodity or list[Commodity]
        """
        commodity_data = cls.get_sqlite_table_data(sqlite_cursor, 'commodities', 'guid = ?', (commodity_guid,))
        new_commodities = cls.__create_commodity_objects_from_data(commodity_data)
        return new_commodities[0]

    @classmethod
    def create_commodities_from_sqlite(cls, sqlite_cursor: sqlite3.Cursor) -> list[Commodity]:
        """
        Creates Commodity objects for all commodities in the SQLite database.

        :param sqlite_cursor: Open cursor to the SQLite database
        :type sqlite_cursor: sqlite3.Cursor
        :return: Commodity object(s) from SQLite
        :rtype: list[Commodity]
        """
        return cls.__create_commodity_objects_from_data(cls.get_sqlite_table_data(sqlite_cursor, 'commodities'))

    @classmethod
    def __create_commodity_objects_from_data(cls, commodity_data: list[dict]) -> list[Commodity]:
        new_commodities = []
        for commodity in commodity_data:
            commodity_id = commodity['mnemonic']
            space = commodity['namespace']

            new_commodity = Commodity(
                commodity_id,
                space,
                guid=commodity['guid'],
                get_quotes=commodity['quote_flag'] == 1,
                quote_source=commodity['quote_source'],
                quote_tz=commodity['quote_tz'],
                name=commodity['fullname'],
                xcode=commodity['cusip'],
                fraction=commodity['fraction'],
            )
            new_commodities.append(new_commodity)
        return new_commodities

    @classmethod
    def create_transactions_from_sqlite(
            cls,
            sqlite_cursor: sqlite3.Cursor,
            root_account: Optional[Account],
            template_root_account: Optional[Account],
    ) -> list[Transaction]:
        """
        Creates Transaction objects from the GnuCash SQLite database.

        :param sqlite_cursor: Open cursor to the SQLite database.
        :type sqlite_cursor: sqlite3.Cursor
        :param root_account: Root account from the SQLite database
        :type root_account: Account
        :param template_root_account: Template root account from the SQLite database
        :type template_root_account: Account
        :return: Transaction objects from SQLite
        :rtype: list[Transaction]
        """
        transaction_data = cls.get_sqlite_table_data(sqlite_cursor, 'transactions')
        new_transactions: list[Transaction] = []
        for transaction in transaction_data:
            new_transaction = Transaction(
                guid=transaction['guid'],
                memo=transaction['num'],
                date_posted=datetime.strptime(transaction['post_date'], '%Y-%m-%d %H:%M:%S'),
                date_entered=datetime.strptime(transaction['enter_date'], '%Y-%m-%d %H:%M:%S'),
                description=transaction['description'],
                currency=cls.create_commodity_from_sqlite(sqlite_cursor,
                                                          commodity_guid=transaction['currency_guid']),
                slots=cls.create_slots_from_sqlite(sqlite_cursor, transaction['guid']),
                splits=cls.create_splits_from_sqlite(sqlite_cursor, transaction['guid'], root_account,
                                                     template_root_account),
            )
            new_transactions.append(new_transaction)
        return new_transactions

    @classmethod
    def create_scheduled_transactions_from_sqlite(
            cls,
            sqlite_cursor: sqlite3.Cursor,
            template_root_account: Optional[Account],
    ) -> list[ScheduledTransaction]:
        """
        Creates ScheduledTransaction objects from the GnuCash SQLite database.

        :param sqlite_cursor: Open cursor to the SQLite database
        :type sqlite_cursor: sqlite3.Cursor
        :param template_root_account: Root template account
        :type template_root_account: Account
        :return: ScheduledTransaction objects from SQLite
        :rtype: list[ScheduledTransaction]
        """
        scheduled_transactions = cls.get_sqlite_table_data(sqlite_cursor, 'schedxactions')
        new_scheduled_transactions = []
        for scheduled_transaction in scheduled_transactions:
            new_scheduled_transaction = ScheduledTransaction(
                guid=scheduled_transaction['guid'],
                name=scheduled_transaction['name'],
                enabled=scheduled_transaction['enabled'] == 1,
                start_date=datetime.strptime(scheduled_transaction['start_date'], '%Y%m%d'),
                end_date=datetime.strptime(scheduled_transaction['end_date'], '%Y%m%d'),
                last_date=datetime.strptime(scheduled_transaction['last_occur'], '%Y%m%d'),
                num_occur=scheduled_transaction['num_occur'],
                rem_occur=scheduled_transaction['rem_occur'],
                auto_create=scheduled_transaction['auto_create'] == 1,
                auto_create_notify=scheduled_transaction['auto_notify'] == 1,
                advance_create_days=scheduled_transaction['adv_creation'],
                advance_remind_days=scheduled_transaction['adv_notify'],
                instance_count=scheduled_transaction['instance_count'],
            )
            if template_root_account is not None:
                new_scheduled_transaction.template_account = template_root_account.get_subaccount_by_id(
                    scheduled_transaction['template_act_guid'])
            recurrence_info = cls.get_sqlite_table_data(sqlite_cursor, 'recurrences', 'obj_guid = ?',
                                                        (new_scheduled_transaction.guid,))[0]

            new_scheduled_transaction.recurrence_multiplier = recurrence_info['recurrence_mult']
            new_scheduled_transaction.recurrence_start = datetime.strptime(recurrence_info['recurrence_period_start'],
                                                                           '%Y%m%d')
            new_scheduled_transaction.recurrence_period = recurrence_info['recurrence_period_type']
            new_scheduled_transaction.recurrence_weekend_adjust = recurrence_info['recurrence_weekend_adjust']

            new_scheduled_transactions.append(new_scheduled_transaction)
        return new_scheduled_transactions

    @classmethod
    def create_budget_from_sqlite(cls, sqlite_cursor: sqlite3.Cursor) -> list[Budget]:
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
            new_budget = Budget(
                guid=budget['guid'],
                name=budget['name'],
                description=budget['description'],
                period_count=budget['num_periods'],
            )

            recurrence_data = cls.get_sqlite_table_data(sqlite_cursor, 'recurrences', 'obj_guid = ?',
                                                        (new_budget.guid,))[0]
            new_budget.recurrence_multiplier = recurrence_data['recurrence_mult']
            new_budget.recurrence_period_type = recurrence_data['recurrence_period_type']
            new_budget.recurrence_start = datetime.strptime(recurrence_data['recurrence_period_start'],
                                                            '%Y%m%d')

            new_budget.slots = cls.create_slots_from_sqlite(sqlite_cursor, new_budget.guid)

            new_budgets.append(new_budget)
        return new_budgets

    @classmethod
    def create_splits_from_sqlite(
            cls,
            sqlite_cursor: sqlite3.Cursor,
            transaction_guid: str,
            root_account: Optional[Account],
            template_root_account: Optional[Account]
    ) -> list[Split]:
        """
        Creates Split objects from the GnuCash SQLite database.

        :param sqlite_cursor: Open cursor to the SQLite database.
        :type sqlite_cursor: sqlite3.Cursor
        :param transaction_guid: GUID of the transaction to load the splits of
        :type transaction_guid: str
        :param root_account: Root account from the SQLite database
        :type root_account: Account
        :param template_root_account: Template root account from the SQLite database
        :type template_root_account: Account
        :return: Split objects from XML
        :rtype: list[Split]
        """
        split_data = cls.get_sqlite_table_data(sqlite_cursor, 'splits', 'tx_guid = ?', (transaction_guid,))
        new_splits = []
        for split in split_data:
            account_object: Optional[Account] = None
            if root_account is not None:
                account_object = root_account.get_subaccount_by_id(split['account_guid'])
            if account_object is None and template_root_account is not None:
                account_object = template_root_account.get_subaccount_by_id(split['account_guid'])

            new_split = Split(
                account_object,
                split['value_num'] / split['value_denom'],
                split['reconcile_state'],
                guid=split['guid'],
                memo=split['memo'],
                action=split['action'],
                reconcile_date=(
                    datetime.strptime(split['reconcile_date'], '%Y-%m-%d %H:%M:%S')
                    if split['reconcile_date'] else None
                ),
                quantity_num=split['quantity_num'],
                quantity_denominator=split['quantity_denom'],
                lot_guid=split['lot_guid'],
                slots=cls.create_slots_from_sqlite(sqlite_cursor, split['guid'])
            )
            new_splits.append(new_split)
        return new_splits

    @classmethod
    def get_sqlite_table_data(
            cls,
            sqlite_cursor: sqlite3.Cursor,
            table_name: str,
            where_condition: Optional[str] = None,
            where_parameters: Optional[tuple[Any]] = None,
    ) -> list[dict[str, Any]]:
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
        sql = f'SELECT * FROM {table_name}'
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
    def dump(cls, gnucash_file: GnuCashFile, *args: Any, target_file: str = '', **kwargs: Any) -> None:  # type: ignore
        """
        Updates GnuCash SQLite file on disk from memory.

        :param gnucash_file: File to write to disk
        :type gnucash_file: GnuCashFile
        :param target_file: Destination file to write to.
        :type target_file: str
        :return:
        """
        create_schema: bool = not os.path.exists(target_file)
        sqlite_connection: sqlite3.Connection = sqlite3.connect(target_file)
        cursor: sqlite3.Cursor = sqlite_connection.cursor()
        if create_schema:
            cls.create_sqlite_schema(cursor)

        for book in gnucash_file.books:
            cls.write_book_to_sqlite(book, cursor)

        cursor.close()
        sqlite_connection.close()

    @classmethod
    def write_book_to_sqlite(cls, book: Book, sqlite_cursor: sqlite3.Cursor) -> None:
        """
        Writes a Book object to the SQLite database.

        :param book: Book object
        :type book: Book
        :param sqlite_cursor: Handle to SQLite file
        :type sqlite_cursor: sqlite3.Cursor
        """
        book_db_action = DBAction.get_db_action(sqlite_cursor, 'books', 'guid', book.guid)
        if book_db_action == DBAction.INSERT:
            sqlite_cursor.execute(
                'INSERT INTO books (guid, root_account_guid, root_template_guid) VALUES (?, ?, ?)',
                (book.guid, book.root_account.guid if book.root_account else None,
                 book.template_root_account.guid if book.template_root_account else None,))
        elif book_db_action == DBAction.UPDATE:
            sqlite_cursor.execute('UPDATE books SET root_account_guid = ?, root_template_guid = ? WHERE guid = ?',
                                  (book.root_account.guid if book.root_account else None,
                                   book.template_root_account.guid if book.template_root_account else None,
                                   book.guid,))

        if book.root_account is not None:
            cls.write_account_to_sqlite(book.root_account, sqlite_cursor)
        if book.template_root_account is not None:
            cls.write_account_to_sqlite(book.template_root_account, sqlite_cursor)

        for slot in book.slots:
            cls.write_slot_to_sqlite(slot, sqlite_cursor, book.guid)

        for commodity in book.commodities:
            cls.write_commodity_to_sqlite(commodity, sqlite_cursor)

        for transaction in book.transactions:
            cls.write_transaction_to_sqlite(transaction, sqlite_cursor)

        for deleted_transaction_guid in book.transactions.deleted_transaction_guids:
            cls.delete_transaction_from_sqlite(deleted_transaction_guid, sqlite_cursor)

        for scheduled_transaction in book.scheduled_transactions:
            cls.write_scheduled_transaction_to_sqlite(scheduled_transaction, sqlite_cursor)

        for budget in book.budgets:
            cls.write_budget_to_sqlite(budget, sqlite_cursor)

    @classmethod
    def write_budget_to_sqlite(cls, budget: Budget, sqlite_cursor: sqlite3.Cursor) -> None:
        """
        Writes a Budget object to the SQLite database.

        :param budget: Budget object
        :type budget: Budget
        :param sqlite_cursor: Handle to SQLite database
        :type sqlite_cursor: sqlite3.Cursor
        """
        db_action: DBAction = DBAction.get_db_action(sqlite_cursor, 'budgets', 'guid', budget.guid)
        sql: str = ''
        sql_args: tuple = tuple()
        if db_action == DBAction.INSERT:
            sql = '''
    INSERT INTO budgets(guid, name, description, num_periods)
    VALUES (?, ?, ?, ?)'''.strip()
            sql_args = (budget.guid, budget.name, budget.description, budget.period_count)
            sqlite_cursor.execute(sql, sql_args)
        elif db_action == DBAction.UPDATE:
            sql = '''
    UPDATE budgets
    SET name = ?,
        description = ?,
        num_periods = ?
    WHERE guid = ?'''.strip()
            sql_args = (budget.name, budget.description, budget.period_count, budget.guid)
            sqlite_cursor.execute(sql, sql_args)

        cls.write_recurrence_to_sqlite(budget, sqlite_cursor)

        for slot in budget.slots:
            cls.write_slot_to_sqlite(slot, sqlite_cursor, budget.guid)

    @classmethod
    def write_recurrence_to_sqlite(cls, obj: Budget, sqlite_cursor: sqlite3.Cursor) -> None:
        """
        Writes recurrence information from a Budget object to the SQLite database.

        :param obj: Budget object
        :type obj: Budget
        :param sqlite_cursor: Handle to SQLite database
        :type sqlite_cursor: sqlite3.Cursor
        """
        db_action = DBAction.get_db_action(sqlite_cursor, 'recurrences', 'obj_guid', obj.guid)
        sql: str = ''
        sql_args: tuple = tuple()

        recurrence_weekend_adjust = ''
        if hasattr(obj, 'recurrence_weekend_adjust'):
            recurrence_weekend_adjust = getattr(obj, 'recurrence_weekend_adjust')
        if db_action == DBAction.INSERT:
            sql = '''
    INSERT INTO recurrences(obj_guid, recurrence_mult, recurrence_period_type, recurrence_period_start,
                            recurrence_weekend_adjust)
    VALUES(?, ?, ?, ?, ?)
'''.strip()
            sql_args = (obj.guid, obj.recurrence_multiplier, obj.recurrence_period_type, obj.recurrence_start,
                        recurrence_weekend_adjust)
        elif db_action == DBAction.UPDATE:
            sql = '''
    UPDATE recurrences
    SET recurrence_mult = ?,
        recurrence_period_type = ?,
        recurrence_period_start = ?,
        recurrence_weekend_adjust = ?
    WHERE obj_guid = ?
'''.strip()
            sql_args = (obj.recurrence_multiplier, obj.recurrence_period_type, obj.recurrence_start,
                        recurrence_weekend_adjust, obj.guid)
        sqlite_cursor.execute(sql, sql_args)

    @classmethod
    def write_commodity_to_sqlite(cls, commodity: Commodity, sqlite_cursor: sqlite3.Cursor) -> None:
        """
        Writes a Commodity object to the SQLite database.

        :param commodity: Commodity object
        :type commodity: Commodity
        :param sqlite_cursor: Handle to SQLite file
        :type sqlite_cursor: sqlite3.Cursor
        """
        db_action: DBAction = DBAction.get_db_action(sqlite_cursor, 'commodities', 'guid', commodity.guid)
        sql: str = ''
        sql_args: tuple = tuple()
        if db_action == DBAction.INSERT:
            sql = 'INSERT INTO commodities(guid, namespace, mnemonic, fullname, cusip, fraction, quote_flag, ' \
                  'quote_source, quote_tz) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)'
            sql_args = (commodity.guid, commodity.space, commodity.commodity_id, commodity.name, commodity.xcode,
                        commodity.fraction, 1 if commodity.get_quotes else 0, commodity.quote_source,
                        commodity.quote_tz,)
            sqlite_cursor.execute(sql, sql_args)
        elif db_action == DBAction.UPDATE:
            sql = 'UPDATE commodities SET namespace = ?, mnemonic = ?, fullname = ?, cusip = ?, fraction = ?, ' \
                  'quote_flag = ?, quote_source = ?, quote_tz = ? WHERE guid = ?'
            sql_args = (commodity.space, commodity.commodity_id, commodity.name, commodity.xcode, commodity.fraction,
                        1 if commodity.get_quotes else 0, commodity.quote_source, commodity.quote_tz, commodity.guid,)
            sqlite_cursor.execute(sql, sql_args)

    @classmethod
    def write_slot_to_sqlite(cls, slot: Slot, sqlite_cursor: sqlite3.Cursor, object_guid: str) -> None:
        """
        Writes a Slot object to the SQLite database.

        :param slot: Slot object
        :type slot: Slot
        :param sqlite_cursor: Handle to SQLite file
        :type sqlite_cursor: sqlite3.Cursor
        """
        sql: str = ''
        sql_args: tuple = tuple()
        update_field_name: str = ''
        if slot.type == 'guid':
            update_field_name = 'guid_val'
        elif slot.type == 'string':
            update_field_name = 'string_val'
        elif slot.type == 'gdate':
            update_field_name = 'gdate_val'
        elif slot.type == 'numeric':
            update_field_name = 'numeric_val_num'
        else:
            raise NotImplementedError(f'Slot type {slot.type} is not implemented.')

        slot_type_id: int = 0
        for slot_type_id_search, slot_type_name in SQLITE_SLOT_TYPE_MAPPING.items():
            if slot_type_name == slot.type:
                slot_type_id = slot_type_id_search
                break
        else:
            raise NotImplementedError(f'Slot type {slot.type} is not implemented.')

        if slot.sqlite_id is None:
            if slot.type == 'numeric':
                sql = '''INSERT INTO slots (obj_guid, name, slot_type, numeric_val_num, numeric_val_denom)
VALUES (?, ?, ?, ?, ?)'''
                sql_args = (object_guid, slot.key, slot_type_id, slot.value, 100)
            else:
                sql = f'INSERT INTO slots (obj_guid, name, slot_type, {update_field_name}) VALUES(?, ?, ?, ?)'
                sql_args = (object_guid, slot.key, slot_type_id, slot.value)
            sqlite_cursor.execute(sql, sql_args)

            # Populate the ID of the insert
            sql = 'select seq from sqlite_sequence where name = ?'
            sql_args = ('slots',)
            sqlite_cursor.execute(sql, sql_args)
            new_id, = sqlite_cursor.fetchone()
            slot.sqlite_id = new_id
        else:
            sql = f'UPDATE slots SET obj_guid = ?, name = ?, slot_type = ?, {update_field_name} = ? ' \
                  'WHERE id = ?'
            if slot.type == 'numeric':
                # Get the denominator first.
                denom_sql = 'SELECT numeric_val_denom FROM slots WHERE id = ?'
                sqlite_cursor.execute(denom_sql, (slot.sqlite_id,))
                denominator = sqlite_cursor.fetchone()
                sql_args = (object_guid, slot.key, slot_type_id, int(slot.value * (denominator or 100)), slot.sqlite_id)
            else:
                sql_args = (object_guid, slot.key, slot_type_id, slot.value, slot.sqlite_id)

            sqlite_cursor.execute(sql, sql_args)

    @classmethod
    def write_account_to_sqlite(cls, account: Account, sqlite_cursor: sqlite3.Cursor) -> None:
        """
        Writes an Account object to the SQLite database.

        :param account: Account object
        :type account: Account
        :param sqlite_cursor: Handle to SQLite file
        :type sqlite_cursor: sqlite3.Cursor
        """
        db_action: DBAction = DBAction.get_db_action(sqlite_cursor, 'accounts', 'guid', account.guid)
        sql: str = ''
        sql_args: tuple = tuple()
        if db_action == DBAction.INSERT:
            sql = '''
INSERT INTO accounts(guid, name, account_type, commodity_guid, commodity_scu, non_std_scu,
parent_guid, code, description, hidden, placeholder)
VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''.strip()
            sql_args = (account.guid, account.name, account.type, account.commodity.guid if account.commodity else None,
                        account.commodity_scu, account.non_std_scu,
                        account.parent.guid if account.parent else None, account.code, account.description,
                        account.hidden, account.placeholder)
            sqlite_cursor.execute(sql, sql_args)
        elif db_action == DBAction.UPDATE:
            sql = '''
UPDATE accounts
SET name = ?,
    account_type = ?,
    commodity_guid = ?,
    commodity_scu = ?,
    non_std_scu = ?,
    parent_guid = ?,
    code = ?,
    description = ?,
    hidden = ?,
    placeholder = ?
WHERE guid  = ?
'''.strip()
            sql_args = (account.name, account.type, account.commodity.guid if account.commodity else None,
                        account.commodity_scu, account.non_std_scu,
                        account.parent.guid if account.parent else None, account.code, account.description,
                        account.hidden, account.placeholder, account.guid)
            sqlite_cursor.execute(sql, sql_args)

        for slot in account.slots:
            cls.write_slot_to_sqlite(slot, sqlite_cursor, account.guid)

        for sub_account in account.children:
            cls.write_account_to_sqlite(sub_account, sqlite_cursor)

    @classmethod
    def write_transaction_to_sqlite(cls, transaction: Transaction, sqlite_cursor: sqlite3.Cursor) -> None:
        """
        Writes a Transaction object to the SQLite database.

        :param transaction: Transaction object
        :type transaction: Transaction
        :param sqlite_cursor: Handle to SQLite file
        :type sqlite_cursor: sqlite3.Cursor
        """
        db_action: DBAction = DBAction.get_db_action(sqlite_cursor, 'transactions', 'guid', transaction.guid)
        sql: str = ''
        sql_args: tuple = tuple()
        if db_action == DBAction.INSERT:
            sql = '''
    INSERT INTO transactions(guid, currency_guid, num, post_date, enter_date, description)
    VALUES (?, ?, ?, ?, ?, ?)'''.strip()
            sql_args = (transaction.guid, transaction.currency.guid if transaction.currency else None,
                        transaction.memo, transaction.date_posted, transaction.date_entered, transaction.description)
            sqlite_cursor.execute(sql, sql_args)
        elif db_action == DBAction.UPDATE:
            sql = '''
    UPDATE transactions
    SET currency_guid = ?,
        num = ?,
        post_date = ?,
        enter_date = ?,
        description = ?
    WHERE guid = ?'''.strip()
            sql_args = (transaction.currency.guid if transaction.currency else None, transaction.memo,
                        transaction.date_posted, transaction.date_entered, transaction.description, transaction.guid)
            sqlite_cursor.execute(sql, sql_args)

        for slot in transaction.slots:
            cls.write_slot_to_sqlite(slot, sqlite_cursor, transaction.guid)

        for split in transaction.splits:
            cls.write_split_to_sqlite(split, sqlite_cursor, transaction.guid)

    @classmethod
    def delete_transaction_from_sqlite(cls, deleted_transaction_guid: str, sqlite_cursor: sqlite3.Cursor) -> None:
        """Removes a transaction from the SQLite database, as well as all dependent objects."""
        # Delete slots for deleted transaction
        sql: str = 'DELETE FROM slots WHERE obj_guid = ?'
        sql_args: tuple = (deleted_transaction_guid,)
        sqlite_cursor.execute(sql, sql_args)

        # Delete slots for splits in transaction
        sql = 'DELETE FROM slots WHERE obj_guid IN (SELECT guid FROM splits WHERE tx_guid = ?)'
        sqlite_cursor.execute(sql, sql_args)

        # Delete splits for the transaction
        sql = 'DELETE FROM splits WHERE tx_guid = ?'
        sqlite_cursor.execute(sql, sql_args)

        # Delete the transaction
        sql = 'DELETE FROM transactions WHERE guid = ?'
        sqlite_cursor.execute(sql, sql_args)

    @classmethod
    def write_split_to_sqlite(cls, split: Split, sqlite_cursor: sqlite3.Cursor, transaction_guid: str) -> None:
        """
        Writes a Split object to the SQLite database.

        :param split: Split object
        :type split: Commodity
        :param sqlite_cursor: Handle to SQLite file
        :type sqlite_cursor: sqlite3.Cursor
        """
        db_action: DBAction = DBAction.get_db_action(sqlite_cursor, 'splits', 'guid', split.guid)
        sql: str = ''
        sql_args: tuple = tuple()
        if db_action == DBAction.INSERT:
            sql = '''
    INSERT INTO splits(guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num,
                       value_denom, quantity_num, quantity_denom, lot_guid)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''.strip()
            sql_args = (split.guid, transaction_guid, split.account.guid if split.account else None,
                        split.memo, split.action if split.action else '',
                        split.reconciled_state,
                        split.reconcile_date.strftime('%Y-%m-%d %H:%M:%S') if split.reconcile_date else None,
                        split.value_num if split.value_num is not None else '',
                        split.value_denom if split.value_denom else '',
                        split.quantity_num,
                        split.quantity_denominator,
                        split.lot_guid)
            sqlite_cursor.execute(sql, sql_args)
        elif db_action == DBAction.UPDATE:
            sql = '''
    UPDATE splits
    SET tx_guid = ?,
        account_guid = ?,
        memo = ?,
        action = ?,
        reconcile_state = ?,
        reconcile_date = ?,
        value_num = ?,
        value_denom = ?,
        quantity_num = ?,
        quantity_denom = ?,
        lot_guid = ?
    WHERE guid = ?'''.strip()
            sql_args = (transaction_guid, split.account.guid if split.account else None, split.memo, split.action,
                        split.reconciled_state,
                        split.reconcile_date.strftime('%Y-%m-%d %H:%M:%S') if split.reconcile_date else None,
                        split.value_num if split.value_num is not None else '',
                        split.value_denom if split.value_denom is not None else '',
                        split.quantity_num,
                        split.quantity_denominator,
                        split.lot_guid,
                        split.guid)
            sqlite_cursor.execute(sql, sql_args)

        for slot in split.slots:
            cls.write_slot_to_sqlite(slot, sqlite_cursor, split.guid)

    @classmethod
    def write_scheduled_transaction_to_sqlite(
            cls,
            scheduled_transaction: ScheduledTransaction,
            sqlite_cursor: sqlite3.Cursor
    ) -> None:
        """
        Writes a ScheduledTransaction object to the SQLite database.

        :param scheduled_transaction: ScheduledTransaction object
        :type scheduled_transaction: ScheduledTransaction
        :param sqlite_cursor: Handle to SQLite file
        :type sqlite_cursor: sqlite3.Cursor
        """
        db_action: DBAction = DBAction.get_db_action(sqlite_cursor, 'schedxactions', 'guid', scheduled_transaction.guid)
        sql: str = ''
        sql_args: tuple = tuple()
        if db_action == DBAction.INSERT:
            sql = 'INSERT INTO schedxactions (guid, name, enabled, start_date, end_date, last_occur, num_occur, ' \
                  'rem_occur, auto_create, auto_notify, adv_creation, adv_notify, instance_count, template_act_guid) ' \
                  'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
            sql_args = (scheduled_transaction.guid, scheduled_transaction.name, scheduled_transaction.enabled,
                        scheduled_transaction.start_date, scheduled_transaction.end_date,
                        scheduled_transaction.last_date, scheduled_transaction.num_occur,
                        scheduled_transaction.rem_occur, scheduled_transaction.auto_create,
                        scheduled_transaction.auto_create_notify, scheduled_transaction.advance_create_days,
                        scheduled_transaction.advance_remind_days, scheduled_transaction.instance_count,
                        scheduled_transaction.template_account.guid if scheduled_transaction.template_account else None)
            sqlite_cursor.execute(sql, sql_args)
        elif db_action == DBAction.UPDATE:
            sql = 'UPDATE schedxactions SET name = ?, enabled = ?, start_date = ?, end_date = ?, last_occur = ?, ' \
                  'num_occur = ?, rem_occur = ?, auto_create = ?, auto_notify = ?, adv_creation = ?, adv_notify = ?, ' \
                  'instance_count = ?, template_act_guid = ? WHERE guid = ?'
            sql_args = (scheduled_transaction.name, scheduled_transaction.enabled,
                        scheduled_transaction.start_date, scheduled_transaction.end_date,
                        scheduled_transaction.last_date, scheduled_transaction.num_occur,
                        scheduled_transaction.rem_occur, scheduled_transaction.auto_create,
                        scheduled_transaction.auto_create_notify, scheduled_transaction.advance_create_days,
                        scheduled_transaction.advance_remind_days, scheduled_transaction.instance_count,
                        scheduled_transaction.template_account.guid if scheduled_transaction.template_account else None,
                        scheduled_transaction.guid)
            sqlite_cursor.execute(sql, sql_args)

    @classmethod
    def create_sqlite_schema(cls, sqlite_cursor: sqlite3.Cursor) -> None:
        """
        Creates the SQLite schema using the provided SQLite cursor.

        :param sqlite_cursor: Open cursor to a SQLite database.
        :type sqlite_cursor: sqlite3.Cursor
        """
        # Note: To update the GnuCash schema, connect to an existing GnuCash SQLite file and run ".schema".
        # Make sure to remove sqlite_sequence from the schema statements
        sqlite_schema_sql_path = pathlib.Path(__file__).parent / 'sqlite_schema.sql'
        with sqlite_schema_sql_path.open(mode='r') as schema_file:
            for line in schema_file.readlines():
                sqlite_cursor.execute(line)


class SqliteFileFormat(GnuCashSQLiteReader, GnuCashSQLiteWriter, BaseFileFormat):  # type: ignore
    """Class containing the logic for loading and saving SQlite files."""
