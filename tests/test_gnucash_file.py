import gzip
import json
from xml.etree import ElementTree

import gnewcash.gnucash_file as gcf
import gnewcash.transaction as trn


def test_read_write():
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash', sort_transactions=False)
    gnucash_file.build_file('test_files/Test1.testresult.gnucash', prettify_xml=True)

    original_tree = ElementTree.parse(source='test_files/Test1.gnucash')
    original_root = original_tree.getroot()

    test_tree = ElementTree.parse(source='test_files/Test1.testresult.gnucash')
    test_root = test_tree.getroot()

    check_gnucash_elements(original_root, test_root)


def check_gnucash_elements(original_element, test_element, original_path=None, test_path=None):
    if original_path is None:
        original_path = '/'
    if test_path is None:
        test_path = '/'
    assertion_message = 'Original path: ' + original_path + '\n' + ' Test path: ' + test_path
    assert original_element.tag == test_element.tag, assertion_message
    assert json.dumps(original_element.attrib) == json.dumps(test_element.attrib), assertion_message
    if original_element.text:
        original_element.text = original_element.text.strip()
    if test_element.text:
        test_element.text = test_element.text.strip()
    assert original_element.text == test_element.text, assertion_message
    for original_subelement, test_subelement in zip(list(original_element), list(test_element)):
        check_gnucash_elements(original_subelement, test_subelement,
                               original_path + original_element.tag + '/',
                               test_path + test_element.tag + '/')


def test_file_not_found():
    gnucash_file = gcf.GnuCashFile.read_file('test_files/thisfiledoesnotexist.gnucash')
    assert 0 == len(gnucash_file.books)


def test_load_gzipped_file():
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gz.gnucash')
    assert 1 == len(gnucash_file.books)


def test_get_account():
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
    book = gnucash_file.books[0]
    account = book.get_account('Assets', 'Current Assets', 'Checking Account')
    assert account is not None


def test_get_account_fail():
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
    book = gnucash_file.books[0]
    account = book.get_account('This', 'Path', 'Does', 'Not', 'Exist')
    assert account is None


def test_get_account_balance():
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
    book = gnucash_file.books[0]
    account = book.get_account('Assets', 'Current Assets', 'Checking Account')
    balance = book.get_account_balance(account)
    assert balance == 1240


def test_get_account_balance_credit():
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
    book = gnucash_file.books[0]
    account = book.get_account('Assets', 'Current Assets', 'Credit Card')
    balance = book.get_account_balance(account)
    assert balance == 0


def test_gzip_write():
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash', sort_transactions=False)
    gnucash_file.build_file('test_files/Test1.testresult.gnucash', prettify_xml=True, use_gzip=True)
    with gzip.open('test_files/Test1.testresult.gnucash', 'rb') as test_file, \
            gzip.open('test_files/Test1.gz.gnucash', 'rb') as actual_file:
        test_file_contents = test_file.read()
        actual_file_contents = actual_file.read()

        original_root = ElementTree.fromstring(actual_file_contents)
        test_root = ElementTree.fromstring(test_file_contents)

        check_gnucash_elements(original_root, test_root)


def test_simple_transaction_load():
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash', sort_transactions=False,
                                             transaction_class=trn.SimpleTransaction)
    gnucash_file.build_file('test_files/Test1.simpletransaction.testresult.gnucash', prettify_xml=True)

    original_tree = ElementTree.parse(source='test_files/Test1.gnucash')
    original_root = original_tree.getroot()

    test_tree = ElementTree.parse(source='test_files/Test1.simpletransaction.testresult.gnucash')
    test_root = test_tree.getroot()

    check_gnucash_elements(original_root, test_root)
