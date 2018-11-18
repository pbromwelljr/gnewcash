import gzip
import os.path
from datetime import datetime
from logging import getLogger
from xml.etree import ElementTree
from xml.dom import minidom

from gnewcash.guid_object import GuidObject
from gnewcash.transaction import Split, Transaction, TransactionManager
from gnewcash.account import Account, AccountType
from gnewcash.commodity import Commodity


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
    def read_file(cls, source_file):
        """
        Reads the specified .gnucash file and loads it into memory

        :param source_file: Full or relative path to the .gnucash file.
        :type source_file: str
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
                new_book = Book.from_xml(book, namespaces)
                built_file.books.append(new_book)
        else:
            logger.warning('Could not find %s', source_file)
        return built_file

    def build_file(self, target_file):
        """
        Writes the contents of the GnuCashFile object out to a .gnucash file on disk

        :param target_file: Full or relative path to the target file
        :type target_file: str
        """
        namespace_info = self.namespace_data
        root_node = ElementTree.Element('gnc-v2', {'xmlns:' + identifier: value
                                                   for identifier, value in namespace_info.items()})
        book_count_node = ElementTree.Element('gnc:count-data', {'cd:type': 'book'})
        book_count_node.text = str(len(self.books))
        root_node.append(book_count_node)

        for book in self.books:
            root_node.append(book.as_xml)

        element_tree = ElementTree.ElementTree(root_node)
        element_tree.write(target_file, encoding='utf-8', xml_declaration=True)

        # Making our resulting XML pretty
        xml = minidom.parse(target_file)
        with open(target_file, 'w', encoding='utf-8') as target_file_handle:
            target_file_handle.write(xml.toprettyxml(encoding='utf-8').decode('utf-8'))

        # TODO: Add support for writing in gzip compression


class Book(GuidObject):
    """
    Represents a Book in GnuCash
    """
    def __init__(self, root_account=None, transactions=None, commodities=None):
        super(Book, self).__init__()
        self.root_account = root_account
        self.transactions = transactions or TransactionManager()
        self.commodities = commodities or []

    @property
    def as_xml(self):
        """
        Returns the current book as GnuCash-compatible XML

        :return: List of ElementTree.Element objects
        :rtype: list[xml.etree.ElementTree.Element]
        """
        book_node = ElementTree.Element('gnc:book', {'version': '2.0.0'})
        book_id_node = ElementTree.SubElement(book_node, 'book:id', {'type': 'guid'})
        book_id_node.text = self.guid

        accounts_xml = self.root_account.as_xml

        commodity_count_node = ElementTree.SubElement(book_node, 'gnc:count-data', {'cd:type': 'commodity'})
        commodity_count_node.text = str(len(list(filter(lambda x: x.id != 'template', self.commodities))))

        account_count_node = ElementTree.SubElement(book_node, 'gnc:count-data', {'cd:type': 'account'})
        account_count_node.text = str(len(accounts_xml))

        transaction_count_node = ElementTree.SubElement(book_node, 'gnc:count-data', {'cd:type': 'transaction'})
        transaction_count_node.text = str(len(self.transactions))

        for commodity in self.commodities:
            book_node.append(commodity.as_xml)

        for account in accounts_xml:
            book_node.append(account)

        for transaction in self.transactions:
            book_node.append(transaction.as_xml)

        return book_node

    @classmethod
    def from_xml(cls, book_node, namespaces):
        new_book = Book()
        new_book.guid = book_node.find('book:id', namespaces).text
        accounts = book_node.findall('gnc:account', namespaces)
        transactions = book_node.findall('gnc:transaction', namespaces)

        commodities = book_node.findall('gnc:commodity', namespaces)
        for commodity in commodities:
            new_book.commodities.append(Commodity.from_xml(commodity, namespaces))

        account_objects = list()
        transaction_manager = TransactionManager()
        transaction_manager.disable_sort = True

        for account in accounts:
            account_objects.append(Account.from_xml(account, namespaces, account_objects))

        for transaction in transactions:
            transaction_manager.add(Transaction.from_xml(transaction, namespaces, account_objects))

        new_book.root_account = [x for x in account_objects if x.type == 'ROOT'][0]
        new_book.transactions = transaction_manager

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
        account_transactions = [x for x in self.transactions if account in [x.from_account, x.to_account]]
        for transaction in account_transactions:
            if account.type == AccountType.CREDIT:
                transaction.amount *= -1
            if transaction.from_account == account:
                account_balance -= transaction.amount
            elif transaction.to_account == account:
                account_balance += transaction.amount
        return account_balance

    def __str__(self):
        return '{} transactions'.format(len(self.transactions))

    def __repr__(self):
        return str(self)

