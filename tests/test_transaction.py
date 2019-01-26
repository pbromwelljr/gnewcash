from datetime import datetime
from decimal import Decimal
import unittest

import gnewcash.gnucash_file as gcf
import gnewcash.transaction as trn
import gnewcash.account as acc

import pytz


class TestTransaction(unittest.TestCase):
    def test_transaction_cleared(self):
        gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
        book = gnucash_file.books[0]
        first_transaction = book.transactions[0]
        self.assertFalse(first_transaction.cleared)

        first_transaction.mark_transaction_cleared()
        self.assertTrue(first_transaction.cleared)

    def test_add_transaction_chronological(self):
        gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
        book = gnucash_file.books[0]
        transaction_manager = book.transactions
        transaction_manager.disable_sort = False

        new_transaction = trn.Transaction()
        new_transaction.date_posted = datetime(2019, 7, 28, tzinfo=pytz.timezone('US/Eastern'))
        new_transaction.date_entered = datetime.now(tz=pytz.timezone('US/Eastern'))
        new_transaction.description = 'Unit Test Transaction'

        transaction_manager.add(new_transaction)

        self.assertNotEqual(transaction_manager[0], new_transaction)
        self.assertNotEqual(transaction_manager[-1], new_transaction)

        # Adding one that should be at the end
        end_transaction = trn.Transaction()
        end_transaction.date_posted = datetime(2038, 1, 1, tzinfo=pytz.timezone('US/Eastern'))
        end_transaction.date_entered = datetime.now(tz=pytz.timezone('US/Eastern'))
        end_transaction.description = 'Unit Test Transaction'

        transaction_manager.add(end_transaction)

        self.assertEqual(transaction_manager[-1], end_transaction)

    def test_delete_transaction(self):
        gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
        book = gnucash_file.books[0]
        transaction_manager = book.transactions

        first_transaction = transaction_manager[0]
        transaction_manager.delete(first_transaction)

        self.assertNotEqual(transaction_manager[0], first_transaction)

    def test_get_transactions(self):
        gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
        book = gnucash_file.books[0]
        transaction_manager = book.transactions
        checking_account = book.get_account('Assets', 'Current Assets', 'Checking Account')

        transactions = list(transaction_manager.get_transactions(checking_account))
        self.assertGreater(len(transactions), 0)
        self.assertLess(len(transactions), len(transaction_manager))

    def test_get_account_starting_balance(self):
        gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
        book = gnucash_file.books[0]
        transaction_manager = book.transactions
        checking_account = book.get_account('Assets', 'Current Assets', 'Checking Account')

        starting_balance = transaction_manager.get_account_starting_balance(checking_account)
        self.assertEqual(starting_balance, Decimal('2000'))

    def test_get_account_ending_balance(self):
        gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
        book = gnucash_file.books[0]
        transaction_manager = book.transactions
        checking_account = book.get_account('Assets', 'Current Assets', 'Checking Account')

        ending_balance = transaction_manager.get_account_ending_balance(checking_account)
        self.assertEqual(ending_balance, Decimal('1240'))

    def test_minimum_balance_past_date(self):
        gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
        book = gnucash_file.books[0]
        transaction_manager = book.transactions
        checking_account = book.get_account('Assets', 'Current Assets', 'Checking Account')

        minimum_balance, minimum_balance_date = transaction_manager.minimum_balance_past_date(
            checking_account, datetime(2019, 12, 1, tzinfo=pytz.timezone('US/Eastern'))
        )
        minimum_balance_date = minimum_balance_date.replace(tzinfo=None)
        self.assertEqual(minimum_balance, Decimal('1240'))
        self.assertEqual(minimum_balance_date, datetime(2019, 12, 31, 5, 59, 0, 0))

    def test_get_balance_at_date(self):
        gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
        book = gnucash_file.books[0]
        transaction_manager = book.transactions
        checking_account = book.get_account('Assets', 'Current Assets', 'Checking Account')

        test_date = datetime(2019, 7, 28, tzinfo=pytz.timezone('US/Eastern'))
        balance_at_date = transaction_manager.get_balance_at_date(checking_account, test_date)

        self.assertEqual(balance_at_date, Decimal('2620'))

    def test_transaction_notes(self):
        test_transaction = trn.Transaction()
        self.assertEqual(len(test_transaction.slots), 0)
        self.assertIsNone(test_transaction.notes)

        test_transaction.notes = 'This is a unit test note'
        self.assertEqual(len(test_transaction.slots), 1)
        self.assertEqual(test_transaction.slots[0].key, 'notes')
        self.assertEqual(test_transaction.slots[0].value, 'This is a unit test note')
        self.assertEqual(test_transaction.slots[0].type, 'string')

        self.assertEqual(test_transaction.notes, 'This is a unit test note')

        test_transaction.notes = 'This is another unit test note'
        self.assertEqual(len(test_transaction.slots), 1)
        self.assertEqual(test_transaction.slots[0].key, 'notes')
        self.assertEqual(test_transaction.slots[0].value, 'This is another unit test note')
        self.assertEqual(test_transaction.slots[0].type, 'string')

        test_transaction = trn.Transaction()
        test_transaction.reversed_by = 'test123456'
        self.assertIsNone(test_transaction.notes)

    def test_transaction_reversed_by(self):
        test_transaction = trn.Transaction()
        self.assertEqual(len(test_transaction.slots), 0)
        self.assertIsNone(test_transaction.reversed_by)

        test_transaction.reversed_by = 'test12345'
        self.assertEqual(len(test_transaction.slots), 1)
        self.assertEqual(test_transaction.slots[0].key, 'reversed-by')
        self.assertEqual(test_transaction.slots[0].value, 'test12345')
        self.assertEqual(test_transaction.slots[0].type, 'guid')

        self.assertEqual(test_transaction.reversed_by, 'test12345')

        test_transaction.reversed_by = 'test23456'
        self.assertEqual(len(test_transaction.slots), 1)
        self.assertEqual(test_transaction.slots[0].key, 'reversed-by')
        self.assertEqual(test_transaction.slots[0].value, 'test23456')
        self.assertEqual(test_transaction.slots[0].type, 'guid')

        test_transaction = trn.Transaction()
        test_transaction.notes = 'This is a test'
        self.assertIsNone(test_transaction.reversed_by)

    def test_transaction_voided(self):
        test_transaction = trn.Transaction()
        self.assertEqual(len(test_transaction.slots), 0)
        self.assertIsNone(test_transaction.voided)

        test_transaction.voided = 'test12345'
        self.assertEqual(len(test_transaction.slots), 1)
        self.assertEqual(test_transaction.slots[0].key, 'trans-read-only')
        self.assertEqual(test_transaction.slots[0].value, 'test12345')
        self.assertEqual(test_transaction.slots[0].type, 'string')

        self.assertEqual(test_transaction.voided, 'test12345')

        test_transaction.voided = 'test23456'
        self.assertEqual(len(test_transaction.slots), 1)
        self.assertEqual(test_transaction.slots[0].key, 'trans-read-only')
        self.assertEqual(test_transaction.slots[0].value, 'test23456')
        self.assertEqual(test_transaction.slots[0].type, 'string')

        test_transaction = trn.Transaction()
        test_transaction.notes = 'This is a test'
        self.assertIsNone(test_transaction.voided)

    def test_transaction_void_time(self):
        test_transaction = trn.Transaction()
        self.assertEqual(len(test_transaction.slots), 0)
        self.assertIsNone(test_transaction.void_time)

        test_transaction.void_time = 'test12345'
        self.assertEqual(len(test_transaction.slots), 1)
        self.assertEqual(test_transaction.slots[0].key, 'void-time')
        self.assertEqual(test_transaction.slots[0].value, 'test12345')
        self.assertEqual(test_transaction.slots[0].type, 'string')

        self.assertEqual(test_transaction.void_time, 'test12345')

        test_transaction.void_time = 'test23456'
        self.assertEqual(len(test_transaction.slots), 1)
        self.assertEqual(test_transaction.slots[0].key, 'void-time')
        self.assertEqual(test_transaction.slots[0].value, 'test23456')
        self.assertEqual(test_transaction.slots[0].type, 'string')

        test_transaction = trn.Transaction()
        test_transaction.notes = 'This is a test'
        self.assertIsNone(test_transaction.void_time)

    def test_transaction_void_reason(self):
        test_transaction = trn.Transaction()
        self.assertEqual(len(test_transaction.slots), 0)
        self.assertIsNone(test_transaction.void_reason)

        test_transaction.void_reason = 'test12345'
        self.assertEqual(len(test_transaction.slots), 1)
        self.assertEqual(test_transaction.slots[0].key, 'void-reason')
        self.assertEqual(test_transaction.slots[0].value, 'test12345')
        self.assertEqual(test_transaction.slots[0].type, 'string')

        self.assertEqual(test_transaction.void_reason, 'test12345')

        test_transaction.void_reason = 'test23456'
        self.assertEqual(len(test_transaction.slots), 1)
        self.assertEqual(test_transaction.slots[0].key, 'void-reason')
        self.assertEqual(test_transaction.slots[0].value, 'test23456')
        self.assertEqual(test_transaction.slots[0].type, 'string')

        test_transaction = trn.Transaction()
        test_transaction.notes = 'This is a test'
        self.assertIsNone(test_transaction.void_reason)

    def test_transaction_associated_uri(self):
        test_transaction = trn.Transaction()
        self.assertEqual(len(test_transaction.slots), 0)
        self.assertIsNone(test_transaction.associated_uri)

        test_transaction.associated_uri = 'https://www.google.com'
        self.assertEqual(len(test_transaction.slots), 1)
        self.assertEqual(test_transaction.slots[0].key, 'assoc_uri')
        self.assertEqual(test_transaction.slots[0].value, 'https://www.google.com')
        self.assertEqual(test_transaction.slots[0].type, 'string')

        self.assertEqual(test_transaction.associated_uri, 'https://www.google.com')

        test_transaction.associated_uri = 'https://www.microsoft.com'
        self.assertEqual(len(test_transaction.slots), 1)
        self.assertEqual(test_transaction.slots[0].key, 'assoc_uri')
        self.assertEqual(test_transaction.slots[0].value, 'https://www.microsoft.com')
        self.assertEqual(test_transaction.slots[0].type, 'string')

        test_transaction = trn.Transaction()
        test_transaction.notes = 'This is a test'
        self.assertIsNone(test_transaction.associated_uri)


class TestSimpleTransaction(unittest.TestCase):
    def test_create_transaction(self):
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

        self.assertEqual(test_transaction.from_account, test_from_account)
        self.assertEqual(test_transaction.to_account, test_to_account)
        self.assertEqual(test_transaction.amount, Decimal('60.00'))
        self.assertEqual(len(test_transaction.splits), 2)
        self.assertEqual(test_transaction.splits[0].account, test_from_account)
        self.assertEqual(test_transaction.splits[0].amount, Decimal('-60.00'))
        self.assertEqual(test_transaction.splits[1].account, test_to_account)
        self.assertEqual(test_transaction.splits[1].amount, Decimal('60.00'))
