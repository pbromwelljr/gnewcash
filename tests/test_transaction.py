from datetime import datetime
from decimal import Decimal

import pytz

import gnewcash.account as acc
import gnewcash.gnucash_file as gcf
import gnewcash.transaction as trn


def test_transaction_cleared():
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
    book = gnucash_file.books[0]
    first_transaction = book.transactions[0]
    assert first_transaction.cleared is False

    first_transaction.mark_transaction_cleared()
    assert first_transaction.cleared is True


def test_add_transaction_chronological():
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
    book = gnucash_file.books[0]
    transaction_manager = book.transactions
    transaction_manager.disable_sort = False

    new_transaction = trn.Transaction()
    new_transaction.date_posted = datetime(2019, 7, 28, tzinfo=pytz.timezone('US/Eastern'))
    new_transaction.date_entered = datetime.now(tz=pytz.timezone('US/Eastern'))
    new_transaction.description = 'Unit Test Transaction'

    transaction_manager.add(new_transaction)

    assert transaction_manager[0] != new_transaction
    assert transaction_manager[-1] != new_transaction

    # Adding one that should be at the end
    end_transaction = trn.Transaction()
    end_transaction.date_posted = datetime(2038, 1, 1, tzinfo=pytz.timezone('US/Eastern'))
    end_transaction.date_entered = datetime.now(tz=pytz.timezone('US/Eastern'))
    end_transaction.description = 'Unit Test Transaction'

    transaction_manager.add(end_transaction)

    assert transaction_manager[-1] == end_transaction


def test_delete_transaction():
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
    book = gnucash_file.books[0]
    transaction_manager = book.transactions

    first_transaction = transaction_manager[0]
    transaction_manager.delete(first_transaction)

    assert transaction_manager[0] != first_transaction

def test_get_transactions():
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
    book = gnucash_file.books[0]
    transaction_manager = book.transactions
    checking_account = book.get_account('Assets', 'Current Assets', 'Checking Account')

    transactions = list(transaction_manager.get_transactions(checking_account))
    assert len(transactions) > 0
    assert len(transactions) < len(transaction_manager)


def test_get_account_starting_balance():
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
    book = gnucash_file.books[0]
    transaction_manager = book.transactions
    checking_account = book.get_account('Assets', 'Current Assets', 'Checking Account')

    starting_balance = transaction_manager.get_account_starting_balance(checking_account)
    assert starting_balance == Decimal('2000')


def test_get_account_ending_balance():
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
    book = gnucash_file.books[0]
    transaction_manager = book.transactions
    checking_account = book.get_account('Assets', 'Current Assets', 'Checking Account')

    ending_balance = transaction_manager.get_account_ending_balance(checking_account)
    assert ending_balance == Decimal('1240')


def test_minimum_balance_past_date():
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
    book = gnucash_file.books[0]
    transaction_manager = book.transactions
    checking_account = book.get_account('Assets', 'Current Assets', 'Checking Account')

    minimum_balance, minimum_balance_date = transaction_manager.minimum_balance_past_date(
        checking_account, datetime(2019, 12, 1, tzinfo=pytz.timezone('US/Eastern'))
    )
    minimum_balance_date = minimum_balance_date.replace(tzinfo=None)
    assert minimum_balance == Decimal('1240')
    assert minimum_balance_date == datetime(2019, 12, 31, 5, 59, 0, 0)


def test_get_balance_at_date():
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
    book = gnucash_file.books[0]
    transaction_manager = book.transactions
    checking_account = book.get_account('Assets', 'Current Assets', 'Checking Account')

    test_date = datetime(2019, 7, 28, tzinfo=pytz.timezone('US/Eastern'))
    balance_at_date = transaction_manager.get_balance_at_date(checking_account, test_date)

    assert balance_at_date == Decimal('2620')


def test_transaction_notes():
    test_transaction = trn.Transaction()
    assert len(test_transaction.slots) == 0
    assert test_transaction.notes is None

    test_transaction.notes = 'This is a unit test note'
    assert len(test_transaction.slots) == 1
    assert test_transaction.slots[0].key == 'notes'
    assert test_transaction.slots[0].value == 'This is a unit test note'
    assert test_transaction.slots[0].type == 'string'

    assert test_transaction.notes == 'This is a unit test note'

    test_transaction.notes = 'This is another unit test note'
    assert len(test_transaction.slots) == 1
    assert test_transaction.slots[0].key == 'notes'
    assert test_transaction.slots[0].value == 'This is another unit test note'
    assert test_transaction.slots[0].type == 'string'

    test_transaction = trn.Transaction()
    test_transaction.reversed_by = 'test123456'
    assert test_transaction.notes is None

def test_transaction_reversed_by():
    test_transaction = trn.Transaction()
    assert len(test_transaction.slots) == 0
    assert test_transaction.reversed_by is None

    test_transaction.reversed_by = 'test12345'
    assert len(test_transaction.slots) == 1
    assert test_transaction.slots[0].key == 'reversed-by'
    assert test_transaction.slots[0].value == 'test12345'
    assert test_transaction.slots[0].type == 'guid'

    assert test_transaction.reversed_by == 'test12345'

    test_transaction.reversed_by = 'test23456'
    assert len(test_transaction.slots) == 1
    assert test_transaction.slots[0].key == 'reversed-by'
    assert test_transaction.slots[0].value == 'test23456'
    assert test_transaction.slots[0].type == 'guid'

    test_transaction = trn.Transaction()
    test_transaction.notes = 'This is a test'
    assert test_transaction.reversed_by is None


def test_transaction_voided():
    test_transaction = trn.Transaction()
    assert len(test_transaction.slots) == 0
    assert test_transaction.voided is None

    test_transaction.voided = 'test12345'
    assert len(test_transaction.slots) == 1
    assert test_transaction.slots[0].key == 'trans-read-only'
    assert test_transaction.slots[0].value == 'test12345'
    assert test_transaction.slots[0].type == 'string'

    assert test_transaction.voided == 'test12345'

    test_transaction.voided = 'test23456'
    assert len(test_transaction.slots) == 1
    assert test_transaction.slots[0].key == 'trans-read-only'
    assert test_transaction.slots[0].value == 'test23456'
    assert test_transaction.slots[0].type == 'string'

    test_transaction = trn.Transaction()
    test_transaction.notes = 'This is a test'
    assert test_transaction.voided is None


def test_transaction_void_time():
    test_transaction = trn.Transaction()
    assert len(test_transaction.slots) == 0
    assert test_transaction.void_time is None

    test_transaction.void_time = 'test12345'
    assert len(test_transaction.slots) == 1
    assert test_transaction.slots[0].key == 'void-time'
    assert test_transaction.slots[0].value == 'test12345'
    assert test_transaction.slots[0].type == 'string'

    assert test_transaction.void_time == 'test12345'

    test_transaction.void_time = 'test23456'
    assert len(test_transaction.slots) == 1
    assert test_transaction.slots[0].key == 'void-time'
    assert test_transaction.slots[0].value == 'test23456'
    assert test_transaction.slots[0].type == 'string'

    test_transaction = trn.Transaction()
    test_transaction.notes = 'This is a test'
    assert test_transaction.void_time is None


def test_transaction_void_reason():
    test_transaction = trn.Transaction()
    assert len(test_transaction.slots) == 0
    assert test_transaction.void_reason is None

    test_transaction.void_reason = 'test12345'
    assert len(test_transaction.slots) == 1
    assert test_transaction.slots[0].key == 'void-reason'
    assert test_transaction.slots[0].value == 'test12345'
    assert test_transaction.slots[0].type == 'string'

    assert test_transaction.void_reason == 'test12345'

    test_transaction.void_reason = 'test23456'
    assert len(test_transaction.slots) == 1
    assert test_transaction.slots[0].key == 'void-reason'
    assert test_transaction.slots[0].value == 'test23456'
    assert test_transaction.slots[0].type == 'string'

    test_transaction = trn.Transaction()
    test_transaction.notes = 'This is a test'
    assert test_transaction.void_reason is None


def test_transaction_associated_uri():
    test_transaction = trn.Transaction()
    assert len(test_transaction.slots) == 0
    assert test_transaction.associated_uri is None

    test_transaction.associated_uri = 'https://www.google.com'
    assert len(test_transaction.slots) == 1
    assert test_transaction.slots[0].key == 'assoc_uri'
    assert test_transaction.slots[0].value == 'https://www.google.com'
    assert test_transaction.slots[0].type == 'string'

    assert test_transaction.associated_uri == 'https://www.google.com'

    test_transaction.associated_uri = 'https://www.microsoft.com'
    assert len(test_transaction.slots) == 1
    assert test_transaction.slots[0].key == 'assoc_uri'
    assert test_transaction.slots[0].value == 'https://www.microsoft.com'
    assert test_transaction.slots[0].type == 'string'

    test_transaction = trn.Transaction()
    test_transaction.notes = 'This is a test'
    assert test_transaction.associated_uri is None


def test_create_transaction():
    test_from_account = acc.BankAccount()
    test_from_account.name = 'Checking Account'

    test_to_account = acc.ExpenseAccount()
    test_to_account.name = 'Video Games'

    test_transaction = trn.SimpleTransaction()
    test_transaction.from_account = test_from_account
    test_transaction.to_account = test_to_account
    test_transaction.amount = Decimal('60.00')
    test_transaction.date_entered = datetime.now()
    test_transaction.date_posted = datetime.now()

    assert test_transaction.from_account == test_from_account
    assert test_transaction.to_account == test_to_account
    assert test_transaction.amount == Decimal('60.00')
    assert len(test_transaction.splits) == 2
    assert test_transaction.splits[0].account == test_from_account
    assert test_transaction.splits[0].amount == Decimal('-60.00')
    assert test_transaction.splits[1].account == test_to_account
    assert test_transaction.splits[1].amount == Decimal('60.00')
