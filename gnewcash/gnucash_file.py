"""
.. module:: gnucash_file
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""

from datetime import datetime
import gzip
import os.path
from logging import getLogger
from xml.etree import ElementTree
from xml.dom import minidom

from gnewcash.guid_object import GuidObject
from gnewcash.transaction import Transaction, TransactionManager, ScheduledTransaction
from gnewcash.account import Account
from gnewcash.commodity import Commodity
from gnewcash.slot import Slot


class GnuCashFile:
    """
    Class representing a GnuCash file on disk.
    """
    namespace_data = {
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

    def __init__(self, books=None):
        if not books:
            books = []
        self.books = books
        self.file_name = None

    def __str__(self):
        as_string = ''
        if self.file_name:
            as_string = self.file_name + ', '
        as_string += '{} books'.format(len(self.books))
        return as_string

    def __repr__(self):
        return str(self)

    @classmethod
    def read_file(cls, source_file, sort_transactions=True):
        """
        Reads the specified .gnucash file and loads it into memory

        :param source_file: Full or relative path to the .gnucash file.
        :type source_file: str
        :param sort_transactions: Flag for if transactions should be sorted by date_posted when reading from XML
        :type sort_transactions: bool
        :return: New GnuCashFile object
        :rtype: GnuCashFile
        """
        logger = getLogger()
        built_file = cls()
        built_file.file_name = source_file
        if os.path.exists(source_file):
            try:
                xml_tree = ElementTree.parse(source=source_file)
                root = xml_tree.getroot()
            except ElementTree.ParseError:
                with gzip.open(source_file, 'rb') as gzipped_file:
                    contents = gzipped_file.read().decode('utf-8')
                xml_tree = ElementTree.fromstring(contents)
                root = xml_tree
            namespaces = cls.namespace_data

            books = root.findall('gnc:book', namespaces)
            for book in books:
                new_book = Book.from_xml(book, namespaces, sort_transactions=sort_transactions)
                built_file.books.append(new_book)
        else:
            logger.warning('Could not find %s', source_file)
        return built_file

    def build_file(self, target_file, prettify_xml=False, use_gzip=False):
        """
        Writes the contents of the GnuCashFile object out to a .gnucash file on disk

        :param target_file: Full or relative path to the target file
        :type target_file: str
        :param prettify_xml: Prettifies XML before writing to disk. Default False.
        :type prettify_xml: bool
        :param use_gzip: Use GZip compression when writing file to disk. Default False.
        :type use_gzip: bool
        """
        namespace_info = self.namespace_data
        root_node = ElementTree.Element('gnc-v2', {'xmlns:' + identifier: value
                                                   for identifier, value in namespace_info.items()})
        book_count_node = ElementTree.Element('gnc:count-data', {'cd:type': 'book'})
        book_count_node.text = str(len(self.books))
        root_node.append(book_count_node)

        for book in self.books:
            root_node.append(book.as_xml)

        file_contents = ElementTree.tostring(root_node, encoding='utf-8', method='xml')

        # Making our resulting XML pretty
        if prettify_xml:
            file_contents = minidom.parseString(file_contents).toprettyxml(encoding='utf-8')

        if use_gzip:
            with gzip.open(target_file, 'wb', compresslevel=9) as gzip_file:
                gzip_file.write(file_contents)
        else:
            with open(target_file, 'wb') as target_file_handle:
                target_file_handle.write(file_contents)


class Book(GuidObject):
    """
    Represents a Book in GnuCash
    """
    def __init__(self, root_account=None, transactions=None, commodities=None, slots=None,
                 template_root_account=None, template_transactions=None, scheduled_transactions=None,
                 budgets=None):
        super(Book, self).__init__()
        self.root_account = root_account
        self.transactions = transactions or TransactionManager()
        self.commodities = commodities or []
        self.slots = slots or []
        self.template_root_account = template_root_account
        self.template_transactions = template_transactions or []
        self.scheduled_transactions = scheduled_transactions or []
        self.budgets = budgets or []

    @property
    def as_xml(self):
        """
        Returns the current book as GnuCash-compatible XML

        :return: ElementTree.Element object
        :rtype: xml.etree.ElementTree.Element
        """
        book_node = ElementTree.Element('gnc:book', {'version': '2.0.0'})
        book_id_node = ElementTree.SubElement(book_node, 'book:id', {'type': 'guid'})
        book_id_node.text = self.guid

        accounts_xml = self.root_account.as_xml

        if self.slots:
            slot_node = ElementTree.SubElement(book_node, 'book:slots')
            for slot in self.slots:
                slot_node.append(slot.as_xml)

        commodity_count_node = ElementTree.SubElement(book_node, 'gnc:count-data', {'cd:type': 'commodity'})
        commodity_count_node.text = str(len(list(filter(lambda x: x.commodity_id != 'template', self.commodities))))

        account_count_node = ElementTree.SubElement(book_node, 'gnc:count-data', {'cd:type': 'account'})
        account_count_node.text = str(len(accounts_xml))

        transaction_count_node = ElementTree.SubElement(book_node, 'gnc:count-data', {'cd:type': 'transaction'})
        transaction_count_node.text = str(len(self.transactions))

        if self.scheduled_transactions:
            scheduled_transaction_node = ElementTree.SubElement(book_node, 'gnc:count-data',
                                                                {'cd:type': 'schedxaction'})
            scheduled_transaction_node.text = str(len(self.scheduled_transactions))

        if self.budgets:
            budget_node = ElementTree.SubElement(book_node, 'gnc:count-data', {'cd:type': 'budget'})
            budget_node.text = str(len(self.budgets))

        for commodity in self.commodities:
            book_node.append(commodity.as_xml)

        for account in accounts_xml:
            book_node.append(account)

        for transaction in self.transactions:
            book_node.append(transaction.as_xml)

        if self.template_root_account or self.template_transactions:
            template_transactions_node = ElementTree.SubElement(book_node, 'gnc:template-transactions')
            for account in self.template_root_account.as_xml:
                template_transactions_node.append(account)
            for transaction in self.template_transactions:
                template_transactions_node.append(transaction.as_xml)

        for scheduled_transaction in self.scheduled_transactions:
            book_node.append(scheduled_transaction.as_xml)

        for budget in self.budgets:
            book_node.append(budget.as_xml)

        return book_node

    @classmethod
    def from_xml(cls, book_node, namespaces, sort_transactions=True):
        """
        Creates a Book object from the GnuCash XML

        :param book_node: XML node for the book
        :type book_node: ElementTree.Element
        :param namespaces: XML namespaces for GnuCash elements
        :type namespaces: dict[str, str]
        :param sort_transactions: Flag for if transactions should be sorted by date_posted when reading from XML
        :type sort_transactions: bool
        :return: Book object from XML
        :rtype: Book
        """
        new_book = Book()
        new_book.guid = book_node.find('book:id', namespaces).text
        accounts = book_node.findall('gnc:account', namespaces)
        transactions = book_node.findall('gnc:transaction', namespaces)
        slots = book_node.find('book:slots', namespaces)

        if slots is not None:
            for slot in slots.findall('slot'):
                new_book.slots.append(Slot.from_xml(slot, namespaces))

        commodities = book_node.findall('gnc:commodity', namespaces)
        for commodity in commodities:
            new_book.commodities.append(Commodity.from_xml(commodity, namespaces))

        account_objects = list()
        transaction_manager = TransactionManager()
        transaction_manager.disable_sort = not sort_transactions

        for account in accounts:
            account_objects.append(Account.from_xml(account, namespaces, account_objects))

        for transaction in transactions:
            transaction_manager.add(Transaction.from_xml(transaction, namespaces, account_objects))

        new_book.root_account = [x for x in account_objects if x.type == 'ROOT'][0]
        new_book.transactions = transaction_manager

        template_transactions_xml = book_node.findall('gnc:template-transactions', namespaces)
        if template_transactions_xml is not None:
            template_accounts = []
            template_transactions = []
            for template_transaction in template_transactions_xml:
                # Process accounts before transactions
                for subelement in template_transaction:
                    if not subelement.tag.endswith('account'):
                        continue
                    template_accounts.append(Account.from_xml(subelement, namespaces, template_accounts))

                for subelement in template_transaction:
                    if not subelement.tag.endswith('transaction'):
                        continue
                    template_transactions.append(Transaction.from_xml(subelement, namespaces, template_accounts))
            new_book.template_transactions = template_transactions
            template_root_accounts = [x for x in template_accounts if x.type == 'ROOT']
            if template_root_accounts:
                new_book.template_root_account = template_root_accounts[0]

        scheduled_transactions = book_node.findall('gnc:schedxaction', namespaces)
        if scheduled_transactions is not None:
            for scheduled_transaction in scheduled_transactions:
                new_book.scheduled_transactions.append(
                    ScheduledTransaction.from_xml(scheduled_transaction,
                                                  namespaces,
                                                  new_book.template_root_account))

        budgets = book_node.findall('gnc:budget', namespaces)
        if budgets is not None:
            for budget in budgets:
                new_book.budgets.append(Budget.from_xml(budget, namespaces))

        return new_book

    def get_account(self, *paths_to_account, current_level=None):
        """
        Retrieves an account based on a path of account names

        :param paths_to_account: Names of accounts that indicate the path
        :param current_level: Account to start the search at (None indicates to start at the root account)
        :type current_level: Account
        :return: Account object if found, otherwise None
        :rtype: Account

        Example: ``get_account('Assets', 'Current Assets', 'Checking Account')``
        """
        if current_level is None:
            current_level = self.root_account
        paths_to_account = list(paths_to_account)
        next_level = paths_to_account.pop(0)
        for account in current_level.children:
            if account.name == next_level:
                if not paths_to_account:
                    return account
                return self.get_account(*paths_to_account, current_level=account)
        return None

    def get_account_balance(self, account):
        """
        Retrieves the balance for a specified account based on the transactions in the Book.

        :param account: Account object to retrieve the balance of.
        :type account: Account
        :return: Account balance if applicable transactions found, otherwise 0.
        :rtype: decimal.Decimal or int
        """
        account_balance = 0
        account_transactions = list(filter(lambda x: account in [y.account for y in x.splits], self.transactions))
        # account_transactions = [x for x in self.transactions if account in [x.from_account, x.to_account]]
        for transaction in account_transactions:
            split = next(filter(lambda x: x.account == account, transaction.splits))
            account_balance += split.amount
        return account_balance

    def __str__(self):
        return '{} transactions'.format(len(self.transactions))

    def __repr__(self):
        return str(self)


class Budget(GuidObject):
    """
    Class object representing a Budget in GnuCash
    """
    def __init__(self):
        super(Budget, self).__init__()
        self.name = None
        self.description = None
        self.period_count = None
        self.recurrence_multiplier = None
        self.recurrence_period_type = None
        self.recurrence_start = None
        self.slots = []

    @property
    def as_xml(self):
        """
        Returns the current budget as GnuCash-compatible XML

        :return: Current budget as XML
        :rtype: xml.etree.ElementTree.Element
        """
        budget_node = ElementTree.Element('gnc:budget', attrib={'version': '2.0.0'})
        ElementTree.SubElement(budget_node, 'bgt:id', {'type': 'guid'}).text = self.guid
        ElementTree.SubElement(budget_node, 'bgt:name').text = self.name
        ElementTree.SubElement(budget_node, 'bgt:description').text = self.description

        if self.period_count is not None:
            ElementTree.SubElement(budget_node, 'bgt:num-periods').text = str(self.period_count)

        if self.recurrence_multiplier is not None or self.recurrence_period_type is not None or \
                self.recurrence_start is not None:
            recurrence_node = ElementTree.SubElement(budget_node, 'bgt:recurrence', attrib={'version': '1.0.0'})
            if self.recurrence_multiplier is not None:
                ElementTree.SubElement(recurrence_node, 'recurrence:mult').text = str(self.recurrence_multiplier)
            if self.recurrence_period_type is not None:
                ElementTree.SubElement(recurrence_node, 'recurrence:period_type').text = self.recurrence_period_type
            if self.recurrence_start is not None:
                start_node = ElementTree.SubElement(recurrence_node, 'recurrence:start')
                ElementTree.SubElement(start_node, 'gdate').text = self.recurrence_start.strftime('%Y-%m-%d')

        if self.slots:
            slots_node = ElementTree.SubElement(budget_node, 'bgt:slots')
            for slot in self.slots:
                slots_node.append(slot.as_xml)

        return budget_node

    @classmethod
    def from_xml(cls, budget_node, namespaces):
        """
        Creates a Budget object from the GnuCash XML

        :param budget_node: XML node for the budget
        :type budget_node: ElementTree.Element
        :param namespaces: XML namespaces for GnuCash elements
        :type namespaces: dict[str, str]
        :return: Budget object from XML
        :rtype: Budget
        """
        new_obj = cls()

        id_node = budget_node.find('bgt:id', namespaces)
        if id_node is not None:
            new_obj.guid = id_node.text

        name_node = budget_node.find('bgt:name', namespaces)
        if name_node is not None:
            new_obj.name = name_node.text

        description_node = budget_node.find('bgt:description', namespaces)
        if description_node is not None:
            new_obj.description = description_node.text

        period_count_node = budget_node.find('bgt:num-periods', namespaces)
        if period_count_node is not None:
            new_obj.period_count = int(period_count_node.text)

        recurrence_node = budget_node.find('bgt:recurrence', namespaces)
        if recurrence_node is not None:
            multiplier_node = recurrence_node.find('recurrence:mult', namespaces)
            if multiplier_node is not None:
                new_obj.recurrence_multiplier = int(multiplier_node.text)

            period_type_node = recurrence_node.find('recurrence:period_type', namespaces)
            if period_type_node is not None:
                new_obj.recurrence_period_type = period_type_node.text

            recurrence_start_node = recurrence_node.find('recurrence:start', namespaces)
            if recurrence_start_node is not None:
                gdate_node = recurrence_start_node.find('gdate', namespaces)
                if gdate_node is not None:
                    new_obj.recurrence_start = datetime.strptime(gdate_node.text, '%Y-%m-%d')

        slots = budget_node.find('bgt:slots', namespaces)
        if slots:
            for slot in slots.findall('slot', namespaces):
                new_obj.slots.append(Slot.from_xml(slot, namespaces))

        return new_obj
