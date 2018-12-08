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

    def test_get_ending_balance_checking(self):
        gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
        book = gnucash_file.books[0]
        account = book.get_account('Assets', 'Current Assets', 'Checking Account')
        ending_balance = account.get_ending_balance(book.transactions)
        self.assertEqual(ending_balance, Decimal('1240'))

    def test_get_ending_balance_credit_card(self):
        gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
        book = gnucash_file.books[0]
        account = book.get_account('Assets', 'Current Assets', 'Credit Card')
        ending_balance = account.get_ending_balance(book.transactions)
        self.assertEqual(ending_balance, Decimal('0'))

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

    def test_interest_account_with_subaccounts(self):
        subaccount_1 = acc.InterestAccount(starting_balance=Decimal('1000'),
                                           starting_date=datetime(2018, 1, 1),
                                           interest_percentage=Decimal('0.05'),
                                           payment_amount=Decimal('100'))
        subaccount_2 = acc.InterestAccount(starting_balance=Decimal('3000'),
                                           starting_date=datetime(2018, 1, 1),
                                           interest_percentage=Decimal('0.02'),
                                           payment_amount=Decimal('50'))
        interest_account = acc.InterestAccount(starting_balance=None,
                                               starting_date=None,
                                               interest_percentage=None,
                                               payment_amount=None,
                                               subaccounts=[subaccount_1, subaccount_2])
        self.assertEqual(interest_account.starting_date, datetime(2018, 1, 1))
        self.assertEqual(interest_account.interest_percentage, Decimal('0.07'))
        self.assertEqual(interest_account.payment_amount, Decimal('150'))
        self.assertEqual(interest_account.starting_balance, Decimal('4000'))

        # Testing date where one is paid off already
        info_date = datetime(2020, 1, 1)
        loan_status = interest_account.get_info_at_date(info_date)
        self.assertEqual(loan_status.iterator_balance, Decimal('1899.17'))
        self.assertEqual(loan_status.iterator_date, info_date)
        self.assertEqual(loan_status.interest, Decimal('3.25'))
        self.assertEqual(loan_status.amount_to_capital, Decimal('46.75'))

        # Testing date where both are being paid on
        info_date = datetime(2018, 7, 1)
        loan_status = interest_account.get_info_at_date(info_date)
        self.assertEqual(loan_status.iterator_balance, Decimal('3147.90'))
        self.assertEqual(loan_status.iterator_date, info_date)
        self.assertEqual(loan_status.interest, Decimal('6.79'))
        self.assertEqual(loan_status.amount_to_capital, Decimal('143.21'))

        actual_payments = [
            (datetime(2018, 2, 1), Decimal('4000'), Decimal('140.82')),
            (datetime(2018, 3, 1), Decimal('3859.18'), Decimal('141.3')),
            (datetime(2018, 4, 1), Decimal('3717.88'), Decimal('141.78')),
            (datetime(2018, 5, 1), Decimal('3576.10'), Decimal('142.25')),
            (datetime(2018, 6, 1), Decimal('3433.85'), Decimal('142.74')),
            (datetime(2018, 7, 1), Decimal('3291.11'), Decimal('143.21')),
            (datetime(2018, 8, 1), Decimal('3147.90'), Decimal('143.7')),
            (datetime(2018, 9, 1), Decimal('3004.20'), Decimal('144.18')),
            (datetime(2018, 10, 1), Decimal('2860.02'), Decimal('144.67')),
            (datetime(2018, 11, 1), Decimal('2715.35'), Decimal('145.15')),
            (datetime(2018, 12, 1), Decimal('2570.20'), Decimal('145.65')),
            (datetime(2019, 1, 1), Decimal('2500.91'), Decimal('45.83')),
            (datetime(2019, 2, 1), Decimal('2455.08'), Decimal('45.9')),
            (datetime(2019, 3, 1), Decimal('2409.18'), Decimal('45.98')),
            (datetime(2019, 4, 1), Decimal('2363.20'), Decimal('46.06')),
            (datetime(2019, 5, 1), Decimal('2317.14'), Decimal('46.13')),
            (datetime(2019, 6, 1), Decimal('2271.01'), Decimal('46.21')),
            (datetime(2019, 7, 1), Decimal('2224.80'), Decimal('46.29')),
            (datetime(2019, 8, 1), Decimal('2178.51'), Decimal('46.36')),
            (datetime(2019, 9, 1), Decimal('2132.15'), Decimal('46.44')),
            (datetime(2019, 10, 1), Decimal('2085.71'), Decimal('46.52')),
            (datetime(2019, 11, 1), Decimal('2039.19'), Decimal('46.6')),
            (datetime(2019, 12, 1), Decimal('1992.59'), Decimal('46.67')),
            (datetime(2020, 1, 1), Decimal('1945.92'), Decimal('46.75')),
            (datetime(2020, 2, 1), Decimal('1899.17'), Decimal('46.83')),
            (datetime(2020, 3, 1), Decimal('1852.34'), Decimal('46.91')),
            (datetime(2020, 4, 1), Decimal('1805.43'), Decimal('46.99')),
            (datetime(2020, 5, 1), Decimal('1758.44'), Decimal('47.06')),
            (datetime(2020, 6, 1), Decimal('1711.38'), Decimal('47.14')),
            (datetime(2020, 7, 1), Decimal('1664.24'), Decimal('47.22')),
            (datetime(2020, 8, 1), Decimal('1617.02'), Decimal('47.3')),
            (datetime(2020, 9, 1), Decimal('1569.72'), Decimal('47.38')),
            (datetime(2020, 10, 1), Decimal('1522.34'), Decimal('47.46')),
            (datetime(2020, 11, 1), Decimal('1474.88'), Decimal('47.54')),
            (datetime(2020, 12, 1), Decimal('1427.34'), Decimal('47.62')),
            (datetime(2021, 1, 1), Decimal('1379.72'), Decimal('47.7')),
            (datetime(2021, 2, 1), Decimal('1332.02'), Decimal('47.77')),
            (datetime(2021, 3, 1), Decimal('1284.25'), Decimal('47.85')),
            (datetime(2021, 4, 1), Decimal('1236.40'), Decimal('47.93')),
            (datetime(2021, 5, 1), Decimal('1188.47'), Decimal('48.01')),
            (datetime(2021, 6, 1), Decimal('1140.46'), Decimal('48.09')),
            (datetime(2021, 7, 1), Decimal('1092.37'), Decimal('48.17')),
            (datetime(2021, 8, 1), Decimal('1044.20'), Decimal('48.25')),
            (datetime(2021, 9, 1), Decimal('995.95'), Decimal('48.34')),
            (datetime(2021, 10, 1), Decimal('947.61'), Decimal('48.42')),
            (datetime(2021, 11, 1), Decimal('899.19'), Decimal('48.5')),
            (datetime(2021, 12, 1), Decimal('850.69'), Decimal('48.58')),
            (datetime(2022, 1, 1), Decimal('802.11'), Decimal('48.66')),
            (datetime(2022, 2, 1), Decimal('753.45'), Decimal('48.74')),
            (datetime(2022, 3, 1), Decimal('704.71'), Decimal('48.82')),
            (datetime(2022, 4, 1), Decimal('655.89'), Decimal('48.9')),
            (datetime(2022, 5, 1), Decimal('606.99'), Decimal('48.98')),
            (datetime(2022, 6, 1), Decimal('558.01'), Decimal('49.07')),
            (datetime(2022, 7, 1), Decimal('508.94'), Decimal('49.15')),
            (datetime(2022, 8, 1), Decimal('459.79'), Decimal('49.23')),
            (datetime(2022, 9, 1), Decimal('410.56'), Decimal('49.31')),
            (datetime(2022, 10, 1), Decimal('361.25'), Decimal('49.39')),
            (datetime(2022, 11, 1), Decimal('311.86'), Decimal('49.48')),
            (datetime(2022, 12, 1), Decimal('262.38'), Decimal('49.56')),
            (datetime(2023, 1, 1), Decimal('212.82'), Decimal('49.64')),
            (datetime(2023, 2, 1), Decimal('163.18'), Decimal('49.72')),
            (datetime(2023, 3, 1), Decimal('113.46'), Decimal('49.81')),
            (datetime(2023, 4, 1), Decimal('63.65'), Decimal('49.89')),
            (datetime(2023, 5, 1), Decimal('13.76'), Decimal('49.97')),
        ]
        all_payments = interest_account.get_all_payments()
        for payment, actual_payment in zip(all_payments, actual_payments):
            payment_date, payment_balance, payment_capital = payment
            actual_date, actual_balance, actual_capital = actual_payment
            self.assertEqual(payment_date, actual_date)
            self.assertEqual(payment_balance, actual_balance)
            self.assertEqual(payment_capital, actual_capital)

    def test_interest_account_skip_and_additional(self):
        ia = acc.InterestAccount(starting_balance=Decimal('3000'),
                                 starting_date=datetime(2018, 1, 1),
                                 interest_percentage=Decimal('5'),  # Interest rates above 1 get divided by 100
                                 payment_amount=Decimal('100'),
                                 skip_payment_dates=[datetime(2018, 7, 1),
                                                     datetime(2019, 7, 1)],
                                 additional_payments=[
                                     {'amount': Decimal(500), 'payment_date': datetime(2018, 9, 20)},
                                     {'amount': Decimal(500), 'payment_date': datetime(2019, 9, 20)}
                                 ])
        # Get the balance after one of our payment skips
        after_skip = ia.get_info_at_date(datetime(2018, 8, 1))
        self.assertEqual(after_skip.iterator_balance, Decimal('2469.53'))
        self.assertEqual(after_skip.iterator_date, datetime(2018, 8, 1))
        self.assertEqual(after_skip.amount_to_capital, Decimal('89.33'))
        self.assertEqual(after_skip.interest, Decimal('10.67'))

        # Get the balance after one of our additional payments
        after_additional = ia.get_info_at_date(datetime(2018, 10, 1))
        self.assertEqual(after_additional.iterator_balance, Decimal('1787.66'))
        self.assertEqual(after_additional.iterator_date, datetime(2018, 10, 1))
        self.assertEqual(after_additional.amount_to_capital, Decimal('92.16'))
        self.assertEqual(after_additional.interest, Decimal('7.84'))

        # Testing get all payments
        all_payments = ia.get_all_payments()
        actual_payments = [
            (datetime(2018, 2, 1), Decimal('3000'), Decimal('87.5')),
            (datetime(2018, 3, 1), Decimal('2912.5'), Decimal('87.86')),
            (datetime(2018, 4, 1), Decimal('2824.64'), Decimal('88.23')),
            (datetime(2018, 5, 1), Decimal('2736.41'), Decimal('88.59')),
            (datetime(2018, 6, 1), Decimal('2647.82'), Decimal('88.96')),
            (datetime(2018, 8, 1), Decimal('2558.86'), Decimal('89.33')),
            (datetime(2018, 9, 1), Decimal('2469.53'), Decimal('89.71')),
            (datetime(2018, 9, 20), Decimal('2379.82'), Decimal('500')),
            (datetime(2018, 10, 1), Decimal('1879.82'), Decimal('92.16')),
            (datetime(2018, 11, 1), Decimal('1787.66'), Decimal('92.55')),
            (datetime(2018, 12, 1), Decimal('1695.11'), Decimal('92.93')),
            (datetime(2019, 1, 1), Decimal('1602.18'), Decimal('93.32')),
            (datetime(2019, 2, 1), Decimal('1508.86'), Decimal('93.71')),
            (datetime(2019, 3, 1), Decimal('1415.15'), Decimal('94.1')),
            (datetime(2019, 4, 1), Decimal('1321.05'), Decimal('94.49')),
            (datetime(2019, 5, 1), Decimal('1226.56'), Decimal('94.88')),
            (datetime(2019, 6, 1), Decimal('1131.68'), Decimal('95.28')),
            (datetime(2019, 8, 1), Decimal('1036.4'), Decimal('95.68')),
            (datetime(2019, 9, 1), Decimal('940.72'), Decimal('96.08')),
            (datetime(2019, 9, 20), Decimal('844.64'), Decimal('500')),
            (datetime(2019, 10, 1), Decimal('344.64'), Decimal('98.56')),
            (datetime(2019, 11, 1), Decimal('246.08'), Decimal('98.97')),
            (datetime(2019, 12, 1), Decimal('147.11'), Decimal('99.38')),
            (datetime(2020, 1, 1), Decimal('47.73'), Decimal('99.8')),
        ]
        for payment, actual_payment in zip(all_payments, actual_payments):
            payment_date, payment_balance, payment_capital = payment
            actual_date, actual_balance, actual_capital = actual_payment
            self.assertEqual(payment_date, actual_date)
            self.assertEqual(payment_balance, actual_balance)
            self.assertEqual(payment_capital, actual_capital)

    def test_interest_account_delayed_interest_start(self):
        ia = acc.InterestAccount(starting_balance=Decimal('3000'),
                                 starting_date=datetime(2018, 1, 1),
                                 interest_percentage=Decimal('0.05'),
                                 payment_amount=Decimal('100'),
                                 interest_start_date=datetime(2019, 1, 1))

        # Get the balance before our interest kicks in
        before_interest = ia.get_info_at_date(datetime(2018, 7, 1))
        self.assertEqual(before_interest.iterator_balance, Decimal('2400'))
        self.assertEqual(before_interest.iterator_date, datetime(2018, 7, 1))
        self.assertEqual(before_interest.amount_to_capital, Decimal('100'))
        self.assertEqual(before_interest.interest, Decimal('0'))

        # Get the balance after our interest kicks in
        after_interest = ia.get_info_at_date(datetime(2019, 7, 1))
        self.assertEqual(after_interest.iterator_balance, Decimal('1247.35'))
        self.assertEqual(after_interest.iterator_date, datetime(2019, 7, 1))
        self.assertEqual(after_interest.amount_to_capital, Decimal('94.4'))
        self.assertEqual(after_interest.interest, Decimal('5.6'))
