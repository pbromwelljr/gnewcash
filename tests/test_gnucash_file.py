import gzip
import json
import unittest
from xml.etree import ElementTree

import gnewcash.gnucash_file as gcf


class TestGnuCashFile(unittest.TestCase):
    def test_read_write(self):
        gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash', sort_transactions=False)
        gnucash_file.build_file('test_files/Test1.testresult.gnucash', prettify_xml=True)

        original_tree = ElementTree.parse(source='test_files/Test1.gnucash')
        original_root = original_tree.getroot()

        test_tree = ElementTree.parse(source='test_files/Test1.testresult.gnucash')
        test_root = test_tree.getroot()

        self.check_gnucash_elements(original_root, test_root)

    def check_gnucash_elements(self, original_element, test_element):
        self.assertEqual(original_element.tag, test_element.tag)
        self.assertEqual(json.dumps(original_element.attrib), json.dumps(test_element.attrib))
        if original_element.text:
            original_element.text = original_element.text.strip()
        if test_element.text:
            test_element.text = test_element.text.strip()
        self.assertEqual(original_element.text, test_element.text)
        for original_subelement, test_subelement in zip(list(original_element), list(test_element)):
            self.check_gnucash_elements(original_subelement, test_subelement)

    def test_file_not_found(self):
        gnucash_file = gcf.GnuCashFile.read_file('test_files/thisfiledoesnotexist.gnucash')
        self.assertEqual(0, len(gnucash_file.books))

    def test_load_gzipped_file(self):
        gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gz.gnucash')
        self.assertEqual(1, len(gnucash_file.books))

    def test_get_account(self):
        gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
        book = gnucash_file.books[0]
        account = book.get_account('Assets', 'Current Assets', 'Checking Account')
        self.assertNotEqual(None, account)

    def test_get_account_fail(self):
        gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
        book = gnucash_file.books[0]
        account = book.get_account('This', 'Path', 'Does', 'Not', 'Exist')
        self.assertEqual(None, account)

    def test_get_account_balance(self):
        gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
        book = gnucash_file.books[0]
        account = book.get_account('Assets', 'Current Assets', 'Checking Account')
        balance = book.get_account_balance(account)
        self.assertEqual(balance, 1240)

    def test_get_account_balance_credit(self):
        gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
        book = gnucash_file.books[0]
        account = book.get_account('Assets', 'Current Assets', 'Credit Card')
        balance = book.get_account_balance(account)
        self.assertEqual(balance, 0)

    def test_gzip_write(self):
        gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash', sort_transactions=False)
        gnucash_file.build_file('test_files/Test1.testresult.gnucash', prettify_xml=True, use_gzip=True)
        with gzip.open('test_files/Test1.testresult.gnucash', 'rb') as test_file, \
                gzip.open('test_files/Test1.gz.gnucash', 'rb') as actual_file:
            test_file_contents = test_file.read()
            actual_file_contents = actual_file.read()

            original_root = ElementTree.fromstring(actual_file_contents)
            test_root = ElementTree.fromstring(test_file_contents)

            self.check_gnucash_elements(original_root, test_root)
