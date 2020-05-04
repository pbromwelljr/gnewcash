"""
Module containing the logic for loading and saving XML files.

.. module:: xml
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""
import gzip
import logging
import pathlib
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from xml.dom import minidom
from xml.etree import ElementTree

from gnewcash.account import Account
from gnewcash.commodity import Commodity
from gnewcash.file_formats.base import BaseFileFormat, BaseFileReader, BaseFileWriter
from gnewcash.gnucash_file import Book, Budget, GnuCashFile
from gnewcash.slot import Slot
from gnewcash.transaction import ScheduledTransaction, Split, Transaction, TransactionManager
from gnewcash.utils import safe_iso_date_formatting, safe_iso_date_parsing

XML_NAMESPACES: Dict[str, str] = {
    'gnc': 'http://www.gnucash.org/XML/gnc',
    'act': 'http://www.gnucash.org/XML/act',
    'book': 'http://www.gnucash.org/XML/book',
    'cd': 'http://www.gnucash.org/XML/cd',
    'cmdty': 'http://www.gnucash.org/XML/cmdty',
    'price': 'http://www.gnucash.org/XML/price',
    'slot': 'http://www.gnucash.org/XML/slot',
    'split': 'http://www.gnucash.org/XML/split',
    'sx': 'http://www.gnucash.org/XML/sx',
    'trn': 'http://www.gnucash.org/XML/trn',
    'ts': 'http://www.gnucash.org/XML/ts',
    'fs': 'http://www.gnucash.org/XML/fs',
    'bgt': 'http://www.gnucash.org/XML/bgt',
    'recurrence': 'http://www.gnucash.org/XML/recurrence',
    'lot': 'http://www.gnucash.org/XML/lot',
    'addr': 'http://www.gnucash.org/XML/addr',
    'owner': 'http://www.gnucash.org/XML/owner',
    'billterm': 'http://www.gnucash.org/XML/billterm',
    'bt-days': 'http://www.gnucash.org/XML/bt-days',
    'bt-prox': 'http://www.gnucash.org/XML/bt-prox',
    'cust': 'http://www.gnucash.org/XML/cust',
    'employee': 'http://www.gnucash.org/XML/employee',
    'entry': 'http://www.gnucash.org/XML/entry',
    'invoice': 'http://www.gnucash.org/XML/invoice',
    'job': 'http://www.gnucash.org/XML/job',
    'order': 'http://www.gnucash.org/XML/order',
    'taxtable': 'http://www.gnucash.org/XML/taxtable',
    'tte': 'http://www.gnucash.org/XML/tte',
    'vendor': 'http://www.gnucash.org/XML/vendor'
}


class GnuCashXMLReader(BaseFileReader):
    """Class containing the logic for loading XML files."""

    LOGGER = logging.getLogger()

    @classmethod
    def load(cls, *args: Any, source_file: str = '', sort_transactions: bool = True, **kwargs: Any) -> GnuCashFile:
        """
        Loads a GnuCash XML file from disk to memory.

        :param source_file: File to load from disk
        :type source_file: str
        :param sort_transactions: Should transactions be sorted by date posted
        :type sort_transactions: bool
        :return: GnuCashFile object
        :rtype: GnuCashFile
        """
        built_file: GnuCashFile = GnuCashFile()
        built_file.file_name = source_file

        source_path: pathlib.Path = pathlib.Path(source_file)
        if not source_path.exists():
            cls.LOGGER.warning('Could not find %s', source_file)
            return built_file

        root: ElementTree.Element = cls.get_xml_root(source_path)

        books: List[ElementTree.Element] = root.findall('gnc:book', XML_NAMESPACES)
        for book in books:
            new_book: Book = cls.create_book_from_xml(book, sort_transactions=sort_transactions)
            built_file.books.append(new_book)
        return built_file

    @classmethod
    def get_xml_root(cls, source_path: pathlib.Path) -> ElementTree.Element:
        """
        Retrieves the root element from a given XML document.

        :param source_path: Path to XML document
        :type source_path: pathlib.Path
        :return: Root element
        :rtype: ElementTree.Element
        """
        return ElementTree.parse(source=str(source_path)).getroot()

    @classmethod
    def create_book_from_xml(cls, book_node: ElementTree.Element, sort_transactions: bool = True) -> Book:
        """
        Creates a Book object from the GnuCash XML.

        :param book_node: XML node for the book
        :type book_node: ElementTree.Element
        :param sort_transactions: Flag for if transactions should be sorted by date_posted when reading from XML
        :type sort_transactions: bool
        :return: Book object from XML
        :rtype: Book
        """
        new_book = Book()
        book_id_node: Optional[ElementTree.Element] = book_node.find('book:id', XML_NAMESPACES)
        if book_id_node is not None and book_id_node.text:
            new_book.guid = book_id_node.text
        accounts: List[ElementTree.Element] = book_node.findall('gnc:account', XML_NAMESPACES)
        transactions: List[ElementTree.Element] = book_node.findall('gnc:transaction', XML_NAMESPACES)
        slots: Optional[ElementTree.Element] = book_node.find('book:slots', XML_NAMESPACES)

        if slots is not None:
            for slot in slots.findall('slot'):
                new_book.slots.append(cls.create_slot_from_xml(slot))

        commodities: List[ElementTree.Element] = book_node.findall('gnc:commodity', XML_NAMESPACES)
        for commodity in commodities:
            new_book.commodities.append(cls.create_commodity_from_xml(commodity))

        account_objects: List[Account] = []
        transaction_manager: TransactionManager = TransactionManager()
        transaction_manager.disable_sort = not sort_transactions

        for account in accounts:
            account_objects.append(cls.create_account_from_xml(account, account_objects))

        for transaction in transactions:
            transaction_manager.add(cls.create_transaction_from_xml(transaction, account_objects))

        new_book.root_account = [x for x in account_objects if x.type == 'ROOT'][0]
        new_book.transactions = transaction_manager

        template_transactions_xml: Optional[List[ElementTree.Element]] = book_node.findall('gnc:template-transactions',
                                                                                           XML_NAMESPACES)
        if template_transactions_xml is not None:
            template_accounts: List[Account] = []
            template_transactions: List[Transaction] = []
            for template_transaction in template_transactions_xml:
                # Process accounts before transactions
                for subelement in template_transaction:
                    if not subelement.tag.endswith('account'):
                        continue
                    template_accounts.append(cls.create_account_from_xml(subelement, template_accounts))

                for subelement in template_transaction:
                    if not subelement.tag.endswith('transaction'):
                        continue
                    template_transactions.append(cls.create_transaction_from_xml(subelement, template_accounts))
            new_book.template_transactions = template_transactions
            template_root_accounts: List[Account] = [x for x in template_accounts if x.type == 'ROOT']
            if template_root_accounts:
                new_book.template_root_account = template_root_accounts[0]

        scheduled_transactions: Optional[List[ElementTree.Element]] = book_node.findall('gnc:schedxaction',
                                                                                        XML_NAMESPACES)
        if scheduled_transactions is not None:
            for scheduled_transaction in scheduled_transactions:
                new_book.scheduled_transactions.append(
                    cls.create_scheduled_transaction_from_xml(scheduled_transaction, new_book.template_root_account))

        budgets: Optional[List[ElementTree.Element]] = book_node.findall('gnc:budget', XML_NAMESPACES)
        if budgets is not None:
            for budget in budgets:
                new_book.budgets.append(cls.create_budget_from_xml(budget))

        return new_book

    @classmethod
    def create_slot_from_xml(cls, slot_node: ElementTree.Element) -> Slot:
        """
        Creates a Slot object from the GnuCash XML.

        :param slot_node: XML node for the slot
        :type slot_node: ElementTree.Element
        :return: Slot object from XML
        :rtype: Slot
        """
        key_node: Optional[ElementTree.Element] = slot_node.find('slot:key', XML_NAMESPACES)
        if key_node is None or not key_node.text:
            raise ValueError('slot:key missing or empty in slot node')
        key: str = key_node.text
        value_node: Optional[ElementTree.Element] = slot_node.find('slot:value', XML_NAMESPACES)
        if value_node is None:
            raise ValueError('slot:value missing in slot node')
        slot_type = value_node.attrib['type']
        value: Any = None
        if slot_type == 'gdate':
            value_gdate_node: Optional[ElementTree.Element] = value_node.find('gdate')
            if value_gdate_node is None:
                raise ValueError('slot type is gdate but missing gdate node')
            if not value_gdate_node.text:
                raise ValueError('slot type is gdate but gdate node is empty')
            value = datetime.strptime(value_gdate_node.text, '%Y-%m-%d')
        elif slot_type in ['string', 'guid', 'numeric']:
            value = value_node.text
        elif slot_type == 'integer' and value_node.text:
            value = int(value_node.text)
        elif slot_type == 'double' and value_node.text:
            value = Decimal(value_node.text)
        else:
            child_tags: List[str] = list(set(map(lambda x: x.tag, value_node)))
            if len(child_tags) == 1 and child_tags[0] == 'slot':
                value = [cls.create_slot_from_xml(x) for x in value_node]
            elif slot_type == 'frame':
                value = None  # Empty frame element, just leave it
            else:
                raise NotImplementedError('Slot type {} is not implemented.'.format(slot_type))

        return Slot(key, value, slot_type)

    @classmethod
    def create_commodity_from_xml(cls, commodity_node: ElementTree.Element) -> Commodity:
        """
        Creates a Commodity object from the GnuCash XML.

        :param commodity_node: XML node for the commodity
        :type commodity_node: ElementTree.Element
        :return: Commodity object from XML
        :rtype: Commodity
        """
        commodity_id_node: Optional[ElementTree.Element] = commodity_node.find('cmdty:id', XML_NAMESPACES)
        if commodity_id_node is None or not commodity_id_node.text:
            raise ValueError('Commodity node is missing id')
        commodity_id: str = commodity_id_node.text
        commodity_space_node: Optional[ElementTree.Element] = commodity_node.find('cmdty:space', XML_NAMESPACES)
        if commodity_space_node is None or not commodity_space_node.text:
            raise ValueError('Commodity node is missing space')
        space: str = commodity_space_node.text
        new_commodity: Commodity = Commodity(commodity_id, space)
        if commodity_node.find('cmdty:get_quotes', XML_NAMESPACES) is not None:
            new_commodity.get_quotes = True

        quote_source_node = commodity_node.find('cmdty:quote_source', XML_NAMESPACES)
        if quote_source_node is not None:
            new_commodity.quote_source = quote_source_node.text

        if commodity_node.find('quote_tz', XML_NAMESPACES) is not None:
            new_commodity.quote_tz = True

        name_node: Optional[ElementTree.Element] = commodity_node.find('cmdty:name', XML_NAMESPACES)
        if name_node is not None:
            new_commodity.name = name_node.text

        xcode_node: Optional[ElementTree.Element] = commodity_node.find('cmdty:xcode', XML_NAMESPACES)
        if xcode_node is not None:
            new_commodity.xcode = xcode_node.text

        fraction_node: Optional[ElementTree.Element] = commodity_node.find('cmdty:fraction', XML_NAMESPACES)
        if fraction_node is not None:
            new_commodity.fraction = fraction_node.text

        return new_commodity

    @classmethod
    def create_account_from_xml(cls, account_node: ElementTree.Element, account_objects: List[Account]) -> Account:
        """
        Creates an Account object from the GnuCash XML.

        :param account_node: XML node for the account
        :type account_node: ElementTree.Element
        :param account_objects: Account objects already created from XML (used for assigning parent account)
        :type account_objects: list[Account]
        :return: Account object from XML
        :rtype: Account
        """
        account_object: Account = Account()
        account_guid_node = account_node.find('act:id', XML_NAMESPACES)
        if account_guid_node is None or not account_guid_node.text:
            raise ValueError('Account guid node is missing or empty')
        account_object.guid = account_guid_node.text
        account_name_node = account_node.find('act:name', XML_NAMESPACES)
        if account_name_node is not None and account_name_node.text:
            account_object.name = account_name_node.text
        account_type_node = account_node.find('act:type', XML_NAMESPACES)
        if account_type_node is not None and account_type_node.text:
            account_object.type = account_type_node.text

        commodity: Optional[ElementTree.Element] = account_node.find('act:commodity', XML_NAMESPACES)
        if commodity is not None and commodity.find('cmdty:id', XML_NAMESPACES) is not None:
            account_object.commodity = cls.create_commodity_from_xml(commodity)
        else:
            account_object.commodity = None

        commodity_scu: Optional[ElementTree.Element] = account_node.find('act:commodity-scu', XML_NAMESPACES)
        if commodity_scu is not None:
            account_object.commodity_scu = commodity_scu.text

        slots: Optional[ElementTree.Element] = account_node.find('act:slots', XML_NAMESPACES)
        if slots is not None:
            for slot in slots.findall('slot', XML_NAMESPACES):
                account_object.slots.append(cls.create_slot_from_xml(slot))

        code: Optional[ElementTree.Element] = account_node.find('act:code', XML_NAMESPACES)
        if code is not None:
            account_object.code = code.text

        description: Optional[ElementTree.Element] = account_node.find('act:description', XML_NAMESPACES)
        if description is not None:
            account_object.description = description.text

        parent: Optional[ElementTree.Element] = account_node.find('act:parent', XML_NAMESPACES)
        if parent is not None:
            account_object.parent = [x for x in account_objects if x.guid == parent.text][0]

        return account_object

    @classmethod
    def create_transaction_from_xml(cls, transaction_node: ElementTree.Element,
                                    account_objects: List[Account]) -> Transaction:
        """
        Creates a Transaction object from the GnuCash XML.

        :param transaction_node: XML node for the transaction
        :type transaction_node: ElementTree.Element
        :param account_objects: Account objects already created from XML (used for assigning accounts)
        :type account_objects: list[Account]
        :return: Transaction object from XML
        :rtype: Transaction
        """
        transaction: Transaction = Transaction()
        guid_node: Optional[ElementTree.Element] = transaction_node.find('trn:id', XML_NAMESPACES)
        if guid_node is not None and guid_node.text:
            transaction.guid = guid_node.text
        date_entered_node: Optional[ElementTree.Element] = transaction_node.find('trn:date-entered', XML_NAMESPACES)
        if date_entered_node is not None:
            date_entered_ts_node: Optional[ElementTree.Element] = date_entered_node.find('ts:date', XML_NAMESPACES)
            if date_entered_ts_node is not None and date_entered_ts_node.text:
                transaction.date_entered = safe_iso_date_parsing(date_entered_ts_node.text)
        date_posted_node: Optional[ElementTree.Element] = transaction_node.find('trn:date-posted', XML_NAMESPACES)
        if date_posted_node is not None:
            date_posted_ts_node: Optional[ElementTree.Element] = date_posted_node.find('ts:date', XML_NAMESPACES)
            if date_posted_ts_node is not None and date_posted_ts_node.text:
                transaction.date_posted = safe_iso_date_parsing(date_posted_ts_node.text)

        description_node: Optional[ElementTree.Element] = transaction_node.find('trn:description', XML_NAMESPACES)
        if description_node is not None and description_node.text:
            transaction.description = description_node.text

        memo: Optional[ElementTree.Element] = transaction_node.find('trn:num', XML_NAMESPACES)
        if memo is not None:
            transaction.memo = memo.text

        currency_node = transaction_node.find('trn:currency', XML_NAMESPACES)
        if currency_node is not None:
            currency_id_node = currency_node.find('cmdty:id', XML_NAMESPACES)
            currency_space_node = currency_node.find('cmdty:space', XML_NAMESPACES)
            if currency_id_node is not None and currency_space_node is not None \
                    and currency_id_node.text and currency_space_node.text:
                transaction.currency = Commodity(currency_id_node.text,
                                                 currency_space_node.text)

        slots: Optional[ElementTree.Element] = transaction_node.find('trn:slots', XML_NAMESPACES)
        if slots:
            for slot in slots.findall('slot', XML_NAMESPACES):
                transaction.slots.append(cls.create_slot_from_xml(slot))

        splits: Optional[ElementTree.Element] = transaction_node.find('trn:splits', XML_NAMESPACES)
        if splits is not None:
            for split in list(splits):
                transaction.splits.append(cls.create_split_from_xml(split, account_objects))

        return transaction

    @classmethod
    def create_split_from_xml(cls, split_node: ElementTree.Element, account_objects: List[Account]) -> Split:
        """
        Creates an Split object from the GnuCash XML.

        :param split_node: XML node for the split
        :type split_node: ElementTree.Element
        :param account_objects: Account objects already created from XML (used for assigning parent account)
        :type account_objects: list[Account]
        :return: Split object from XML
        :rtype: Split
        """
        account_node: Optional[ElementTree.Element] = split_node.find('split:account', XML_NAMESPACES)
        if account_node is None or not account_node.text:
            raise ValueError('Invalid or missing split:account node')
        account: str = account_node.text

        value_node: Optional[ElementTree.Element] = split_node.find('split:value', XML_NAMESPACES)
        if value_node is None or not value_node.text:
            raise ValueError('Invalid or missing split:value node')
        value_str: str = value_node.text
        value: Decimal = Decimal(value_str[:value_str.find('/')]) / Decimal(value_str[value_str.find('/') + 1:])

        reconciled_state_node: Optional[ElementTree.Element] = split_node.find('split:reconciled-state',
                                                                               XML_NAMESPACES)
        if reconciled_state_node is None or not reconciled_state_node.text:
            raise ValueError('Invalid or missing split:reconciled-state node')
        new_split = Split([x for x in account_objects if x.guid == account][0],
                          value, reconciled_state_node.text)
        guid_node = split_node.find('split:id', XML_NAMESPACES)
        if guid_node is not None and guid_node.text:
            new_split.guid = guid_node.text

        split_memo: Optional[ElementTree.Element] = split_node.find('split:memo', XML_NAMESPACES)
        if split_memo is not None:
            new_split.memo = split_memo.text

        split_action: Optional[ElementTree.Element] = split_node.find('split:action', XML_NAMESPACES)
        if split_action is not None:
            new_split.action = split_action.text

        quantity_node = split_node.find('split:quantity', XML_NAMESPACES)
        if quantity_node is not None:
            quantity = quantity_node.text
            if quantity is not None and '/' in quantity:
                new_split.quantity_denominator = quantity.split('/')[1]

        return new_split

    @classmethod
    def create_scheduled_transaction_from_xml(cls, xml_obj: ElementTree.Element,
                                              template_account_root: Optional[Account]) -> ScheduledTransaction:
        """
        Creates a ScheduledTransaction object from the GnuCash XML.

        :param xml_obj: XML node for the scheduled transaction
        :type xml_obj: ElementTree.Element
        :param template_account_root: Root template account
        :type template_account_root: Account
        :return: ScheduledTransaction object from XML
        :rtype: ScheduledTransaction
        """
        new_obj: 'ScheduledTransaction' = ScheduledTransaction()
        sx_transaction_guid: Optional[str] = cls.read_xml_child_text(xml_obj, 'sx:id', XML_NAMESPACES)
        if sx_transaction_guid is not None and sx_transaction_guid:
            new_obj.guid = sx_transaction_guid
        new_obj.name = cls.read_xml_child_text(xml_obj, 'sx:name', XML_NAMESPACES)
        new_obj.enabled = cls.read_xml_child_boolean(xml_obj, 'sx:enabled', XML_NAMESPACES)
        new_obj.auto_create = cls.read_xml_child_boolean(xml_obj, 'sx:autoCreate', XML_NAMESPACES)
        new_obj.auto_create_notify = cls.read_xml_child_boolean(xml_obj, 'sx:autoCreateNotify', XML_NAMESPACES)
        new_obj.advance_create_days = cls.read_xml_child_int(xml_obj, 'sx:advanceCreateDays', XML_NAMESPACES)
        new_obj.advance_remind_days = cls.read_xml_child_int(xml_obj, 'sx:advanceRemindDays', XML_NAMESPACES)
        new_obj.instance_count = cls.read_xml_child_int(xml_obj, 'sx:instanceCount', XML_NAMESPACES)
        new_obj.start_date = cls.read_xml_child_date(xml_obj, 'sx:start', XML_NAMESPACES)
        new_obj.last_date = cls.read_xml_child_date(xml_obj, 'sx:last', XML_NAMESPACES)
        new_obj.end_date = cls.read_xml_child_date(xml_obj, 'sx:end', XML_NAMESPACES)

        template_account_node: Optional[ElementTree.Element] = xml_obj.find('sx:templ-acct', XML_NAMESPACES)
        if template_account_node is not None and template_account_node.text and template_account_root is not None:
            new_obj.template_account = template_account_root.get_subaccount_by_id(template_account_node.text)

        schedule_node: Optional[ElementTree.Element] = xml_obj.find('sx:schedule', XML_NAMESPACES)
        if schedule_node is not None:
            recurrence_node = schedule_node.find('gnc:recurrence', XML_NAMESPACES)
            if recurrence_node is not None:
                new_obj.recurrence_multiplier = cls.read_xml_child_int(
                    recurrence_node, 'recurrence:mult', XML_NAMESPACES
                )
                new_obj.recurrence_period = cls.read_xml_child_text(
                    recurrence_node, 'recurrence:period_type', XML_NAMESPACES)
                new_obj.recurrence_start = cls.read_xml_child_date(
                    recurrence_node, 'recurrence:start', XML_NAMESPACES)

        return new_obj

    @classmethod
    def create_budget_from_xml(cls, budget_node: ElementTree.Element) -> Budget:
        """
        Creates a Budget object from the GnuCash XML.

        :param budget_node: XML node for the budget
        :type budget_node: ElementTree.Element
        :return: Budget object from XML
        :rtype: Budget
        """
        new_obj = Budget()

        id_node: Optional[ElementTree.Element] = budget_node.find('bgt:id', XML_NAMESPACES)
        if id_node is not None and id_node.text:
            new_obj.guid = id_node.text

        name_node: Optional[ElementTree.Element] = budget_node.find('bgt:name', XML_NAMESPACES)
        if name_node is not None:
            new_obj.name = name_node.text

        description_node: Optional[ElementTree.Element] = budget_node.find('bgt:description', XML_NAMESPACES)
        if description_node is not None:
            new_obj.description = description_node.text

        period_count_node: Optional[ElementTree.Element] = budget_node.find('bgt:num-periods', XML_NAMESPACES)
        if period_count_node is not None and period_count_node.text:
            new_obj.period_count = int(period_count_node.text)

        recurrence_node: Optional[ElementTree.Element] = budget_node.find('bgt:recurrence', XML_NAMESPACES)
        if recurrence_node is not None:
            multiplier_node: Optional[ElementTree.Element] = recurrence_node.find('recurrence:mult', XML_NAMESPACES)
            if multiplier_node is not None and multiplier_node.text:
                new_obj.recurrence_multiplier = int(multiplier_node.text)

            period_type_node: Optional[ElementTree.Element] = recurrence_node.find('recurrence:period_type',
                                                                                   XML_NAMESPACES)
            if period_type_node is not None:
                new_obj.recurrence_period_type = period_type_node.text

            recurrence_start_node: Optional[ElementTree.Element] = recurrence_node.find('recurrence:start',
                                                                                        XML_NAMESPACES)
            if recurrence_start_node is not None:
                gdate_node: Optional[ElementTree.Element] = recurrence_start_node.find('gdate', XML_NAMESPACES)
                if gdate_node is not None and gdate_node.text:
                    new_obj.recurrence_start = datetime.strptime(gdate_node.text, '%Y-%m-%d')

        slots: Optional[ElementTree.Element] = budget_node.find('bgt:slots', XML_NAMESPACES)
        if slots:
            for slot in slots.findall('slot', XML_NAMESPACES):
                new_obj.slots.append(cls.create_slot_from_xml(slot))

        return new_obj

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


class GnuCashXMLWriter(BaseFileWriter):
    """Class containing the logic for saving XML files."""

    LOGGER = logging.getLogger()

    @classmethod
    def dump(cls, gnucash_file: GnuCashFile, *args: Any, target_file: str = '',  # type: ignore
             prettify_xml: bool = False, **kwargs: Any) -> None:
        """
        Writes GnuCash XML file from memory to disk.

        :param gnucash_file: File to write to disk
        :type gnucash_file: GnuCashFile
        :param target_file: Destination file to write to.
        :type target_file: str
        :param prettify_xml: Should the XML be prettified? (default false)
        :type prettify_xml: bool
        :return:
        """
        root_node: ElementTree.Element = ElementTree.Element(
            'gnc-v2', {'xmlns:' + identifier: value for identifier, value in XML_NAMESPACES.items()}
        )
        book_count_node: ElementTree.Element = ElementTree.Element('gnc:count-data', {'cd:type': 'book'})
        book_count_node.text = str(len(gnucash_file.books))
        root_node.append(book_count_node)

        for book in gnucash_file.books:
            root_node.append(cls.cast_book_as_xml(book))

        file_contents: bytes = ElementTree.tostring(root_node, encoding='utf-8', method='xml')

        # Making our resulting XML pretty
        if prettify_xml:
            file_contents = minidom.parseString(file_contents).toprettyxml(encoding='utf-8')

        cls.write_file_contents(target_file, file_contents)

    @classmethod
    def cast_book_as_xml(cls, book: Book) -> ElementTree.Element:
        """
        Returns the current book as GnuCash-compatible XML.

        :return: ElementTree.Element object
        :rtype: xml.etree.ElementTree.Element
        """
        book_node: ElementTree.Element = ElementTree.Element('gnc:book', {'version': '2.0.0'})
        book_id_node = ElementTree.SubElement(book_node, 'book:id', {'type': 'guid'})
        book_id_node.text = book.guid

        accounts_xml: Optional[List[ElementTree.Element]] = None
        if book.root_account:
            accounts_xml = cls.cast_account_as_xml(book.root_account)

        if book.slots:
            slot_node = ElementTree.SubElement(book_node, 'book:slots')
            for slot in book.slots:
                slot_node.append(cls.cast_slot_as_xml(slot))

        commodity_count_node = ElementTree.SubElement(book_node, 'gnc:count-data', {'cd:type': 'commodity'})
        commodity_count_node.text = str(len(list(filter(lambda x: x.commodity_id != 'template', book.commodities))))

        account_count_node = ElementTree.SubElement(book_node, 'gnc:count-data', {'cd:type': 'account'})
        account_count_node.text = str(len(accounts_xml) if accounts_xml else 0)

        transaction_count_node = ElementTree.SubElement(book_node, 'gnc:count-data', {'cd:type': 'transaction'})
        transaction_count_node.text = str(len(book.transactions))

        if book.scheduled_transactions:
            scheduled_transaction_node = ElementTree.SubElement(book_node, 'gnc:count-data',
                                                                {'cd:type': 'schedxaction'})
            scheduled_transaction_node.text = str(len(book.scheduled_transactions))

        if book.budgets:
            budget_node = ElementTree.SubElement(book_node, 'gnc:count-data', {'cd:type': 'budget'})
            budget_node.text = str(len(book.budgets))

        for commodity in book.commodities:
            book_node.append(cls.cast_commodity_as_xml(commodity))

        if accounts_xml:
            for account in accounts_xml:
                book_node.append(account)

        for transaction in book.transactions:
            book_node.append(cls.cast_transaction_as_xml(transaction))

        if book.template_root_account and book.template_transactions:
            template_transactions_node = ElementTree.SubElement(book_node, 'gnc:template-transactions')
            for account in cls.cast_account_as_xml(book.template_root_account):
                template_transactions_node.append(account)
            for transaction in book.template_transactions:
                template_transactions_node.append(cls.cast_transaction_as_xml(transaction))

        for scheduled_transaction in book.scheduled_transactions:
            book_node.append(cls.cast_scheduled_transaction_as_xml(scheduled_transaction))

        for budget in book.budgets:
            book_node.append(cls.cast_budget_as_xml(budget))

        return book_node

    @classmethod
    def cast_account_as_xml(cls, account: Account) -> List[ElementTree.Element]:
        """
        Returns the current account configuration (and all of its child accounts) as GnuCash-compatible XML.

        :return: Current account and children as XML
        :rtype: list[xml.etree.ElementTree.Element]
        :raises: ValueError if no commodity found.
        """
        node_and_children: List = []
        account_node: ElementTree.Element = ElementTree.Element('gnc:account', {'version': '2.0.0'})
        ElementTree.SubElement(account_node, 'act:name').text = account.name
        ElementTree.SubElement(account_node, 'act:id', {'type': 'guid'}).text = account.guid
        ElementTree.SubElement(account_node, 'act:type').text = account.type
        if account.commodity:
            account_node.append(cls.cast_commodity_as_short_xml(account.commodity, 'act:commodity'))
        else:
            parent_commodity: Optional[Commodity] = account.get_parent_commodity()
            if parent_commodity:
                account_node.append(cls.cast_commodity_as_short_xml(parent_commodity, 'act:commodity'))

        if account.commodity_scu:
            ElementTree.SubElement(account_node, 'act:commodity-scu').text = str(account.commodity_scu)

        if account.code:
            ElementTree.SubElement(account_node, 'act:code').text = str(account.code)

        if account.description:
            ElementTree.SubElement(account_node, 'act:description').text = str(account.description)

        if account.slots:
            slots_node = ElementTree.SubElement(account_node, 'act:slots')
            for slot in account.slots:
                slots_node.append(cls.cast_slot_as_xml(slot))

        if account.parent is not None:
            ElementTree.SubElement(account_node, 'act:parent', {'type': 'guid'}).text = account.parent.guid
        node_and_children.append(account_node)

        if account.children:
            for child in account.children:
                node_and_children += cls.cast_account_as_xml(child)

        return node_and_children

    @classmethod
    def cast_slot_as_xml(cls, slot: Slot) -> ElementTree.Element:
        """
        Returns the current slot as GnuCash-compatible XML.

        :return: Current slot as XML
        :rtype: xml.etree.ElementTree.Element
        """
        slot_node: ElementTree.Element = ElementTree.Element('slot')
        ElementTree.SubElement(slot_node, 'slot:key').text = slot.key

        slot_value_node = ElementTree.SubElement(slot_node, 'slot:value', {'type': slot.type})
        if slot.type == 'gdate':
            ElementTree.SubElement(slot_value_node, 'gdate').text = datetime.strftime(slot.value, '%Y-%m-%d')
        elif slot.type in ['string', 'guid', 'numeric']:
            slot_value_node.text = slot.value
        elif slot.type in ['integer', 'double']:
            slot_value_node.text = str(slot.value)
        elif isinstance(slot.value, list) and slot.value:
            for sub_slot in slot.value:
                slot_value_node.append(cls.cast_slot_as_xml(sub_slot))
        elif slot.type == 'frame':
            pass  # Empty frame element, just leave it
        else:
            raise NotImplementedError('Slot type {} is not implemented.'.format(slot.type))

        return slot_node

    @classmethod
    def cast_commodity_as_xml(cls, commodity: Commodity) -> ElementTree.Element:
        """
        Returns the current commodity as GnuCash-compatible XML.

        :return: Current commodity as XML
        :rtype: xml.etree.ElementTree.Element
        """
        commodity_node = ElementTree.Element('gnc:commodity', {'version': '2.0.0'})
        ElementTree.SubElement(commodity_node, 'cmdty:space').text = commodity.space
        ElementTree.SubElement(commodity_node, 'cmdty:id').text = commodity.commodity_id
        if commodity.get_quotes:
            ElementTree.SubElement(commodity_node, 'cmdty:get_quotes')
        if commodity.quote_source:
            ElementTree.SubElement(commodity_node, 'cmdty:quote_source').text = commodity.quote_source
        if commodity.quote_tz:
            ElementTree.SubElement(commodity_node, 'cmdty:quote_tz')
        if commodity.name:
            ElementTree.SubElement(commodity_node, 'cmdty:name').text = commodity.name
        if commodity.xcode:
            ElementTree.SubElement(commodity_node, 'cmdty:xcode').text = commodity.xcode
        if commodity.fraction:
            ElementTree.SubElement(commodity_node, 'cmdty:fraction').text = commodity.fraction

        return commodity_node

    @classmethod
    def cast_commodity_as_short_xml(cls, commodity: Commodity, node_tag: str) -> ElementTree.Element:
        """
        Returns the current commodity as GnuCash-compatible XML (short version used for accounts).

        :param commodity: Commodity being cast to short XML
        :type commodity: Commodity
        :param node_tag: XML element tag name for the commodity
        :type node_tag: str
        :return: Current commodity as short XML
        :rtype: xml.etree.ElementTree.Element
        """
        commodity_node: ElementTree.Element = ElementTree.Element(node_tag)
        ElementTree.SubElement(commodity_node, 'cmdty:space').text = commodity.space
        ElementTree.SubElement(commodity_node, 'cmdty:id').text = commodity.commodity_id
        return commodity_node

    @classmethod
    def cast_transaction_as_xml(cls, transaction: Transaction) -> ElementTree.Element:
        """
        Returns the current transaction as GnuCash-compatible XML.

        :return: Current transaction as XML
        :rtype: xml.etree.ElementTree.Element
        """
        transaction_node: ElementTree.Element = ElementTree.Element('gnc:transaction', {'version': '2.0.0'})
        ElementTree.SubElement(transaction_node, 'trn:id', {'type': 'guid'}).text = transaction.guid

        if transaction.currency:
            transaction_node.append(cls.cast_commodity_as_short_xml(transaction.currency, 'trn:currency'))

        if transaction.memo:
            ElementTree.SubElement(transaction_node, 'trn:num').text = transaction.memo

        if transaction.date_posted:
            date_posted_node = ElementTree.SubElement(transaction_node, 'trn:date-posted')
            ElementTree.SubElement(date_posted_node, 'ts:date').text = safe_iso_date_formatting(transaction.date_posted)
        if transaction.date_entered:
            date_entered_node = ElementTree.SubElement(transaction_node, 'trn:date-entered')
            ElementTree.SubElement(date_entered_node, 'ts:date').text = safe_iso_date_formatting(
                transaction.date_entered)
        ElementTree.SubElement(transaction_node, 'trn:description').text = transaction.description

        if transaction.slots:
            slots_node = ElementTree.SubElement(transaction_node, 'trn:slots')
            for slot in transaction.slots:
                slots_node.append(cls.cast_slot_as_xml(slot))

        if transaction.splits:
            splits_node = ElementTree.SubElement(transaction_node, 'trn:splits')
            for split in transaction.splits:
                splits_node.append(cls.cast_split_as_xml(split))

        return transaction_node

    @classmethod
    def cast_split_as_xml(cls, split: Split) -> ElementTree.Element:
        """
        Returns the current split as GnuCash-compatible XML.

        :return: Current split as XML
        :rtype: xml.etree.ElementTree.Element
        """
        split_node: ElementTree.Element = ElementTree.Element('trn:split')
        ElementTree.SubElement(split_node, 'split:id', {'type': 'guid'}).text = split.guid

        if split.memo:
            ElementTree.SubElement(split_node, 'split:memo').text = split.memo
        if split.action:
            ElementTree.SubElement(split_node, 'split:action').text = split.action

        ElementTree.SubElement(split_node, 'split:reconciled-state').text = split.reconciled_state
        if split.amount is not None:
            ElementTree.SubElement(split_node, 'split:value').text = str(int(split.amount * 100)) + '/100'
            ElementTree.SubElement(split_node, 'split:quantity').text = '/'.join([
                str(int(split.amount * 100)), split.quantity_denominator])
        if split.account:
            ElementTree.SubElement(split_node, 'split:account', {'type': 'guid'}).text = split.account.guid
        return split_node

    @classmethod
    def cast_scheduled_transaction_as_xml(cls, scheduled_transaction: ScheduledTransaction) -> ElementTree.Element:
        """
        Returns the current scheduled transaction as GnuCash-compatible XML.

        :return: Current scheduled transaction as XML
        :rtype: xml.etree.ElementTree.Element
        """
        xml_node: ElementTree.Element = ElementTree.Element('gnc:schedxaction', attrib={'version': '2.0.0'})
        if scheduled_transaction.guid:
            ElementTree.SubElement(xml_node, 'sx:id', attrib={'type': 'guid'}).text = scheduled_transaction.guid
        if scheduled_transaction.name:
            ElementTree.SubElement(xml_node, 'sx:name').text = scheduled_transaction.name
        ElementTree.SubElement(xml_node, 'sx:enabled').text = 'y' if scheduled_transaction.enabled else 'n'
        ElementTree.SubElement(xml_node, 'sx:autoCreate').text = 'y' if scheduled_transaction.auto_create else 'n'
        ElementTree.SubElement(xml_node, 'sx:autoCreateNotify').text = 'y' if scheduled_transaction.auto_create_notify \
            else 'n'
        if scheduled_transaction.advance_create_days is not None:
            ElementTree.SubElement(xml_node, 'sx:advanceCreateDays').text = \
                str(scheduled_transaction.advance_create_days)
        if scheduled_transaction.advance_remind_days is not None:
            ElementTree.SubElement(xml_node, 'sx:advanceRemindDays').text = \
                str(scheduled_transaction.advance_remind_days)
        if scheduled_transaction.instance_count is not None:
            ElementTree.SubElement(xml_node, 'sx:instanceCount').text = str(scheduled_transaction.instance_count)
        if scheduled_transaction.start_date:
            start_node = ElementTree.SubElement(xml_node, 'sx:start')
            ElementTree.SubElement(start_node, 'gdate').text = scheduled_transaction.start_date.strftime('%Y-%m-%d')
        if scheduled_transaction.last_date:
            last_node = ElementTree.SubElement(xml_node, 'sx:last')
            ElementTree.SubElement(last_node, 'gdate').text = scheduled_transaction.last_date.strftime('%Y-%m-%d')
        if scheduled_transaction.end_date:
            end_node = ElementTree.SubElement(xml_node, 'sx:end')
            ElementTree.SubElement(end_node, 'gdate').text = scheduled_transaction.end_date.strftime('%Y-%m-%d')
        if scheduled_transaction.template_account:
            ElementTree.SubElement(xml_node, 'sx:templ-acct', attrib={'type': 'guid'}).text = \
                scheduled_transaction.template_account.guid
        if scheduled_transaction.recurrence_multiplier is not None \
                or scheduled_transaction.recurrence_period is not None \
                or scheduled_transaction.recurrence_start is not None:
            schedule_node = ElementTree.SubElement(xml_node, 'sx:schedule')
            recurrence_node = ElementTree.SubElement(schedule_node, 'gnc:recurrence', attrib={'version': '1.0.0'})
            if scheduled_transaction.recurrence_multiplier:
                ElementTree.SubElement(recurrence_node, 'recurrence:mult').text = \
                    str(scheduled_transaction.recurrence_multiplier)
            if scheduled_transaction.recurrence_period:
                ElementTree.SubElement(recurrence_node, 'recurrence:period_type').text = \
                    scheduled_transaction.recurrence_period
            if scheduled_transaction.recurrence_start:
                start_node = ElementTree.SubElement(recurrence_node, 'recurrence:start')
                ElementTree.SubElement(start_node, 'gdate').text = \
                    scheduled_transaction.recurrence_start.strftime('%Y-%m-%d')
        return xml_node

    @classmethod
    def cast_budget_as_xml(cls, budget: Budget) -> ElementTree.Element:
        """
        Returns the current budget as GnuCash-compatible XML.

        :return: Current budget as XML
        :rtype: xml.etree.ElementTree.Element
        """
        budget_node: ElementTree.Element = ElementTree.Element('gnc:budget', attrib={'version': '2.0.0'})
        ElementTree.SubElement(budget_node, 'bgt:id', {'type': 'guid'}).text = budget.guid
        ElementTree.SubElement(budget_node, 'bgt:name').text = budget.name
        ElementTree.SubElement(budget_node, 'bgt:description').text = budget.description

        if budget.period_count is not None:
            ElementTree.SubElement(budget_node, 'bgt:num-periods').text = str(budget.period_count)

        if budget.recurrence_multiplier is not None or budget.recurrence_period_type is not None or \
                budget.recurrence_start is not None:
            recurrence_node = ElementTree.SubElement(budget_node, 'bgt:recurrence', attrib={'version': '1.0.0'})
            if budget.recurrence_multiplier is not None:
                ElementTree.SubElement(recurrence_node, 'recurrence:mult').text = str(budget.recurrence_multiplier)
            if budget.recurrence_period_type is not None:
                ElementTree.SubElement(recurrence_node, 'recurrence:period_type').text = budget.recurrence_period_type
            if budget.recurrence_start is not None:
                start_node = ElementTree.SubElement(recurrence_node, 'recurrence:start')
                ElementTree.SubElement(start_node, 'gdate').text = budget.recurrence_start.strftime('%Y-%m-%d')

        if budget.slots:
            slots_node = ElementTree.SubElement(budget_node, 'bgt:slots')
            for slot in budget.slots:
                slots_node.append(cls.cast_slot_as_xml(slot))

        return budget_node

    @classmethod
    def write_file_contents(cls, target_file: str, file_contents: bytes) -> None:
        """
        Writes the file contents to the target file.

        :param target_file: File that contents will be written to.
        :type target_file: str
        :param file_contents: Contents to be written to the file.
        :type file_contents: bytes
        """
        with open(target_file, 'wb') as target_file_handle:
            target_file_handle.write(file_contents)


class XMLFileFormat(GnuCashXMLReader, GnuCashXMLWriter, BaseFileFormat):  # type: ignore
    """Class containing the logic for loading and saving XML files."""


class GZipXMLFileFormat(XMLFileFormat):
    """Class containing the logic for loading and saving XML files with GZip compression."""

    @classmethod
    def get_xml_root(cls, source_path: pathlib.Path) -> ElementTree.Element:
        """
        Retrieves the XML root element from a GZipped XML file.

        :param source_path: Path to GZipped XML File.
        :type source_path: str
        :return: XML root element
        :rtype: ElementTree.Element
        """
        with gzip.open(source_path, 'rb') as gzipped_file:
            contents = gzipped_file.read().decode('utf-8')
        return ElementTree.fromstring(contents)

    @classmethod
    def write_file_contents(cls, target_file: str, file_contents: bytes) -> None:
        """
        Writes the specified contents to the target file, with a level 9 GZip compression.

        :param target_file: Target GZip file to write to.
        :type target_file: str
        :param file_contents: Contents to write to the GZip file
        :type file_contents: bytes
        """
        with gzip.open(target_file, 'wb', compresslevel=9) as gzip_file:
            gzip_file.write(file_contents)
