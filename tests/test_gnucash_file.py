import gzip
import json
import os
import sqlite3
from xml.etree import ElementTree

import gnewcash.file_formats as gff
import gnewcash.gnucash_file as gcf
import gnewcash.transaction as trn


def test_read_write():
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash', sort_transactions=False,
                                             file_format=gff.XMLFileFormat)
    gnucash_file.build_file('test_files/Test1.testresult.gnucash', prettify_xml=True,
                            file_format=gff.XMLFileFormat)

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
    gnucash_file = gcf.GnuCashFile.read_file('test_files/thisfiledoesnotexist.gnucash',
                                             file_format=gff.XMLFileFormat)
    assert 0 == len(gnucash_file.books)


def test_load_gzipped_file():
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gz.gnucash', file_format=gff.GZipXMLFileFormat)
    assert 1 == len(gnucash_file.books)


def test_get_account():
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash', file_format=gff.XMLFileFormat)
    book = gnucash_file.books[0]
    account = book.get_account('Assets', 'Current Assets', 'Checking Account')
    assert account is not None


def test_get_account_fail():
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash', file_format=gff.XMLFileFormat)
    book = gnucash_file.books[0]
    account = book.get_account('This', 'Path', 'Does', 'Not', 'Exist')
    assert account is None


def test_get_account_balance():
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash', file_format=gff.XMLFileFormat)
    book = gnucash_file.books[0]
    account = book.get_account('Assets', 'Current Assets', 'Checking Account')
    balance = book.get_account_balance(account)
    assert balance == 1240


def test_get_account_balance_credit():
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash', file_format=gff.XMLFileFormat)
    book = gnucash_file.books[0]
    account = book.get_account('Assets', 'Current Assets', 'Credit Card')
    balance = book.get_account_balance(account)
    assert balance == 0


def test_gzip_write():
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash', sort_transactions=False,
                                             file_format=gff.XMLFileFormat)
    gnucash_file.build_file('test_files/Test1.testresult.gnucash', prettify_xml=True,
                            file_format=gff.GZipXMLFileFormat)
    with gzip.open('test_files/Test1.testresult.gnucash', 'rb') as test_file, \
            gzip.open('test_files/Test1.gz.gnucash', 'rb') as actual_file:
        test_file_contents = test_file.read()
        actual_file_contents = actual_file.read()

        original_root = ElementTree.fromstring(actual_file_contents)
        test_root = ElementTree.fromstring(test_file_contents)

        check_gnucash_elements(original_root, test_root)


def test_simple_transaction_load():
    # TODO: Fix unit test after SimpleTransaction loader is done
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash', file_format=gff.XMLFileFormat,
                                             sort_transactions=False)
    gnucash_file.build_file('test_files/Test1.simpletransaction.testresult.gnucash', prettify_xml=True,
                            file_format=gff.XMLFileFormat)

    original_tree = ElementTree.parse(source='test_files/Test1.gnucash')
    original_root = original_tree.getroot()

    test_tree = ElementTree.parse(source='test_files/Test1.simpletransaction.testresult.gnucash')
    test_root = test_tree.getroot()

    check_gnucash_elements(original_root, test_root)


def test_read_write_sqlite():
    result_sqlite_file = 'test_files/Test1.sqlite.testresult.gnucash'
    if os.path.exists(result_sqlite_file):
        os.remove(result_sqlite_file)
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.sqlite.gnucash', file_format=gff.SqliteFileFormat,
                                             sort_transactions=False)
    gnucash_file.build_file(result_sqlite_file, file_format=gff.SqliteFileFormat)

    original_conn, new_conn = (sqlite3.connect('test_files/Test1.sqlite.gnucash'),
                               sqlite3.connect('test_files/Test1.sqlite.testresult.gnucash'))

    # Asserting we have the same tables
    original_tables, new_tables = (get_sqlite_tables(original_conn),
                                   get_sqlite_tables(new_conn))
    assert original_tables == new_tables

    for table_name in original_tables:
        # Asserting we have the same table schema
        original_columns, new_columns = (get_sqlite_columns(original_conn, table_name),
                                         get_sqlite_columns(new_conn, table_name))
        assert original_columns == new_columns

        # Asserting we have the same data
        original_data, new_data = (get_sqlite_table_data(original_conn, table_name),
                                   get_sqlite_table_data(new_conn, table_name))
        for original_row, new_row in zip(original_data, new_data):
            print('Testing row')
            assert original_row == new_row

    original_conn.close()
    new_conn.close()


def get_sqlite_tables(conn: sqlite3.Connection):
    cursor = conn.cursor()
    sql = 'SELECT DISTINCT tbl_name FROM sqlite_master ORDER BY tbl_name ASC'
    cursor.execute(sql)
    tables = []
    for table_name, in cursor.fetchall():
        if not table_name.startswith('sqlite_'):
            tables.append(table_name)
    cursor.close()

    return tables


def get_sqlite_columns(conn: sqlite3.Connection, table_name: str):
    cursor = conn.cursor()
    sql = f'pragma table_info({table_name})'
    cursor.execute(sql)
    columns = []
    for _, column_name, data_type, nullable, default_value, is_primary_key in cursor.fetchall():
        columns.append({
            'name': column_name,
            'data_type': data_type,
            'nullable': nullable,
            'default_value': default_value,
            'is_primary_key': is_primary_key
        })
    cursor.close()
    return columns


def get_sqlite_table_data(conn: sqlite3.Connection, table_name: str):
    cursor = conn.cursor()
    sql = f'SELECT * FROM {table_name}'
    cursor.execute(sql)
    column_names = [column[0] for column in cursor.description]
    rows = []
    for row in cursor.fetchall():
        row_data = dict(zip(column_names, row))
        rows.append(row_data)
    return rows


def test_read_sort_standard():
    test_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash',
                                          gff.XMLFileFormat,
                                          sort_method=trn.StandardSort())
    transactions = test_file.books[0].transactions.transactions
    assert transactions[0].date_posted <= transactions[1].date_posted


def test_read_sort_standard_reversed():
    test_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash',
                                          gff.XMLFileFormat,
                                          sort_method=trn.StandardSort(reverse=True))
    transactions = test_file.books[0].transactions.transactions
    assert transactions[0].date_posted >= transactions[1].date_posted


def test_read_sort_date():
    test_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash',
                                          gff.XMLFileFormat,
                                          sort_method=trn.DateSort())
    transactions = test_file.books[0].transactions.transactions
    assert transactions[0].date_posted <= transactions[1].date_posted


def test_read_sort_date_reversed():
    test_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash',
                                          gff.XMLFileFormat,
                                          sort_method=trn.DateSort(reverse=True))
    transactions = test_file.books[0].transactions.transactions
    assert transactions[0].date_posted >= transactions[1].date_posted



def test_read_sort_date_of_entry():
    test_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash',
                                          gff.XMLFileFormat,
                                          sort_method=trn.DateOfEntrySort())
    transactions = test_file.books[0].transactions.transactions
    assert transactions[0].date_entered <= transactions[1].date_entered


def test_read_sort_date_of_entry_reversed():
    test_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash',
                                          gff.XMLFileFormat,
                                          sort_method=trn.DateOfEntrySort(reverse=True))
    transactions = test_file.books[0].transactions.transactions
    assert transactions[0].date_entered >= transactions[1].date_entered


def test_read_sort_transaction_number():
    test_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash',
                                          gff.XMLFileFormat,
                                          sort_method=trn.TransactionNumberSort())
    transactions = test_file.books[0].transactions.transactions
    assert transactions[0].guid <= transactions[1].guid


def test_read_sort_transaction_number_reversed():
    test_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash',
                                          gff.XMLFileFormat,
                                          sort_method=trn.TransactionNumberSort(reverse=True))
    transactions = test_file.books[0].transactions.transactions
    assert transactions[0].guid >= transactions[1].guid


def test_read_sort_description():
    test_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash',
                                          gff.XMLFileFormat,
                                          sort_method=trn.DescriptionSort())
    transactions = test_file.books[0].transactions.transactions
    assert transactions[0].description <= transactions[1].description


def test_read_sort_description_reversed():
    test_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash',
                                          gff.XMLFileFormat,
                                          sort_method=trn.DescriptionSort(reverse=True))
    transactions = test_file.books[0].transactions.transactions
    assert transactions[0].description >= transactions[1].description


def test_read_sort_amount():
    test_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash',
                                          gff.XMLFileFormat,
                                          sort_method=trn.AmountSort())
    transactions = test_file.books[0].transactions.transactions
    assert transactions[0].splits[0].amount <= transactions[1].splits[0].amount


def test_read_sort_amount_reversed():
    test_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash',
                                          gff.XMLFileFormat,
                                          sort_method=trn.AmountSort(reverse=True))
    transactions = test_file.books[0].transactions.transactions
    assert transactions[0].splits[0].amount >= transactions[1].splits[0].amount


def test_read_sort_number_action():
    test_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash',
                                          gff.XMLFileFormat,
                                          sort_method=trn.NumberActionSort())
    transactions = test_file.books[0].transactions.transactions
    assert (transactions[0].splits[0].action or '') <= (transactions[1].splits[0].action or '')


def test_read_sort_number_action_reversed():
    test_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash',
                                          gff.XMLFileFormat,
                                          sort_method=trn.NumberActionSort(reverse=True))
    transactions = test_file.books[0].transactions.transactions
    assert (transactions[0].splits[0].action or '') >= (transactions[1].splits[0].action or '')

def test_read_sort_memo():
    test_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash',
                                          gff.XMLFileFormat,
                                          sort_method=trn.MemoSort())
    transactions = test_file.books[0].transactions.transactions
    assert (transactions[0].splits[0].memo or '') <= (transactions[1].splits[0].memo or '')


def test_read_sort_memo_reversed():
    test_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash',
                                          gff.XMLFileFormat,
                                          sort_method=trn.MemoSort(reverse=True))
    transactions = test_file.books[0].transactions.transactions
    assert (transactions[0].splits[0].memo or '') >= (transactions[1].splits[0].memo or '')


def test_get_all_accounts():
    test_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash', gff.XMLFileFormat)
    current_book = test_file.books[0]
    all_accounts = list(current_book.get_all_accounts())
    assert len(all_accounts) == 19
