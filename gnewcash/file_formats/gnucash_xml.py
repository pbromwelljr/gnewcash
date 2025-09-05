"""
Module containing the logic for loading and saving XML files.

.. module:: xml
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""
import gzip
import logging
import pathlib
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from xml.dom import minidom
from xml.etree import ElementTree

from gnewcash.account import Account
from gnewcash.commodity import Commodity
from gnewcash.file_formats.base import BaseFileFormat, BaseFileReader, BaseFileWriter
from gnewcash.gnucash_file import Book, Budget, GnuCashFile, RecurrencePeriodType
from gnewcash.slot import Slot
from gnewcash.transaction import ScheduledTransaction, SortingMethod, Split, Transaction, TransactionManager
from gnewcash.utils import safe_iso_date_formatting, safe_iso_date_parsing

XML_NAMESPACES: dict[str, str] = {
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


@dataclass
class ElementTag:
    """Class to hold tag namespace and actual tag name info."""

    namespace: str = field()
    tag: str = field()

    tag_format: re.Pattern = re.compile(r'^(\{[^}]+})?(.*)$')

    @classmethod
    def parse(cls, tag_name: str) -> 'ElementTag':
        """Parses ElementTree's full tag name into namespace and actual tag name."""
        match = cls.tag_format.match(tag_name)
        if match is None:
            return ElementTag(namespace='', tag='')

        return ElementTag(namespace=match.group(1),
                          tag=match.group(2))


class MalformedXMLElementException(Exception):
    """Custom error class for when a malformed XML element is detected."""


class GnuCashXMLReader(BaseFileReader):
    """Class containing the logic for loading XML files."""

    LOGGER = logging.getLogger()

    @classmethod
    def load(
            cls,
            *args: Any,
            source_file: Optional[pathlib.Path] = None,
            sort_transactions: bool = True,
            sort_method: Optional[SortingMethod] = None,
            **kwargs: Any
    ) -> GnuCashFile:
        """
        Loads a GnuCash XML file from disk to memory.

        :param source_file: File to load from disk
        :type source_file: str
        :param sort_transactions: Should transactions be sorted by date posted
        :type sort_transactions: bool
        :param sort_method: SortMethod class instance that determines the sort order for the transactions
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

        cls._build_file(built_file, source_file, sort_transactions, sort_method)

        return built_file

    @classmethod
    def _build_file(
            cls,
            built_file: GnuCashFile,
            source_file: pathlib.Path,
            sort_transactions: bool = True,
            sort_method: Optional[SortingMethod] = None
    ) -> None:
        current_iter: Iterator = cls.__get_xml_root(source_file)
        for event, elem in current_iter:
            if event == 'start' and elem.tag == '{http://www.gnucash.org/XML/gnc}book':
                new_book = cls.create_book_from_xml(current_iter,
                                                    sort_transactions=sort_transactions,
                                                    sort_method=sort_method)
                built_file.books.append(new_book)

    @classmethod
    def __get_xml_root(cls, source_path: pathlib.Path) -> Iterator:
        """
        Retrieves an iterator to all the XML elements.

        :param source_path: Path to XML document
        :type source_path: pathlib.Path
        :return: Iterator to all XML elements
        :rtype: Iterator
        """
        return ElementTree.iterparse(source=str(source_path), events=('start', 'end'))

    @classmethod
    def create_book_from_xml(
            cls,
            current_iter: Iterator,
            sort_transactions: bool = True,
            sort_method: Optional[SortingMethod] = None,
    ) -> Book:
        """
        Creates a Book object from the GnuCash XML.

        :param current_iter: Current iterator to XML elements
        :type current_iter: Iterator
        :param sort_transactions: Flag for if transactions should be sorted by date_posted when reading from XML
        :type sort_transactions: bool
        :param sort_method: SortingMethod class instance that determines the sort order for the transactions.
        :type sort_method: SortingMethod
        :return: Book object from XML
        :rtype: Book
        """
        new_book = Book()
        account_objects: list[Account] = []
        transaction_manager: TransactionManager = TransactionManager(disable_sort=not sort_transactions,
                                                                     sort_method=sort_method)
        for event, elem in current_iter:
            parsed_tag = ElementTag.parse(elem.tag)
            if event == 'end' and parsed_tag.tag == 'book':
                break

            if parsed_tag.tag == 'id' and (elem.text or '').strip():
                new_book.guid = elem.text.strip()
            elif event == 'start' and parsed_tag.tag == 'slots':
                new_book.slots = cls.__collect_slots(current_iter, elem.tag)
            elif event == 'start' and parsed_tag.tag == 'commodity':
                new_book.commodities.append(cls.create_commodity_from_xml(current_iter))
            elif event == 'start' and parsed_tag.tag == 'account':
                account_objects.append(cls.create_account_from_xml(current_iter, account_objects))
            elif event == 'start' and parsed_tag.tag == 'transaction':
                transaction_manager.add(cls.create_transaction_from_xml(current_iter, account_objects))
            elif event == 'start' and parsed_tag.tag == 'template-transactions':
                template_accounts: list[Account] = []
                template_transactions: list[Transaction] = []
                for templ_trans_event, templ_trans_elem in current_iter:
                    if templ_trans_event == 'end' and templ_trans_elem.tag == elem.tag:
                        break
                    templ_trans_tag = ElementTag.parse(templ_trans_elem.tag)
                    if templ_trans_event == 'start' and templ_trans_tag.tag == 'account':
                        template_accounts.append(cls.create_account_from_xml(current_iter, template_accounts))
                    elif templ_trans_event == 'start' and templ_trans_tag.tag == 'transaction':
                        template_transactions.append(cls.create_transaction_from_xml(current_iter, template_accounts))
                new_book.template_transactions = template_transactions
                template_root_account: Optional[Account] = next((x for x in template_accounts if x.type == 'ROOT'),
                                                                None)
                if template_root_account:
                    new_book.template_root_account = template_root_account
            elif event == 'start' and parsed_tag.tag == 'schedxaction':
                new_book.scheduled_transactions.append(
                    cls.create_scheduled_transaction_from_xml(current_iter, new_book.template_root_account)
                )
            elif event == 'start' and parsed_tag.tag == 'budget':
                new_book.budgets.append(cls.create_budget_from_xml(current_iter))

        new_book.root_account = next(x for x in account_objects if x.type == 'ROOT')
        new_book.transactions = transaction_manager

        return new_book

    @classmethod
    def __collect_slots(cls, current_iter: Iterator, slots_tag_name: str) -> list[Slot]:
        slots: list[Slot] = []
        for slot_event, slot_elem in current_iter:
            if slot_event == 'end' and slot_elem.tag == slots_tag_name:
                break
            if slot_event == 'start' and slot_elem.tag == 'slot':
                slots.append(cls.create_slot_from_xml(current_iter))
        return slots

    @classmethod
    def create_slot_from_xml(cls, current_iter: Iterator) -> Slot:
        """
        Creates a Slot object from the GnuCash XML.

        :param current_iter: Iterator for XML elements
        :type current_iter: Iterator
        :return: Slot object from XML
        :rtype: Slot
        """
        key: Optional[str] = None
        slot_type: Optional[str] = None
        value: Optional[Any] = None
        for event, elem in current_iter:
            parsed_tag = ElementTag.parse(elem.tag)
            if event == 'end' and elem.tag == 'slot':
                break
            if parsed_tag.tag == 'key' and (elem.text or '').strip():
                key = elem.text.strip()
            elif parsed_tag.tag == 'value':
                slot_type = elem.attrib['type']
                if slot_type in ('string', 'guid', 'numeric'):
                    # NOTE: Separate "if" so we don't get NotImplementedError on empty string values
                    if (elem.text or '').strip():
                        value = elem.text.strip()
                elif slot_type == 'integer':
                    # NOTE: Separate "if" so we don't get NotImplementedError on empty string values
                    if (elem.text or '').strip():
                        value = int(elem.text.strip())
                elif slot_type == 'double':
                    # NOTE: Separate "if" so we don't get NotImplementedError on empty string values
                    if (elem.text or '').strip():
                        value = Decimal(elem.text.strip())
                elif slot_type == 'gdate':
                    value = cls.__extract_gdate_value(current_iter, elem.tag)
                elif slot_type == 'frame':
                    value = cls.__collect_slots(current_iter, elem.tag)
                else:
                    raise NotImplementedError(f'Slot type {slot_type} is not implemented.')

        if key is None or slot_type is None:
            raise NotImplementedError('Malformed slot.')

        return Slot(key, value, slot_type)

    @classmethod
    def __extract_gdate_value(cls, current_iter: Iterator, parent_tag_name: str) -> Optional[datetime]:
        value: Optional[datetime] = None
        for event, element in current_iter:
            if event == 'end' and element.tag == parent_tag_name:
                break
            if element.tag == 'gdate' and (element.text or '').strip():
                value = datetime.strptime(element.text.strip(), '%Y-%m-%d')
        return value

    @classmethod
    def create_commodity_from_xml(cls, current_iter: Iterator) -> Commodity:
        """
        Creates a Commodity object from the GnuCash XML.

        :param current_iter: Iterator for XML elements
        :type current_iter: Iterator
        :return: Commodity object from XML
        :rtype: Commodity
        """
        commodity_id: Optional[str] = None
        space: Optional[str] = None
        get_quotes: Optional[bool] = None
        quote_source: Optional[str] = None
        quote_tz: Optional[bool] = None
        name: Optional[str] = None
        xcode: Optional[str] = None
        fraction: Optional[str] = None
        for event, elem in current_iter:
            parsed_tag = ElementTag.parse(elem.tag)
            if event == 'end' and parsed_tag.tag == 'commodity':
                break

            if parsed_tag.tag == 'space' and (elem.text or '').strip():
                space = elem.text.strip()
            elif parsed_tag.tag == 'id' and (elem.text or '').strip():
                commodity_id = elem.text.strip()
            elif parsed_tag.tag == 'get_quotes':
                get_quotes = True
            elif parsed_tag.tag == 'quote_source' and (elem.text or '').strip():
                quote_source = elem.text.strip()
            elif parsed_tag.tag == 'quote_tz':
                quote_tz = True
            elif parsed_tag.tag == 'name' and (elem.text or '').strip():
                name = elem.text.strip()
            elif parsed_tag.tag == 'xcode' and (elem.text or '').strip():
                xcode = elem.text.strip()
            elif parsed_tag.tag == 'fraction' and (elem.text or '').strip():
                fraction = elem.text.strip()

        if commodity_id is None or space is None:
            raise MalformedXMLElementException('Malformed commodity.')

        new_commodity: Commodity = Commodity(commodity_id, space)
        if get_quotes is not None:
            new_commodity.get_quotes = get_quotes
        new_commodity.quote_source = quote_source
        if quote_tz is not None:
            new_commodity.quote_tz = quote_tz
        new_commodity.name = name
        new_commodity.xcode = xcode
        new_commodity.fraction = fraction

        return new_commodity

    @classmethod
    def create_account_from_xml(cls, current_iter: Iterator, account_objects: list[Account]) -> Account:
        """
        Creates an Account object from the GnuCash XML.

        :param current_iter: Iterator for XML elements
        :type current_iter: Iterator
        :param account_objects: Account objects already created from XML (used for assigning parent account)
        :type account_objects: list[Account]
        :return: Account object from XML
        :rtype: Account
        """
        account_object: Account = Account()
        for event, elem in current_iter:
            parsed_tag = ElementTag.parse(elem.tag)
            if event == 'end' and parsed_tag.tag == 'account':
                break

            if parsed_tag.tag == 'id' and (elem.text or '').strip():
                account_object.guid = elem.text.strip()
            elif parsed_tag.tag == 'name' and (elem.text or '').strip():
                account_object.name = elem.text.strip()
            elif parsed_tag.tag == 'type' and (elem.text or '').strip():
                account_object.type = elem.text.strip()
            elif parsed_tag.tag == 'commodity':
                account_object.commodity = cls.create_commodity_from_xml(current_iter)
            elif parsed_tag.tag == 'commodity-scu' and (elem.text or '').strip():
                account_object.commodity_scu = elem.text.strip()
            elif parsed_tag.tag == 'slots':
                account_object.slots = cls.__collect_slots(current_iter, elem.tag)
            elif parsed_tag.tag == 'code' and (elem.text or '').strip():
                account_object.code = elem.text.strip()
            elif parsed_tag.tag == 'description' and (elem.text or '').strip():
                account_object.description = elem.text.strip()
            elif parsed_tag.tag == 'parent' and (elem.text or '').strip():
                account_object.parent = next(x for x in account_objects if x.guid == elem.text.strip())

        return account_object

    @classmethod
    def create_transaction_from_xml(cls, current_iter: Iterator,
                                    account_objects: list[Account]) -> Transaction:
        """
        Creates a Transaction object from the GnuCash XML.

        :param current_iter: Iterator for XML elements
        :type current_iter: Iterator
        :param account_objects: Account objects already created from XML (used for assigning accounts)
        :type account_objects: list[Account]
        :return: Transaction object from XML
        :rtype: Transaction
        """
        transaction: Transaction = Transaction()
        for event, elem in current_iter:
            parsed_tag = ElementTag.parse(elem.tag)
            if event == 'end' and parsed_tag.tag == 'transaction':
                break

            if parsed_tag.tag == 'id' and (elem.text or '').strip():
                transaction.guid = elem.text.strip()
            elif parsed_tag.tag == 'date-entered':
                for date_entered_event, date_entered_elem in current_iter:
                    if date_entered_event == 'end' and date_entered_elem.tag == elem.tag:
                        break
                    if (date_entered_elem.tag == '{http://www.gnucash.org/XML/ts}date' and
                            (date_entered_elem.text or '').strip()):
                        transaction.date_entered = safe_iso_date_parsing(date_entered_elem.text.strip())
            elif parsed_tag.tag == 'date-posted':
                for date_posted_event, date_posted_elem in current_iter:
                    if date_posted_event == 'end' and date_posted_elem.tag == elem.tag:
                        break
                    if (date_posted_elem.tag == '{http://www.gnucash.org/XML/ts}date' and
                            (date_posted_elem.text or '').strip()):
                        transaction.date_posted = safe_iso_date_parsing(date_posted_elem.text.strip())
            elif parsed_tag.tag == 'description' and (elem.text or '').strip():
                transaction.description = elem.text.strip()
            elif parsed_tag.tag == 'num' and (elem.text or '').strip():
                transaction.memo = elem.text.strip()
            elif parsed_tag.tag == 'currency':
                currency_id: Optional[str] = None
                currency_space: Optional[str] = None
                for currency_event, currency_elem in current_iter:
                    if currency_event == 'end' and currency_elem.tag == elem.tag:
                        break
                    parsed_currency_tag = ElementTag.parse(currency_elem.tag)
                    if parsed_currency_tag.tag == 'id' and currency_id is None and (currency_elem.text or '').strip():
                        currency_id = currency_elem.text.strip()
                    elif (parsed_currency_tag.tag == 'space' and currency_space is None and
                          (currency_elem.text or '').strip()):
                        currency_space = currency_elem.text.strip()
                if currency_id is None or currency_space is None:
                    raise MalformedXMLElementException('Malformed currency')
                transaction.currency = Commodity(currency_id, currency_space)
            elif parsed_tag.tag == 'slots':
                transaction.slots = cls.__collect_slots(current_iter, elem.tag)
            elif parsed_tag.tag == 'splits':
                for split_event, split_elem in current_iter:
                    if split_event == 'end' and split_elem.tag == elem.tag:
                        break
                    if split_event == 'start' and split_elem.tag == '{http://www.gnucash.org/XML/trn}split':
                        transaction.splits.append(cls.create_split_from_xml(current_iter, account_objects))

        return transaction

    @classmethod
    def create_split_from_xml(cls, current_iter: Iterator, account_objects: list[Account]) -> Split:
        """
        Creates an Split object from the GnuCash XML.

        :param current_iter: Iterator for XML elements
        :type current_iter: Iterator
        :param account_objects: Account objects already created from XML (used for assigning parent account)
        :type account_objects: list[Account]
        :return: Split object from XML
        :rtype: Split
        """
        split_id: Optional[str] = None
        reconciled_state: Optional[str] = None
        value: Optional[str] = None
        quantity: Optional[str] = None
        account_id: Optional[str] = None
        memo: Optional[str] = None
        action: Optional[str] = None
        slots: list[Slot] = []
        for event, elem in current_iter:
            parsed_tag = ElementTag.parse(elem.tag)
            if event == 'end' and parsed_tag.tag == 'split':
                break
            if parsed_tag.tag == 'id' and (elem.text or '').strip():
                split_id = elem.text
            elif parsed_tag.tag == 'reconciled-state' and (elem.text or '').strip():
                reconciled_state = elem.text
            elif parsed_tag.tag == 'value' and (elem.text or '').strip():
                value = elem.text
            elif parsed_tag.tag == 'quantity' and (elem.text or '').strip():
                quantity = elem.text
            elif parsed_tag.tag == 'account' and (elem.text or '').strip():
                account_id = elem.text
            elif parsed_tag.tag == 'memo' and (elem.text or '').strip():
                memo = elem.text
            elif parsed_tag.tag == 'action' and (elem.text or '').strip():
                action = elem.text
            elif event == 'start' and parsed_tag.tag == 'slots':
                slots = cls.__collect_slots(current_iter, elem.tag)

        if value is None or reconciled_state is None:
            raise MalformedXMLElementException('Malformed split')

        new_split = Split(
            guid=split_id,
            account=next(x for x in account_objects if x.guid == account_id),
            amount=Decimal(value[:value.find('/')]) / Decimal(value[value.find('/') + 1:]),
            reconciled_state=reconciled_state
        )

        if memo:
            new_split.memo = memo
        if action:
            new_split.action = action
        if quantity:
            if '/' in quantity:
                new_split.quantity_num = int(quantity.split('/')[0])
                new_split.quantity_denominator = quantity.split('/')[1]
            else:
                new_split.quantity_num = int(quantity) * 100
                new_split.quantity_denominator = '100'
        if slots:
            new_split.slots = slots
        return new_split

    @classmethod
    def create_scheduled_transaction_from_xml(
        cls,
        current_iter: Iterator,
        template_account_root: Optional[Account]
    ) -> ScheduledTransaction:
        """
        Creates a ScheduledTransaction object from the GnuCash XML.

        :param current_iter: Iterator for XML elements
        :type current_iter: Iterator
        :param template_account_root: Root template account
        :type template_account_root: Account
        :return: ScheduledTransaction object from XML
        :rtype: ScheduledTransaction
        """
        new_obj: ScheduledTransaction = ScheduledTransaction()
        for event, elem in current_iter:
            parsed_tag = ElementTag.parse(elem.tag)
            if event == 'end' and parsed_tag.tag == 'schedxaction':
                break
            if parsed_tag.tag == 'id' and (elem.text or '').strip():
                new_obj.guid = elem.text.strip()
            elif parsed_tag.tag == 'name' and (elem.text or '').strip():
                new_obj.name = elem.text.strip()
            elif parsed_tag.tag == 'enabled' and (elem.text or '').strip():
                new_obj.enabled = elem.text.strip() == 'y'
            elif parsed_tag.tag == 'autoCreate' and (elem.text or '').strip():
                new_obj.auto_create = elem.text.strip() == 'y'
            elif parsed_tag.tag == 'autoCreateNotify' and (elem.text or '').strip():
                new_obj.auto_create_notify = elem.text.strip() == 'y'
            elif parsed_tag.tag == 'advanceCreateDays' and (elem.text or '').strip():
                new_obj.advance_create_days = int(elem.text.strip())
            elif parsed_tag.tag == 'advanceRemindDays' and (elem.text or '').strip():
                new_obj.advance_remind_days = int(elem.text.strip())
            elif parsed_tag.tag == 'instanceCount' and (elem.text or '').strip():
                new_obj.instance_count = int(elem.text.strip())
            elif event == 'start' and parsed_tag.tag == 'start':
                new_obj.start_date = cls.__extract_gdate_value(current_iter, elem.tag)
            elif event == 'start' and parsed_tag.tag == 'last':
                new_obj.last_date = cls.__extract_gdate_value(current_iter, elem.tag)
            elif event == 'start' and parsed_tag.tag == 'end':
                new_obj.end_date = cls.__extract_gdate_value(current_iter, elem.tag)
            elif parsed_tag.tag == 'templ-acct' and (elem.text or '').strip() and template_account_root is not None:
                new_obj.template_account = template_account_root.get_subaccount_by_id(elem.text.strip())
            elif event == 'start' and parsed_tag.tag == 'schedule':
                for schedule_event, schedule_elem in current_iter:
                    if schedule_event == 'end' and schedule_elem.tag == elem.tag:
                        break
                    schedule_tag = ElementTag.parse(schedule_elem.tag)
                    if schedule_tag.tag == 'mult' and (schedule_elem.text or '').strip():
                        new_obj.recurrence_multiplier = int(schedule_elem.text.strip())
                    elif schedule_tag.tag == 'period_type' and (schedule_elem.text or '').strip():
                        new_obj.recurrence_period = schedule_elem.text.strip()
                    elif schedule_tag.tag == 'start':
                        new_obj.recurrence_start = cls.__extract_gdate_value(current_iter, schedule_elem.tag)
        return new_obj

    @classmethod
    def create_budget_from_xml(cls, current_iter: Iterator) -> Budget:
        """
        Creates a Budget object from the GnuCash XML.

        :param current_iter: Iterator for XML elements
        :type current_iter: Iterator
        :return: Budget object from XML
        :rtype: Budget
        """
        new_obj = Budget()

        for event, elem in current_iter:
            parsed_tag = ElementTag.parse(elem.tag)
            if event == 'end' and parsed_tag.tag == 'budget':
                break

            if parsed_tag.tag == 'id' and (elem.text or '').strip():
                new_obj.guid = elem.text.strip()
            elif parsed_tag.tag == 'name' and (elem.text or '').strip():
                new_obj.name = elem.text.strip()
            elif parsed_tag.tag == 'description' and (elem.text or '').strip():
                new_obj.description = elem.text.strip()
            elif parsed_tag.tag == 'num-periods' and (elem.text or '').strip():
                new_obj.period_count = int(elem.text.strip())
            elif event == 'start' and parsed_tag.tag == 'recurrence':
                for recurrence_event, recurrence_elem in current_iter:
                    recurrence_tag = ElementTag.parse(recurrence_elem.tag)
                    if recurrence_event == 'end' and recurrence_elem.tag == elem.tag:
                        break
                    if recurrence_tag.tag == 'mult' and (recurrence_elem.text or '').strip():
                        new_obj.recurrence_multiplier = int(recurrence_elem.text.strip())
                    elif recurrence_tag.tag == 'period_type' and (recurrence_elem.text or '').strip():
                        new_obj.recurrence_period_type = RecurrencePeriodType(recurrence_elem.text.strip())
                    elif recurrence_tag.tag == 'start':
                        new_obj.recurrence_start = cls.__extract_gdate_value(current_iter, recurrence_elem.tag)
            elif event == 'start' and parsed_tag.tag == 'slots':
                new_obj.slots = cls.__collect_slots(current_iter, elem.tag)

        return new_obj


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

        accounts_xml: Optional[list[ElementTree.Element]] = None
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
    def cast_account_as_xml(cls, account: Account) -> list[ElementTree.Element]:
        """
        Returns the current account configuration (and all of its child accounts) as GnuCash-compatible XML.

        :return: Current account and children as XML
        :rtype: list[xml.etree.ElementTree.Element]
        :raises: ValueError if no commodity found.
        """
        node_and_children: list = []
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
        ElementTree.SubElement(slot_node, 'slot:key').text = str(slot.key)

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
            raise NotImplementedError(f'Slot type {slot.type} is not implemented.')

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

        if split.slots:
            slots_node = ElementTree.SubElement(split_node, 'split:slots')
            for slot in split.slots:
                slots_node.append(cls.cast_slot_as_xml(slot))

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
                ElementTree.SubElement(
                    recurrence_node, 'recurrence:period_type'
                ).text = budget.recurrence_period_type.value
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
    def _build_file(
            cls,
            built_file: GnuCashFile,
            source_file: pathlib.Path,
            sort_transactions: bool = True,
            sort_method: Optional[SortingMethod] = None
    ) -> None:
        with gzip.GzipFile(source_file, 'r') as gzipped_file:
            current_iter: Iterator = cls.__get_xml_root(gzipped_file)
            for event, elem in current_iter:
                if event == 'start' and elem.tag == '{http://www.gnucash.org/XML/gnc}book':
                    new_book = cls.create_book_from_xml(current_iter,
                                                        sort_transactions=sort_transactions,
                                                        sort_method=sort_method)
                    built_file.books.append(new_book)

    @classmethod
    def __get_xml_root(cls, gzipped_file: gzip.GzipFile) -> Iterator:
        """
        Retrieves the XML root element from a GZipped XML file.

        :param source_path: Path to GZipped XML File.
        :type source_path: str
        :return: Iterator to all XML elements
        :rtype: Iterator
        """
        return ElementTree.iterparse(gzipped_file, events=('start', 'end'))

    @classmethod
    def write_file_contents(cls, target_file: str, file_contents: bytes) -> None:
        """
        Writes the specified contents to the target file, with a level 9 GZip compression.

        :param target_file: Target GZip file to write to.
        :type target_file: str
        :param file_contents: Contents to write to the GZip file
        :type file_contents: bytes
        """
        with gzip.GzipFile(target_file, 'w', compresslevel=9) as gzip_file:
            gzip_file.write(file_contents)
