import unittest

import gnewcash.gnucash_file as gcf


class TestAccount(unittest.TestCase):
    def test_get_starting_balance(self):
        gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
        book = gnucash_file.books[0]
        account = book.get_account('Assets', 'Current Assets', 'Checking Account')
        self.assertEqual(account.get_starting_balance(book.transactions), 2000)
