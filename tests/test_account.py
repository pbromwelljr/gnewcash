from datetime import datetime
from decimal import Decimal
import pytz
import unittest

import gnewcash.gnucash_file as gcf
import gnewcash.account as acc


class TestAccount(unittest.TestCase):
    def test_get_starting_balance(self):
        gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
        book = gnucash_file.books[0]
        account = book.get_account('Assets', 'Current Assets', 'Checking Account')
        self.assertEqual(account.get_starting_balance(book.transactions), 2000)

    def test_get_balance_at_date_checking(self):
        gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
        book = gnucash_file.books[0]
        account = book.get_account('Assets', 'Current Assets', 'Checking Account')
        test_date = datetime(2019, 6, 1, 0, 0, 0, 0, tzinfo=pytz.timezone('US/Eastern'))
        balance_at_date = account.get_balance_at_date(book.transactions, test_date)
        self.assertEqual(balance_at_date, 480)

    def test_get_balance_at_date_credit(self):
        gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
        book = gnucash_file.books[0]
        account = book.get_account('Assets', 'Current Assets', 'Credit Card')
        test_date = datetime(2019, 6, 30, 0, 0, 0, 0, tzinfo=pytz.timezone('US/Eastern'))
        balance_at_date = account.get_balance_at_date(book.transactions, test_date)
        self.assertEqual(balance_at_date, 860)

    def test_minimum_balance_past_date(self):
        gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
        book = gnucash_file.books[0]
        account = book.get_account('Assets', 'Current Assets', 'Checking Account')
        test_date = datetime(2019, 12, 1, 0, 0, 0, 0, tzinfo=pytz.timezone('US/Eastern'))
        minimum_balance, minimum_balance_date = account.minimum_balance_past_date(book.transactions, test_date)
        self.assertEqual(minimum_balance, 1240)
        # Not worried about timezones
        minimum_balance_date = minimum_balance_date.replace(tzinfo=None)
        self.assertEqual(minimum_balance_date, datetime(2019, 12, 31, 5, 59, 0, 0))

    def test_account_shortcut_classes(self):
        ba = acc.BankAccount()
        self.assertEqual(ba.type, acc.AccountType.BANK)

        ia = acc.IncomeAccount()
        self.assertEqual(ia.type, acc.AccountType.INCOME)

        aa = acc.AssetAccount()
        self.assertEqual(aa.type, acc.AccountType.ASSET)

        ca = acc.CreditAccount()
        self.assertEqual(ca.type, acc.AccountType.CREDIT)

        ea = acc.ExpenseAccount()
        self.assertEqual(ea.type, acc.AccountType.EXPENSE)

        eqa = acc.EquityAccount()
        self.assertEqual(eqa.type, acc.AccountType.EQUITY)

        la = acc.LiabilityAccount()
        self.assertEqual(la.type, acc.AccountType.LIABILITY)

    def test_simple_interest_account(self):
        ia = acc.InterestAccount(starting_balance=Decimal('3000'),
                                 starting_date=datetime(2018, 1, 1),
                                 interest_percentage=Decimal('0.05'),
                                 payment_amount=Decimal('100'))
        self.assertEqual(ia.starting_date, datetime(2018, 1, 1))
        self.assertEqual(ia.interest_percentage, Decimal('0.05'))
        self.assertEqual(ia.payment_amount, Decimal('100'))
        self.assertEqual(ia.starting_balance, Decimal('3000'))

        info_date = datetime(2020, 1, 1)
        loan_status = ia.get_info_at_date(info_date)
        self.assertEqual(loan_status.iterator_balance, Decimal('796.36'))
        self.assertEqual(loan_status.iterator_date, info_date)
        self.assertEqual(loan_status.interest, Decimal('3.72'))
        self.assertEqual(loan_status.amount_to_capital, Decimal('96.28'))

        all_payments = ia.get_all_payments()
        actual_payments = [
            (datetime(2018, 2, 1), Decimal('3000'), Decimal('87.5')),
            (datetime(2018, 3, 1), Decimal('2912.5'), Decimal('87.86')),
            (datetime(2018, 4, 1), Decimal('2824.64'), Decimal('88.23')),
            (datetime(2018, 5, 1), Decimal('2736.41'), Decimal('88.59')),
            (datetime(2018, 6, 1), Decimal('2647.82'), Decimal('88.96')),
            (datetime(2018, 7, 1), Decimal('2558.86'), Decimal('89.33')),
            (datetime(2018, 8, 1), Decimal('2469.53'), Decimal('89.71')),
            (datetime(2018, 9, 1), Decimal('2379.82'), Decimal('90.08')),
            (datetime(2018, 10, 1), Decimal('2289.74'), Decimal('90.45')),
            (datetime(2018, 11, 1), Decimal('2199.29'), Decimal('90.83')),
            (datetime(2018, 12, 1), Decimal('2108.46'), Decimal('91.21')),
            (datetime(2019, 1, 1), Decimal('2017.25'), Decimal('91.59')),
            (datetime(2019, 2, 1), Decimal('1925.66'), Decimal('91.97')),
            (datetime(2019, 3, 1), Decimal('1833.69'), Decimal('92.35')),
            (datetime(2019, 4, 1), Decimal('1741.34'), Decimal('92.74')),
            (datetime(2019, 5, 1), Decimal('1648.6'), Decimal('93.13')),
            (datetime(2019, 6, 1), Decimal('1555.47'), Decimal('93.51')),
            (datetime(2019, 7, 1), Decimal('1461.96'), Decimal('93.9')),
            (datetime(2019, 8, 1), Decimal('1368.06'), Decimal('94.29')),
            (datetime(2019, 9, 1), Decimal('1273.77'), Decimal('94.69')),
            (datetime(2019, 10, 1), Decimal('1179.08'), Decimal('95.08')),
            (datetime(2019, 11, 1), Decimal('1084'), Decimal('95.48')),
            (datetime(2019, 12, 1), Decimal('988.52'), Decimal('95.88')),
            (datetime(2020, 1, 1), Decimal('892.64'), Decimal('96.28')),
            (datetime(2020, 2, 1), Decimal('796.36'), Decimal('96.68')),
            (datetime(2020, 3, 1), Decimal('699.68'), Decimal('97.08')),
            (datetime(2020, 4, 1), Decimal('602.6'), Decimal('97.48')),
            (datetime(2020, 5, 1), Decimal('505.12'), Decimal('97.89')),
            (datetime(2020, 6, 1), Decimal('407.23'), Decimal('98.3')),
            (datetime(2020, 7, 1), Decimal('308.93'), Decimal('98.71')),
            (datetime(2020, 8, 1), Decimal('210.22'), Decimal('99.12')),
            (datetime(2020, 9, 1), Decimal('111.1'), Decimal('99.53')),
            (datetime(2020, 10, 1), Decimal('11.57'), Decimal('99.95')),
        ]
        for payment, actual_payment in zip(all_payments, actual_payments):
            payment_date, payment_balance, payment_capital = payment
            actual_date, actual_balance, actual_capital = actual_payment
            self.assertEqual(payment_date, actual_date)
            self.assertEqual(payment_balance, actual_balance)
            self.assertEqual(payment_capital, actual_capital)
