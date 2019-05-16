"""
Module containing classes that read, manipulate, and write transactions.

.. module:: transaction
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Iterator, List, Optional, Tuple
from xml.etree import ElementTree
from warnings import warn
from sqlite3 import Cursor

from gnewcash.account import Account
from gnewcash.commodity import Commodity
from gnewcash.enums import AccountType
from gnewcash.file_formats import DBAction, GnuCashXMLObject, GnuCashSQLiteObject
from gnewcash.guid_object import GuidObject
from gnewcash.slot import Slot, SlottableObject
from gnewcash.utils import safe_iso_date_parsing, safe_iso_date_formatting


class Transaction(GuidObject, SlottableObject, GnuCashXMLObject, GnuCashSQLiteObject):
    """Represents a transaction in GnuCash."""

    def __init__(self) -> None:
        super(Transaction, self).__init__()
        self.currency: Optional[Commodity] = None
        self.date_posted: Optional[datetime] = None
        self.date_entered: Optional[datetime] = None
        self.description: str = ''
        self.splits: List[Split] = []
        self.memo: Optional[str] = None

    def __str__(self) -> str:
        if self.date_posted:
            return '{} - {}'.format(self.date_posted.strftime('%m/%d/%Y'), self.description)
        return self.description

    def __repr__(self) -> str:
        return str(self)

    @property
    def as_xml(self) -> ElementTree.Element:
        """
        Returns the current transaction as GnuCash-compatible XML.

        :return: Current transaction as XML
        :rtype: xml.etree.ElementTree.Element
        """
        transaction_node: ElementTree.Element = ElementTree.Element('gnc:transaction', {'version': '2.0.0'})
        ElementTree.SubElement(transaction_node, 'trn:id', {'type': 'guid'}).text = self.guid

        if self.currency:
            transaction_node.append(self.currency.as_short_xml('trn:currency'))

        if self.memo:
            ElementTree.SubElement(transaction_node, 'trn:num').text = self.memo

        if self.date_posted:
            date_posted_node = ElementTree.SubElement(transaction_node, 'trn:date-posted')
            ElementTree.SubElement(date_posted_node, 'ts:date').text = safe_iso_date_formatting(self.date_posted)
        if self.date_entered:
            date_entered_node = ElementTree.SubElement(transaction_node, 'trn:date-entered')
            ElementTree.SubElement(date_entered_node, 'ts:date').text = safe_iso_date_formatting(self.date_entered)
        ElementTree.SubElement(transaction_node, 'trn:description').text = self.description

        if self.slots:
            slots_node = ElementTree.SubElement(transaction_node, 'trn:slots')
            for slot in self.slots:
                slots_node.append(slot.as_xml)

        if self.splits:
            splits_node = ElementTree.SubElement(transaction_node, 'trn:splits')
            for split in self.splits:
                splits_node.append(split.as_xml)

        return transaction_node

    @classmethod
    def from_xml(cls, transaction_node: ElementTree.Element, namespaces: Dict[str, str],
                 account_objects: List[Account]) -> 'Transaction':
        """
        Creates a Transaction object from the GnuCash XML.

        :param transaction_node: XML node for the transaction
        :type transaction_node: ElementTree.Element
        :param namespaces: XML namespaces for GnuCash elements
        :type namespaces: dict[str, str]
        :param account_objects: Account objects already created from XML (used for assigning accounts)
        :type account_objects: list[Account]
        :return: Transaction object from XML
        :rtype: Transaction
        """
        transaction: 'Transaction' = cls()
        guid_node: Optional[ElementTree.Element] = transaction_node.find('trn:id', namespaces)
        if guid_node is not None and guid_node.text:
            transaction.guid = guid_node.text
        date_entered_node: Optional[ElementTree.Element] = transaction_node.find('trn:date-entered', namespaces)
        if date_entered_node is not None:
            date_entered_ts_node: Optional[ElementTree.Element] = date_entered_node.find('ts:date', namespaces)
            if date_entered_ts_node is not None and date_entered_ts_node.text:
                transaction.date_entered = safe_iso_date_parsing(date_entered_ts_node.text)
        date_posted_node: Optional[ElementTree.Element] = transaction_node.find('trn:date-posted', namespaces)
        if date_posted_node is not None:
            date_posted_ts_node: Optional[ElementTree.Element] = date_posted_node.find('ts:date', namespaces)
            if date_posted_ts_node is not None and date_posted_ts_node.text:
                transaction.date_posted = safe_iso_date_parsing(date_posted_ts_node.text)

        description_node: Optional[ElementTree.Element] = transaction_node.find('trn:description', namespaces)
        if description_node is not None and description_node.text:
            transaction.description = description_node.text

        memo: Optional[ElementTree.Element] = transaction_node.find('trn:num', namespaces)
        if memo is not None:
            transaction.memo = memo.text

        currency_node = transaction_node.find('trn:currency', namespaces)
        if currency_node is not None:
            currency_id_node = currency_node.find('cmdty:id', namespaces)
            currency_space_node = currency_node.find('cmdty:space', namespaces)
            if currency_id_node is not None and currency_space_node is not None \
                    and currency_id_node.text and currency_space_node.text:
                transaction.currency = Commodity(currency_id_node.text,
                                                 currency_space_node.text)

        slots: Optional[ElementTree.Element] = transaction_node.find('trn:slots', namespaces)
        if slots:
            for slot in slots.findall('slot', namespaces):
                transaction.slots.append(Slot.from_xml(slot, namespaces))

        splits: Optional[ElementTree.Element] = transaction_node.find('trn:splits', namespaces)
        if splits is not None:
            for split in list(splits):
                transaction.splits.append(Split.from_xml(split, namespaces, account_objects))

        return transaction

    def __lt__(self, other: 'Transaction') -> bool:
        if self.date_posted is not None and other.date_posted is not None:
            return self.date_posted < other.date_posted
        if self.date_posted is not None and other.date_posted is None:
            return False
        if self.date_posted is None and other.date_posted is not None:
            return True
        return False

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Transaction):
            return NotImplemented
        return self.date_posted == other.date_posted

    @property
    def cleared(self) -> bool:
        """
        Checks if all splits in the transaction are cleared.

        :return: Boolean indicating if all splits in the transaction are cleared.
        :rtype: bool
        """
        return sum([1 for split in self.splits if split.reconciled_state.lower() == 'c']) > 0

    def mark_transaction_cleared(self) -> None:
        """Marks all splits in the transaction as cleared (reconciled_state = 'c')."""
        for split in self.splits:
            split.reconciled_state = 'c'

    @property
    def notes(self) -> str:
        """
        Notes on the transaction.

        :return: Notes tied to the transaction
        :rtype: str
        """
        return super(Transaction, self).get_slot_value('notes')

    @notes.setter
    def notes(self, value: str) -> None:
        super(Transaction, self).set_slot_value('notes', value, 'string')

    @property
    def reversed_by(self) -> str:
        """
        GUID of the transaction that reverses this transaction.

        :return: Transaction GUID
        :rtype: str
        """
        return super(Transaction, self).get_slot_value('reversed-by')

    @reversed_by.setter
    def reversed_by(self, value: str) -> None:
        super(Transaction, self).set_slot_value('reversed-by', value, 'guid')

    @property
    def voided(self) -> str:
        """
        Void status.

        :return: Void status
        :rtype: str
        """
        return super(Transaction, self).get_slot_value('trans-read-only')

    @voided.setter
    def voided(self, value: str) -> None:
        super(Transaction, self).set_slot_value('trans-read-only', value, 'string')

    @property
    def void_time(self) -> str:
        """
        Time that the transaction was voided.

        :return: Time that the transaction was voided
        :rtype: str
        """
        return super(Transaction, self).get_slot_value('void-time')

    @void_time.setter
    def void_time(self, value: str) -> None:
        super(Transaction, self).set_slot_value('void-time', value, 'string')

    @property
    def void_reason(self) -> str:
        """
        Reason that the transaction was voided.

        :return: Reason that the transaction was voided
        :rtype: str
        """
        return super(Transaction, self).get_slot_value('void-reason')

    @void_reason.setter
    def void_reason(self, value: str) -> None:
        super(Transaction, self).set_slot_value('void-reason', value, 'string')

    @property
    def associated_uri(self) -> str:
        """
        URI associated with the transaction.

        :return: URI associated with the transaction
        :rtype: str
        """
        return super(Transaction, self).get_slot_value('assoc_uri')

    @associated_uri.setter
    def associated_uri(self, value: str) -> None:
        super(Transaction, self).set_slot_value('assoc_uri', value, 'string')

    @classmethod
    def from_sqlite(cls, sqlite_cursor: Cursor, root_account: Account,
                    template_root_account: Account) -> List['Transaction']:
        """
        Creates Transaction objects from the GnuCash XML.

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
        new_transactions = []
        for transaction in transaction_data:
            new_transaction = cls()
            new_transaction.guid = transaction['guid']
            new_transaction.memo = transaction['num']
            new_transaction.date_posted = datetime.strptime(transaction['post_date'], '%Y-%m-%d %H:%M:%S')
            new_transaction.date_entered = datetime.strptime(transaction['enter_date'], '%Y-%m-%d %H:%M:%S')
            new_transaction.description = transaction['description']
            new_transaction.currency = Commodity.from_sqlite(sqlite_cursor, commodity_guid=transaction['currency_guid'])
            new_transaction.slots = Slot.from_sqlite(sqlite_cursor, transaction['guid'])
            new_transaction.splits = Split.from_sqlite(sqlite_cursor, transaction['guid'], root_account,
                                                       template_root_account)
            new_transactions.append(new_transaction)
        return new_transactions

    def to_sqlite(self, sqlite_cursor: Cursor) -> None:
        db_action: DBAction = self.get_db_action(sqlite_cursor, 'transactions', 'guid', self.guid)
        sql: str = ''
        sql_args: Tuple = tuple()
        if db_action == DBAction.INSERT:
            sql = '''
INSERT INTO transactions(guid, currency_guid, num, post_date, enter_date, description)
VALUES (?, ?, ?, ?, ?, ?)'''.strip()
            sql_args = (self.guid, self.currency.guid, self.memo, self.date_posted, self.date_entered, 
                        self.description)
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
            sql_args = (self.currency.guid if self.currency else None, self.memo, self.date_posted, self.date_entered,
                        self.description, self.guid)
            sqlite_cursor.execute(sql, sql_args)
        
        # TODO: slots
        # TODO: splits


GnuCashSQLiteObject.register(Transaction)


class Split(GuidObject, GnuCashXMLObject, GnuCashSQLiteObject):
    """Represents a split in GnuCash."""

    def __init__(self, account: Optional[Account], amount: Optional[Decimal], reconciled_state: str = 'n'):
        super(Split, self).__init__()
        self.reconciled_state: str = reconciled_state
        self.amount: Optional[Decimal] = amount
        self.account: Optional[Account] = account
        self.action: Optional[str] = None
        self.memo: Optional[str] = None
        self.quantity_denominator: str = '100'

    def __str__(self) -> str:
        return '{} - {}'.format(self.account, str(self.amount))

    def __repr__(self) -> str:
        return str(self)

    @property
    def as_xml(self) -> ElementTree.Element:
        """
        Returns the current split as GnuCash-compatible XML.

        :return: Current split as XML
        :rtype: xml.etree.ElementTree.Element
        """
        split_node: ElementTree.Element = ElementTree.Element('trn:split')
        ElementTree.SubElement(split_node, 'split:id', {'type': 'guid'}).text = self.guid

        if self.memo:
            ElementTree.SubElement(split_node, 'split:memo').text = self.memo
        if self.action:
            ElementTree.SubElement(split_node, 'split:action').text = self.action

        ElementTree.SubElement(split_node, 'split:reconciled-state').text = self.reconciled_state
        if self.amount is not None:
            ElementTree.SubElement(split_node, 'split:value').text = str(int(self.amount * 100)) + '/100'
            ElementTree.SubElement(split_node, 'split:quantity').text = '/'.join([
                str(int(self.amount * 100)), self.quantity_denominator])
        if self.account:
            ElementTree.SubElement(split_node, 'split:account', {'type': 'guid'}).text = self.account.guid
        return split_node

    @classmethod
    def from_xml(cls, split_node: ElementTree.Element, namespaces: Dict[str, str],
                 account_objects: List[Account]) -> 'Split':
        """
        Creates an Split object from the GnuCash XML.

        :param split_node: XML node for the split
        :type split_node: ElementTree.Element
        :param namespaces: XML namespaces for GnuCash elements
        :type namespaces: dict[str, str]
        :param account_objects: Account objects already created from XML (used for assigning parent account)
        :type account_objects: list[Account]
        :return: Split object from XML
        :rtype: Split
        """
        account_node: Optional[ElementTree.Element] = split_node.find('split:account', namespaces)
        if account_node is None or not account_node.text:
            raise ValueError('Invalid or missing split:account node')
        account: str = account_node.text

        value_node: Optional[ElementTree.Element] = split_node.find('split:value', namespaces)
        if value_node is None or not value_node.text:
            raise ValueError('Invalid or missing split:value node')
        value_str: str = value_node.text
        value: Decimal = Decimal(value_str[:value_str.find('/')]) / Decimal(100)

        reconciled_state_node: Optional[ElementTree.Element] = split_node.find('split:reconciled-state', namespaces)
        if reconciled_state_node is None or not reconciled_state_node.text:
            raise ValueError('Invalid or missing split:reconciled-state node')
        new_split = cls([x for x in account_objects if x.guid == account][0],
                        value, reconciled_state_node.text)
        guid_node = split_node.find('split:id', namespaces)
        if guid_node is not None and guid_node.text:
            new_split.guid = guid_node.text

        split_memo: Optional[ElementTree.Element] = split_node.find('split:memo', namespaces)
        if split_memo is not None:
            new_split.memo = split_memo.text

        split_action: Optional[ElementTree.Element] = split_node.find('split:action', namespaces)
        if split_action is not None:
            new_split.action = split_action.text

        quantity_node = split_node.find('split:quantity', namespaces)
        if quantity_node is not None:
            quantity = quantity_node.text
            if quantity is not None and '/' in quantity:
                new_split.quantity_denominator = quantity.split('/')[1]

        return new_split

    @classmethod
    def from_sqlite(cls, sqlite_cursor: Cursor, transaction_guid: str, root_account: Account,
                    template_root_account: Account) -> List['Split']:
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
            account_object = root_account.get_subaccount_by_id(split['account_guid']) or \
                template_root_account.get_subaccount_by_id(split['account_guid'])
            new_split = cls(account_object, split['value_num'] / split['value_denom'], split['reconcile_state'])
            new_split.guid = split['guid']
            new_split.memo = split['memo']
            new_split.action = split['action']
            # TODO: reconcile_date
            # TODO: quantity_num
            new_split.quantity_denominator = split['quantity_denom']
            # TODO: lot_guid

            new_splits.append(new_split)
        return new_splits

    def to_sqlite(self, sqlite_cursor: Cursor, transaction_guid: str) -> None:
        db_action: DBAction = self.get_db_action(sqlite_cursor, 'splits', 'guid', self.guid)
        sql: str = ''
        sql_args: Tuple = tuple()
        if db_action == DBAction.INSERT:
            sql = '''
INSERT INTO splits(guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom,
                   quantity_num, quantity_denom, lot_guid)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''.strip()
            sql_args = (self.guid, transaction_guid, self.account.guid, self.reconciled_state,
                        None,  # TODO: reconcile_date
                        None,  # TODO: value_num
                        None,  # TODO: value_denom
                        None,  # TODO: quantity_num
                        self.quantity_denominator,
                        None)  # TODO: lot_guid
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
    quantity_num ?,
    quantity_denom = ?,
    lot_guid = ?
WHERE guid = ?'''.strip()
        sql_args = (transaction_guid, self.account.guid if self.account else None, self.reconciled_state,
                    None,  # TODO: reconcile_date
                    None,  # TODO: value_num
                    None,  # TODO: value_denom
                    None,  # TODO: quantity_num
                    self.quantity_denominator,
                    None,  # TODO: lot_guid
                    self.guid)
        sqlite_cursor.execute(sql, sql_args)


GnuCashSQLiteObject.register(Split)


class TransactionManager:
    """Class used to add/remove transactions, maintaining a chronological order based on transaction posted date."""

    def __init__(self) -> None:
        self.transactions: List[Transaction] = list()
        self.disable_sort: bool = False

    def add(self, new_transaction: Transaction) -> None:
        """
        Adds a transaction to the transaction manager.

        :param new_transaction: Transaction to add
        :type new_transaction: Transaction
        """
        if new_transaction.date_posted is None or self.disable_sort:
            self.transactions.append(new_transaction)
        elif not self.disable_sort:
            # Inserting transactions in order
            for index, transaction in enumerate(self.transactions):
                if not transaction.date_posted:
                    continue
                if transaction.date_posted > new_transaction.date_posted:
                    self.transactions.insert(index, new_transaction)
                    break
                elif transaction.date_posted == new_transaction.date_posted:
                    self.transactions.insert(index, new_transaction)
                    break
            else:
                self.transactions.append(new_transaction)

    def delete(self, transaction: Transaction) -> None:
        """
        Removes a transaction from the transaction manager.

        :param transaction: Transaction to remove
        :type transaction: Transaction
        """
        # We're looking up by GUID here because a simple list remove doesn't work
        for index, iter_transaction in enumerate(self.transactions):
            if iter_transaction.guid == transaction.guid:
                del self.transactions[index]
                break

    def get_transactions(self, account: Optional[Account] = None) -> Iterator[Transaction]:
        """
        Generator function that gets transactions based on a from account and/or to account for the transaction.

        :param account: Account to retrieve transactions for (default None, all transactions)
        :type account: Account
        :return: Generator that produces transactions based on the given from account and/or to account
        :rtype: Iterator[Transaction]
        """
        for transaction in self.transactions:
            if account is None or account in list(map(lambda x: x.account, transaction.splits)):
                yield transaction

    def get_account_starting_balance(self, account: Account) -> Decimal:
        """
        Retrieves the starting balance for the current account, given the list of transactions.

        :param transactions: List of transactions or TransactionManager
        :type transactions: list[Transaction] or TransactionManager
        :return: First transaction amount if the account has transactions, otherwise 0.
        :rtype: decimal.Decimal
        """
        account_transactions: List[Transaction] = [x for x in self.transactions
                                                   if account in [y.account for y in x.splits
                                                                  if y.amount is not None and y.amount >= 0]]
        amount: Decimal = Decimal(0)
        if account_transactions:
            first_transaction: Transaction = account_transactions[0]
            amount = next(filter(lambda x: x.account == account and x.amount is not None and x.amount >= 0,
                                 first_transaction.splits)).amount or Decimal(0)
        return amount

    def get_account_ending_balance(self, account: Account) -> Decimal:
        """
        Retrieves the ending balance for the provided account given the list of transactions in the manager.

        :param account: Account to get the ending balance for
        :type account: Account
        :return: Account starting balance
        :rtype: decimal.Decimal
        """
        return self.get_balance_at_date(account)

    def minimum_balance_past_date(self, account: Account,
                                  date: datetime) -> Tuple[Optional[Decimal], Optional[datetime]]:
        """
        Gets the minimum balance for the account after a certain date, given the list of transactions.

        :param transactions: List of transactions or TransactionManager
        :type transactions: list[Transaction] or TransactionManager
        :param start_date: datetime object representing the date you want to find the minimum balance for.
        :type start_date: datetime.datetime
        :return: Tuple containing the minimum balance (element 0) and the date it's at that balance (element 1)
        :rtype: tuple
        """
        minimum_balance: Optional[Decimal] = None
        minimum_balance_date: Optional[datetime] = None
        iterator_date: datetime = date
        end_date: Optional[datetime] = max(map(lambda x: x.date_posted, self.transactions))
        if end_date is None:
            return None, None
        while iterator_date < end_date:
            iterator_date += timedelta(days=1)
            current_balance: Decimal = self.get_balance_at_date(account, iterator_date)
            if minimum_balance is None or current_balance < minimum_balance:
                minimum_balance, minimum_balance_date = current_balance, iterator_date
        if minimum_balance_date and minimum_balance_date > end_date:
            minimum_balance_date = end_date
        return minimum_balance, minimum_balance_date

    def get_balance_at_date(self, account: Account, date: Optional[datetime] = None) -> Decimal:
        """
        Retrieves the account balance for the current account at a certain date, given the list of transactions.

        If the provided date is None, it will retrieve the ending balance.

        :param transactions: List of transactions or TransactionManager
        :type transactions: list[Transaction] or TransactionManager
        :param date: Last date to consider when determining the account balance.
        :type date: datetime.datetime
        :return: Account balance at specified date (or ending balance) or 0, if no applicable transactions were found.
        :rtype: decimal.Decimal
        """
        balance: Decimal = Decimal(0)
        applicable_transactions: List[Transaction] = []
        for transaction in self.transactions:
            transaction_accounts = list(map(lambda y: y.account, transaction.splits))
            if date is not None and account in transaction_accounts and transaction.date_posted is not None and \
                    transaction.date_posted <= date:
                applicable_transactions.append(transaction)
            elif date is None and account in transaction_accounts:
                applicable_transactions.append(transaction)

        for transaction in applicable_transactions:
            if date is None or (transaction.date_posted is not None and transaction.date_posted <= date):
                applicable_split: Split = next(filter(lambda x: x.account == account, transaction.splits))
                amount: Decimal = applicable_split.amount or Decimal(0)
                if account.type == AccountType.CREDIT:
                    amount = amount * -1
                balance += amount
        return balance

    # Making TransactionManager iterable
    def __getitem__(self, item: int) -> Transaction:
        if item > len(self):
            raise IndexError
        return self.transactions[item]

    def __len__(self) -> int:
        return len(self.transactions)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TransactionManager):
            return NotImplemented
        for my_transaction, other_transaction in zip(self.transactions, other.transactions):
            if my_transaction != other_transaction:
                return False
        return True

    def __iter__(self) -> Iterator[Transaction]:
        yield from self.transactions


class ScheduledTransaction(GuidObject, GnuCashXMLObject, GnuCashSQLiteObject):
    """Class that represents a scheduled transaction in Gnucash."""

    def __init__(self) -> None:
        super(ScheduledTransaction, self).__init__()
        self.name: Optional[str] = None
        self.enabled: Optional[bool] = False
        self.auto_create: Optional[bool] = False
        self.auto_create_notify: Optional[bool] = False
        self.advance_create_days: Optional[int] = -1
        self.advance_remind_days: Optional[int] = -1
        self.instance_count: Optional[int] = 0
        self.start_date: Optional[datetime] = None
        self.last_date: Optional[datetime] = None
        self.end_date: Optional[datetime] = None
        self.template_account: Optional[Account] = None
        self.recurrence_multiplier: Optional[int] = 0
        self.recurrence_period: Optional[str] = None
        self.recurrence_start: Optional[datetime] = None

    @property
    def as_xml(self) -> ElementTree.Element:
        """
        Returns the current scheduled transaction as GnuCash-compatible XML.

        :return: Current scheduled transaction as XML
        :rtype: xml.etree.ElementTree.Element
        """
        xml_node: ElementTree.Element = ElementTree.Element('gnc:schedxaction', attrib={'version': '2.0.0'})
        if self.guid:
            ElementTree.SubElement(xml_node, 'sx:id', attrib={'type': 'guid'}).text = self.guid
        if self.name:
            ElementTree.SubElement(xml_node, 'sx:name').text = self.name
        ElementTree.SubElement(xml_node, 'sx:enabled').text = 'y' if self.enabled else 'n'
        ElementTree.SubElement(xml_node, 'sx:autoCreate').text = 'y' if self.auto_create else 'n'
        ElementTree.SubElement(xml_node, 'sx:autoCreateNotify').text = 'y' if self.auto_create_notify else 'n'
        if self.advance_create_days is not None:
            ElementTree.SubElement(xml_node, 'sx:advanceCreateDays').text = str(self.advance_create_days)
        if self.advance_remind_days is not None:
            ElementTree.SubElement(xml_node, 'sx:advanceRemindDays').text = str(self.advance_remind_days)
        if self.instance_count is not None:
            ElementTree.SubElement(xml_node, 'sx:instanceCount').text = str(self.instance_count)
        if self.start_date:
            start_node = ElementTree.SubElement(xml_node, 'sx:start')
            ElementTree.SubElement(start_node, 'gdate').text = self.start_date.strftime('%Y-%m-%d')
        if self.last_date:
            last_node = ElementTree.SubElement(xml_node, 'sx:last')
            ElementTree.SubElement(last_node, 'gdate').text = self.last_date.strftime('%Y-%m-%d')
        if self.end_date:
            end_node = ElementTree.SubElement(xml_node, 'sx:end')
            ElementTree.SubElement(end_node, 'gdate').text = self.end_date.strftime('%Y-%m-%d')
        if self.template_account:
            ElementTree.SubElement(xml_node, 'sx:templ-acct', attrib={'type': 'guid'}).text = self.template_account.guid
        if self.recurrence_multiplier is not None or self.recurrence_period is not None \
                or self.recurrence_start is not None:
            schedule_node = ElementTree.SubElement(xml_node, 'sx:schedule')
            recurrence_node = ElementTree.SubElement(schedule_node, 'gnc:recurrence', attrib={'version': '1.0.0'})
            if self.recurrence_multiplier:
                ElementTree.SubElement(recurrence_node, 'recurrence:mult').text = str(self.recurrence_multiplier)
            if self.recurrence_period:
                ElementTree.SubElement(recurrence_node, 'recurrence:period_type').text = self.recurrence_period
            if self.recurrence_start:
                start_node = ElementTree.SubElement(recurrence_node, 'recurrence:start')
                ElementTree.SubElement(start_node, 'gdate').text = self.recurrence_start.strftime('%Y-%m-%d')
        return xml_node

    @classmethod
    def from_xml(cls, xml_obj: ElementTree.Element, namespaces: Dict[str, str],
                 template_account_root: Optional[Account]) -> 'ScheduledTransaction':
        """
        Creates a ScheduledTransaction object from the GnuCash XML.

        :param xml_obj: XML node for the scheduled transaction
        :type xml_obj: ElementTree.Element
        :param namespaces: XML namespaces for GnuCash elements
        :type namespaces: dict[str, str]
        :param template_account_root: Root template account
        :type template_account_root: Account
        :return: ScheduledTransaction object from XML
        :rtype: ScheduledTransaction
        """
        new_obj: 'ScheduledTransaction' = cls()
        sx_transaction_guid: Optional[str] = cls.read_xml_child_text(xml_obj, 'sx:id', namespaces)
        if sx_transaction_guid is not None and sx_transaction_guid:
            new_obj.guid = sx_transaction_guid
        new_obj.name = cls.read_xml_child_text(xml_obj, 'sx:name', namespaces)
        new_obj.enabled = cls.read_xml_child_boolean(xml_obj, 'sx:enabled', namespaces)
        new_obj.auto_create = cls.read_xml_child_boolean(xml_obj, 'sx:autoCreate', namespaces)
        new_obj.auto_create_notify = cls.read_xml_child_boolean(xml_obj, 'sx:autoCreateNotify', namespaces)
        new_obj.advance_create_days = cls.read_xml_child_int(xml_obj, 'sx:advanceCreateDays', namespaces)
        new_obj.advance_remind_days = cls.read_xml_child_int(xml_obj, 'sx:advanceRemindDays', namespaces)
        new_obj.instance_count = cls.read_xml_child_int(xml_obj, 'sx:instanceCount', namespaces)
        new_obj.start_date = cls.read_xml_child_date(xml_obj, 'sx:start', namespaces)
        new_obj.last_date = cls.read_xml_child_date(xml_obj, 'sx:last', namespaces)
        new_obj.end_date = cls.read_xml_child_date(xml_obj, 'sx:end', namespaces)

        template_account_node: Optional[ElementTree.Element] = xml_obj.find('sx:templ-acct', namespaces)
        if template_account_node is not None and template_account_node.text and template_account_root is not None:
            new_obj.template_account = template_account_root.get_subaccount_by_id(template_account_node.text)

        schedule_node: Optional[ElementTree.Element] = xml_obj.find('sx:schedule', namespaces)
        if schedule_node is not None:
            recurrence_node = schedule_node.find('gnc:recurrence', namespaces)
            if recurrence_node is not None:
                new_obj.recurrence_multiplier = cls.read_xml_child_int(
                    recurrence_node, 'recurrence:mult', namespaces
                )
                new_obj.recurrence_period = cls.read_xml_child_text(
                    recurrence_node, 'recurrence:period_type', namespaces)
                new_obj.recurrence_start = cls.read_xml_child_date(
                    recurrence_node, 'recurrence:start', namespaces)

        return new_obj

    # TODO: Move these read functions to GnuCashXMLObject and refactor

    @classmethod
    def read_xml_child_text(cls, xml_object: ElementTree.Element, tag_name: str,
                            namespaces: Dict[str, str]) -> Optional[str]:
        """
        Reads the text from a specific child XML element.

        :param xml_object: Current XML object
        :type xml_object: ElementTree.Element
        :param tag_name: Child tag name
        :type tag_name: str
        :param namespaces: GnuCash namespaces
        :type namespaces: dict[str, str]
        :return: Child node's text
        :rtype: str
        """
        target_node: Optional[ElementTree.Element] = xml_object.find(tag_name, namespaces)
        if target_node is not None:
            return target_node.text
        return None

    @classmethod
    def read_xml_child_boolean(cls, xml_object: ElementTree.Element, tag_name: str,
                               namespaces: Dict[str, str]) -> Optional[bool]:
        """
        Reads the text from a specific child XML element and returns a Boolean if the text is "Y" or "y".

        :param xml_object: Current XML object
        :type xml_object: ElementTree.Element
        :param tag_name: Child tag name
        :type tag_name: str
        :param namespaces: GnuCash namespaces
        :type namespaces: dict[str, str]
        :return: True if child node's text is "Y" or "Y", otherwise False.
        :rtype: bool
        """
        node_text: Optional[str] = cls.read_xml_child_text(xml_object, tag_name, namespaces)
        if node_text and node_text.lower() == 'y':
            return True
        if node_text:
            return False
        return None

    @classmethod
    def read_xml_child_int(cls, xml_object: ElementTree.Element, tag_name: str,
                           namespaces: Dict[str, str]) -> Optional[int]:
        """
        Reads the text from a specific child XML element and returns its text as an integer value.

        :param xml_object: Current XML object
        :type xml_object: ElementTree.Element
        :param tag_name: Child tag name
        :type tag_name: str
        :param namespaces: GnuCash namespaces
        :type namespaces: dict[str, str]
        :return: Child's text as an integer value
        :rtype: int
        """
        node_text: Optional[str] = cls.read_xml_child_text(xml_object, tag_name, namespaces)
        if node_text:
            return int(node_text)
        return None

    @classmethod
    def read_xml_child_date(cls, xml_object: ElementTree.Element, tag_name: str,
                            namespaces: Dict[str, str]) -> Optional[datetime]:
        """
        Reads the text from a specific child XML element and returns its inner gdate text as a datetime.

        :param xml_object: Current XML object
        :type xml_object: ElementTree.Element
        :param tag_name: Child tag name
        :type tag_name: str
        :param namespaces: GnuCash namespaces
        :type namespaces: dict[str, str]
        :return: Child's gdate's text as datetime
        :rtype: datetime.datetime
        """
        target_node: Optional[ElementTree.Element] = xml_object.find(tag_name, namespaces)
        if target_node is None:
            return None

        date_node: Optional[ElementTree.Element] = target_node.find('gdate', namespaces)
        if date_node is None:
            return None

        return datetime.strptime(date_node.text, '%Y-%m-%d') if date_node.text else None

    @classmethod
    def from_sqlite(cls, sqlite_cursor: Cursor, template_root_account: Account) -> List['ScheduledTransaction']:
        """
        Creates ScheduledTransaction objects from the GnuCash SQLite database.

        :param sqlite_cursor: Open cursor to the SQLite database
        :type sqlite_cursor: sqlite3.Cursor
        :param template_account_root: Root template account
        :type template_account_root: Account
        :return: ScheduledTransaction objects from SQLite
        :rtype: list[ScheduledTransaction]
        """
        scheduled_transactions = cls.get_sqlite_table_data(sqlite_cursor, 'schedxactions')
        new_scheduled_transactions = []
        for scheduled_transaction in scheduled_transactions:
            new_scheduled_transaction = cls()
            new_scheduled_transaction.guid = scheduled_transaction['guid']
            new_scheduled_transaction.name = scheduled_transaction['name']
            new_scheduled_transaction.enabled = scheduled_transaction['enabled'] == 1
            new_scheduled_transaction.start_date = datetime.strptime(scheduled_transaction['start_date'], '%Y%m%d')
            new_scheduled_transaction.end_date = datetime.strptime(scheduled_transaction['end_date'], '%Y%m%d')
            new_scheduled_transaction.last_date = datetime.strptime(scheduled_transaction['last_occur'], '%Y%m%d')
            # TODO: num_occur
            # TODO: rem_occur
            new_scheduled_transaction.auto_create = scheduled_transaction['auto_create'] == 1
            new_scheduled_transaction.auto_create_notify = scheduled_transaction['auto_notify'] == 1
            new_scheduled_transaction.advance_create_days = scheduled_transaction['adv_creation']
            new_scheduled_transaction.advance_remind_days = scheduled_transaction['adv_notify']
            new_scheduled_transaction.instance_count = scheduled_transaction['instance_count']
            new_scheduled_transaction.template_account = template_root_account.get_subaccount_by_id(
                scheduled_transaction['template_act_guid'])

            recurrence_info, = cls.get_sqlite_table_data(sqlite_cursor, 'recurrences', 'obj_guid = ?',
                                                         (new_scheduled_transaction.guid,))

            new_scheduled_transaction.recurrence_multiplier = recurrence_info['recurrence_mult']
            new_scheduled_transaction.recurrence_start = datetime.strptime(recurrence_info['recurrence_period_start'],
                                                                           '%Y%m%d')
            new_scheduled_transaction.recurrence_period = recurrence_info['recurrence_period_type']
            # TODO: recurrence_weekend_adjust

            new_scheduled_transactions.append(new_scheduled_transaction)
        return new_scheduled_transactions

    def to_sqlite(self, sqlite_cursor: Cursor) -> None:
        raise NotImplementedError


GnuCashSQLiteObject.register(ScheduledTransaction)


class SimpleTransaction(Transaction):
    """Class used to simplify creating and manipulating Transactions that only have 2 splits."""

    def __init__(self) -> None:
        super(SimpleTransaction, self).__init__()
        self.from_split: Split = Split(None, None)
        self.to_split: Split = Split(None, None)
        self.splits: List[Split] = [self.from_split, self.to_split]

    @classmethod
    def from_xml(cls, transaction_node: ElementTree.Element, namespaces: Dict[str, str],
                 account_objects: List[Account]) -> 'SimpleTransaction':
        """
        Creates a SimpleTransaction object from the GnuCash XML.

        :param transaction_node: XML node for the transaction
        :type transaction_node: ElementTree.Element
        :param namespaces: XML namespaces for GnuCash elements
        :type namespaces: dict[str, str]
        :param account_objects: Account objects already created from XML (used for assigning accounts)
        :type account_objects: list[Account]
        :return: Transaction object from XML
        :rtype: Transaction
        """
        transaction: Transaction = super(SimpleTransaction, cls).from_xml(transaction_node, namespaces, account_objects)
        new_object: 'SimpleTransaction' = cls()
        new_object.__dict__.update(transaction.__dict__)

        # Remove the two splits created by the SimpleTransaction constructor
        new_object.splits = list(filter(lambda x: x.account is not None and x.amount is not None,
                                        new_object.splits))
        if new_object.splits and len(new_object.splits) > 2:
            warn('Transaction {} is a SimpleTransaction but has more than one split. '.format(new_object.guid) +
                 'Using the from_account, to_account, and amount SimpleTransaction fields will result in undesirable ' +
                 'behavior.')

        from_split = list(filter(lambda x: x.amount is not None and x.amount < 0, new_object.splits))
        if from_split:
            new_object.from_split = from_split[0]
        elif new_object.splits:
            warn('Transaction {} does not have a deterministic "from" split. '.format(new_object.guid) +
                 'Assuming first split in transaction: {}'.format(str(new_object.splits[0])))
            new_object.from_split = new_object.splits[0]
        else:
            new_object.splits.append(new_object.from_split)

        to_split = list(filter(lambda x: x.amount is not None and x.amount > 0, new_object.splits))
        if to_split:
            new_object.to_split = to_split[0]
        elif new_object.splits:
            warn('Transaction {} does not have a deterministic "to" split. '.format(new_object.guid) +
                 'Assuming last split in transaction: {}'.format(str(new_object.splits[-1])))
            new_object.to_split = new_object.splits[-1]
        else:
            new_object.splits.append(new_object.to_split)

        return new_object

    @property
    def from_account(self) -> Optional[Account]:
        """
        Account which the transaction transfers funds from.

        :return: Account which the transaction transfers funds from.
        :rtype: Account
        """
        return self.from_split.account

    @from_account.setter
    def from_account(self, value: 'Account') -> None:
        self.from_split.account = value

    @property
    def to_account(self) -> Optional[Account]:
        """
        Account which the transaction transfers funds to.

        :return: Account which the transaction transfers funds to.
        :rtype: Account
        """
        return self.to_split.account

    @to_account.setter
    def to_account(self, value: Account) -> None:
        self.to_split.account = value

    @property
    def amount(self) -> Optional[Decimal]:
        """
        Dollar amount for funds transferred.

        :return: Dollar amount for funds transferred.
        :rtype: decimal.Decimal
        """
        return self.to_split.amount

    @amount.setter
    def amount(self, value: Decimal) -> None:
        self.from_split.amount = value * -1
        self.to_split.amount = value
