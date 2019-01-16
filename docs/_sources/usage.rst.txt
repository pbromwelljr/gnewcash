Using GNewCash
**************

GnuCashFile
-----------

`GnuCashFile <gnucash_file.html>`__ is responsible for reading data from and writing data to GnuCash files.

To read a GnuCash file:

.. code:: python

    from gnewcash import GnuCashFile
    my_file = GnuCashFile.read_file('/path/to/my/file.gnucash')

To write a GnuCash file (recommend backing up beforehand if overwriting an existing file):

.. code:: python

    from gnewcash import GnuCashFile, Book
    my_book = Book()
    my_file = GnuCashFile([my_book])
    my_file.build_file('/path/to/my/file.gnucash')

The build_file function accepts two arguments to modify how the file is written: :code:`prettify_xml` and :code:`use_gzip`. Both options are turned off by default.

- :code:`prettify_xml` will prettify the XML before writing to disk. Helpful if the XML is to be reviewed on disk.
- :code:`use_gzip` will write the file to disk using GZip compression (GnuCash's default).


Book
----

`Book <gnucash_file.html#gnucash_file.Book>`__ is a GnuCash entry that contains transactions, accounts, and their associated commodity.

When you read an existing GnuCash file, the book object(s) are automatically generated from the XML. To create a book object:

.. code:: python

    from gnewcash import Book, Account, AccountType, TransactionManager, Commodity
    my_root_account = Account()
    my_root_account.type = AccountType.ROOT
    my_commodity = Commodity('USD', 'ISO4217')
    my_transaction_manager = TransactionManager()
    my_book = Book(root_account=my_root_account, transactions=my_transaction_manager, commodities=[my_commodity])


Commodity
---------

`Commodity <commodity.html>`__ is a GnuCash entry that defines the type of currency used for the book/account/transaction.

You can find more information on commodities and their implementations `here <https://code.gnucash.org/docs/MAINT/group__Commodity.html>`__.

There is a long list of available commodities in GnuCash. Implementing each one isn't practical, so I'd recommend opening an uncompressed GnuCash file and view which commodity you're using in the XML.

Here's an example:

.. code-block:: xml

    <gnc:commodity version="2.0.0">
      <cmdty:space>ISO4217</cmdty:space>
      <cmdty:id>USD</cmdty:id>
      <cmdty:get_quotes/>
      <cmdty:quote_source>currency</cmdty:quote_source>
      <cmdty:quote_tz/>
    </gnc:commodity>


Account
-------

`Account <account.html>`__ is a GnuCash entry that's best described from the `GnuCash documentation itself <https://www.gnucash.org/docs/v3/C/gnucash-guide/accts-types1.html>`__.

It's essentially a "bucket" that you can assign transaction splits to. Accounts can also have sub-accounts.

Retrieving Accounts
~~~~~~~~~~~~~~~~~~~

When you read in an existing GnuCash file, the accounts and their subaccounts are loaded into the :code:`root_account` property of the Book.
You can retrieve subaccounts by either accessing the :code:`children` property of the root account (not recommended) or using the
:code:`get_account` method on the Book object (recommended).

Using :code:`get_account` is pretty straightforward. Each account name from the root account should be an argument to :code:`get_account`.

For example, if your hierarchy structure in GnuCash is:

- Root Account
    - Assets
        - Current Assets
            - Checking Account
            - Credit Card
    - Expenses
        - Bills
            - Rent
            - Phone

And you want to get the "Checking Account" account, this call will retrieve it for you:

.. code:: python

    checking_account = my_book.get_account('Assets', 'Current Assets', 'Checking Account')


Creating Accounts
~~~~~~~~~~~~~~~~~

There isn't a default "loader" for accounts, as everyone's requirements (or preferences) are different. To create it purely in code, you'd do the following:


.. code:: python

    from gnewcash import Account, AccountType
    my_root_account = Account()
    my_root_account.type = AccountType.ROOT

    assets_account = Account()
    assets_account.type = AccountType.ASSET
    assets_account.name = 'Assets'
    assets_account.parent = my_root_account

    current_assets_account = Account()
    current_assets_account.type = AccountType.ASSET
    current_assets_account.name = 'Current Assets'
    current_assets_account.parent = assets_account

    checking_account = Account()
    checking_account.type = AccountType.BANK
    checking_account.name = 'Checking Account'
    checking_account.parent = current_assets_account

    credit_card_account = Account()
    credit_card_account.type = AccountType.CREDIT
    credit_card_account.name = 'Credit Card'
    credit_card_account.parent = current_assets_account

As you can tell, the code above is unwieldy.
GNewCash does support `shortcut accounts <account.html#shortcut-accounts>`__ that cuts down on the lines of code. Here's the same example using shortcut accounts.

.. code:: python

    from gnewcash import Account, AccountType, AssetAccount, BankAccount, CreditAccount
    my_root_account = Account()
    my_root_account.type = AccountType.ROOT

    assets_account = AssetAccount()
    assets_account.name = 'Assets'
    assets_account.parent = my_root_account

    current_assets_account = AssetAccount()
    current_assets_account.name = 'Current Assets'
    current_assets_account.parent = assets_account

    checking_account = BankAccount()
    checking_account.name = 'Checking Account'
    checking_account.parent = current_assets_account

    credit_card_account = CreditAccount()
    credit_card_account.name = 'Credit Card'
    credit_card_account.parent = current_assets_account

Better, but still a bit much. Here's a JSON loader I wrote for personal usage:

.. code:: python

    import json

    from gnewcash import Account, BankAccount, IncomeAccount, AssetAccount, CreditAccount, ExpenseAccount, EquityAccount, LiabilityAccount

    def load_accounts_from_json(json_file):
        with open(json_file, 'r') as account_data_file:
            account_data = json.load(account_data_file)

        accounts = load_account_and_subaccounts(account_data)
        return accounts


    def load_account_and_subaccounts(account_object, account_parent=None, current_path=None):
        account_lookup = dict()
        account_class = get_account_type(account_object['type'])

        account_class_object = account_class()
        if account_object['type'].upper() == 'ROOT':
            account_class_object.type = AccountType.ROOT
        else:
            account_class_object.name = account_object['name']
            account_class_object.parent = account_parent
        if not current_path:
            account_lookup['/'] = account_class_object
        else:
            account_lookup[current_path + account_object['path']] = account_class_object

        for account in account_object['subaccounts']:
            if not current_path:
                account_lookup.update(load_account_and_subaccounts(account, account_class_object, '/'))
            else:
                account_lookup.update(load_account_and_subaccounts(account, account_class_object, current_path +
                                                                   account_object['path'] + '/'))
        return account_lookup

    def get_account_type(account_type_string):
        account_type_mapping = {
            'ROOT': Account,
            'BANK': BankAccount,
            'INCOME': IncomeAccount,
            'ASSET': AssetAccount,
            'CREDIT': CreditAccount,
            'EXPENSE': ExpenseAccount,
            'EQUITY': EquityAccount,
            'LIABILITY': LiabilityAccount
        }
        return account_type_mapping[account_type_string]

Passing in a JSON file into :code:`load_accounts_from_json` with this structure:

.. code-block:: json

    {
      "name": "Root Account",
      "path": "",
      "type": "ROOT",
      "subaccounts": [
        {
          "name": "Expenses",
          "path": "expenses",
          "type": "EXPENSE",
          "subaccounts": [
             {
              "name": "Bills",
              "path": "bills",
              "type": "EXPENSE",
              "subaccounts": [
                {
                  "name": "Rent",
                  "path": "rent",
                  "type": "EXPENSE",
                  "subaccounts": []
                },
                {
                  "name": "Phone",
                  "path": "phone",
                  "type": "EXPENSE",
                  "subaccounts": []
                }
              ]
            }
          ]
        },
        {
          "name": "Assets",
          "path": "assets",
          "type": "ASSET",
          "subaccounts": [
            {
              "name": "Current Assets",
              "path": "current_assets",
              "type": "ASSET",
              "subaccounts": [
                {
                  "name": "Checking Account",
                  "path": "checking_account",
                  "type": "BANK",
                  "subaccounts": []
                },
                {
                  "name": "Credit Card",
                  "path": "credit_card",
                  "type": "CREDIT",
                  "subaccounts": []
                }
              ]
            }
          ]
        }
      ]
    }

Will yield the following :code:`dict`:

.. code:: python

    {
        '/': root_account,
        '/assets': assets_account,
        '/assets/current_assets': current_assets_account,
        '/assets/current_assets/checking_account': checking_account,
        '/assets/current_assets/credit_card': credit_card_account,
        '/expenses': expenses_account,
        '/expenses/bills': bills_account,
        '/expenses/bills/rent': rent_account,
        '/expenses/bills/phone': phone_account
    }

Feel free to use or modify that for your own usage!


Interest Accounts
~~~~~~~~~~~~~~~~~

Interest accounts are `special accounts <account.html#special-accounts>`__ that actually aren't used inside GnuCash.
Trying to add one of the special accounts to a GnuCash file would result in an error.

The purpose of an interest account is to calculate balances and payment schedules for loans that accumulate interest.

Here's the general usage of an interest account:

.. code:: python

    from datetime import datetime
    from decimal import Decimal

    from gnewcash import InterestAccount

    my_loan = InterestAccount(starting_balance=Decimal('1000'),
                              starting_date=datetime(2019, 1, 1),
                              interest_percentage=Decimal('0.05'),  # 5% APR
                              payment_amount=Decimal('50'))
    my_loan.get_info_at_date(datetime(2019, 7, 1))

    # LoanStatus(iterator_balance=Decimal('722.15'), iterator_date=datetime.datetime(2019, 7, 1, 0, 0), interest=Decimal('3.21'), amount_to_capital=Decimal('46.79'))

    my_loan.get_all_payments()

    # Probably should be converted to a namedtuple, but fields are: date, balance before payment, amount to principal
    # [(datetime.datetime(2019, 2, 1, 0, 0), Decimal('1000'), Decimal('45.83')),
    #  (datetime.datetime(2019, 3, 1, 0, 0), Decimal('954.17'), Decimal('46.02')),
    #  (datetime.datetime(2019, 4, 1, 0, 0), Decimal('908.15'), Decimal('46.21')),
    #  (datetime.datetime(2019, 5, 1, 0, 0), Decimal('861.94'), Decimal('46.40')),
    #  (datetime.datetime(2019, 6, 1, 0, 0), Decimal('815.54'), Decimal('46.60')),
    #  (datetime.datetime(2019, 7, 1, 0, 0), Decimal('768.94'), Decimal('46.79')),
    #  (datetime.datetime(2019, 8, 1, 0, 0), Decimal('722.15'), Decimal('46.99')),
    #  (datetime.datetime(2019, 9, 1, 0, 0), Decimal('675.16'), Decimal('47.18')),
    #  (datetime.datetime(2019, 10, 1, 0, 0), Decimal('627.98'), Decimal('47.38')),
    #  (datetime.datetime(2019, 11, 1, 0, 0), Decimal('580.60'), Decimal('47.58')),
    #  (datetime.datetime(2019, 12, 1, 0, 0), Decimal('533.02'), Decimal('47.77')),
    #  (datetime.datetime(2020, 1, 1, 0, 0), Decimal('485.25'), Decimal('47.97')),
    #  (datetime.datetime(2020, 2, 1, 0, 0), Decimal('437.28'), Decimal('48.17')),
    #  (datetime.datetime(2020, 3, 1, 0, 0), Decimal('389.11'), Decimal('48.37')),
    #  (datetime.datetime(2020, 4, 1, 0, 0), Decimal('340.74'), Decimal('48.58')),
    #  (datetime.datetime(2020, 5, 1, 0, 0), Decimal('292.16'), Decimal('48.78')),
    #  (datetime.datetime(2020, 6, 1, 0, 0), Decimal('243.38'), Decimal('48.98')),
    #  (datetime.datetime(2020, 7, 1, 0, 0), Decimal('194.40'), Decimal('49.18')),
    #  (datetime.datetime(2020, 8, 1, 0, 0), Decimal('145.22'), Decimal('49.39')),
    #  (datetime.datetime(2020, 9, 1, 0, 0), Decimal('95.83'), Decimal('49.60')),
    #  (datetime.datetime(2020, 10, 1, 0, 0), Decimal('46.23'), Decimal('49.80'))]

Interest accounts also take the following constructor parameters:

- :code:`additional_payments`
    List of dictionaries containing the following key-value pairs:

    Note: Additional payments are assumed to have no interest collected on them.

    - :code:`amount`: Dollar amount for the additional payment (Decimal)
    - :code:`payment_date`: Date of the additional payment (datetime)
- :code:`skip_payment_dates`
    List of :code:`datetime` objects for dates that payments should be skipped.
- :code:`interest_start_date`
    :code:`datetime` object that designates when interest starts incurring on the loan.
- :code:`subaccounts`
    List of InterestAccount objects that make up the parent interest account.
    This is helpful for things like school loans where your overall loan is comprised of multiple small loans.
    When setting up subaccounts, pass :code:`None` for :code:`starting_balance`, :code:`starting_date`,
    :code:`interest_percentage`, and :code:`payment_amount` in the parent InterestAccount. When accessing those fields,
    they will be derived from their child accounts' information.

Transaction
-----------

`Transaction <transaction.html>`__ is a GnuCash object that represents a real-world transaction; for example, a credit/debit card purchase or a money transfer.

Transactions contain `Splits <transaction.html#transaction.Split>`__ that indicate how much money was added or removed from a particular account for the transaction.
You can find more information on splits `here <https://www.gnucash.org/docs/v3/C/gnucash-guide/txns-registers-txntypes.html>`__.

By default, all transactions in GNewCash are "split transactions", although there are plans to add a SimpleTransaction class for easier usage.

Retrieving Transactions
~~~~~~~~~~~~~~~~~~~~~~~

When you load an existing GnuCash file via the :code:`GnuCashFile.read_file` method, the transactions in the document are
loaded into a `TransactionManager object <transaction.html#transaction.TransactionManager>`__. You can retrieve transactions
for a given account like so:

.. code:: python

    my_file = GnuCashFile.read_file('/path/to/my/file.gnucash')
    my_book = my_file.books[0]
    checking_account = my_book.get_account('Assets', 'Current Assets', 'Checking Account')
    checking_transactions = list(my_book.transactions.get_transactions(checking_account))

:code:`get_transactions` returns a generator, so you can iterate over transactions in a memory-efficient way.

Creating Transactions
~~~~~~~~~~~~~~~~~~~~~

Like accounts, transactions can be unwieldy without some sort of loader (which depends on your implementation).

Creating a transaction can be done like so:

.. code:: python

    from datetime import datetime
    from decimal import Decimal

    from gnewcash import Transaction, Split

    from pytz import timezone


    my_new_transaction = Transaction()

    # Date that the transaction takes place
    my_new_transaction.date_posted = datetime(2019, 7, 5, 0, 0, 0, 0, tzinfo=timezone('US/Eastern'))

    # Date that the transaction was created
    my_new_transaction.date_entered = datetime.now(tz=timezone('US/Eastern'))

    # Description for the transaction
    my_new_transaction.description = 'My First Transaction'

    # Memo for the transaction (appears in the "Num" field in GnuCash)
    my_new_transaction.memo = 'My First Memo'

    # Splits define what amount of money goes where. There should be at least 2 splits in a transaction.
    my_new_transaction.splits = [
        Split(checking_account, Decimal('-50.00')),
        Split(phone_bill, Decimal('50.00')),
    ]

To add your new transaction to the TransactionManager, simply call:

.. code:: python

    my_book.transactions.add(my_new_transaction)

Transactions have an additional property called :code:`cleared`, which returns a :code:`bool` indicating if all splits
are in the "cleared" state.

Transactions also have an additional method called :code:`mark_transaction_cleared`, which sets the :code:`reconciled_state`
of all splits on the transaction to "c" (for cleared).

For more information on reconciliation states, please see the `GnuCash documentation <https://www.gnucash.org/docs/v3/C/gnucash-help/trans-stts.html>`__.


Creating Transactions (Simplified)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As of version 1.0.2, GNewCash provides a class called `SimpleTransaction <transaction.html#transaction.SimpleTransaction>`__.
The purpose of this class is to simplify creating transactions that consist of only two splits: "from" and "to".

When using SimpleTransaction, the code changes to this:

.. code:: python

    from datetime import datetime
    from decimal import Decimal

    from gnewcash import SimpleTransaction

    from pytz import timezone


    my_new_transaction = SimpleTransaction()

    # Date that the transaction takes place
    my_new_transaction.date_posted = datetime(2019, 7, 5, 0, 0, 0, 0, tzinfo=timezone('US/Eastern'))

    # Date that the transaction was created
    my_new_transaction.date_entered = datetime.now(tz=timezone('US/Eastern'))

    # Description for the transaction
    my_new_transaction.description = 'My First Transaction'

    # Memo for the transaction (appears in the "Num" field in GnuCash)
    my_new_transaction.memo = 'My First Memo'

    # Define the dollar amount
    my_new_transaction.amount = Decimal('50.00')

    # Define where it's coming from
    my_new_transaction.from_account = checking_account

    # Define where it's going to
    my_new_transaction.to_account = phone_bill


Transaction Manager
~~~~~~~~~~~~~~~~~~~

The `Transaction Manager <transaction.html#transaction.TransactionManager>`__ is a class used to maintain transactions
in the GnuCash file.

- :code:`add`
    Adds the transaction to the manager. By default, the manager will maintain sort order based on :code:`date_posted`.
    You can disable this functionality by either setting the :code:`disable_sort` property on the manager to
    :code:`False`, or by passing :code:`sort_transactions=False` when calling :code:`GnuCashFile.read_file`. Some
    functions inside GNewCash rely on the transactions being sorted, so be careful when turning this setting off.
- :code:`remove`
    Removes the transaction from the manager. No magic behind the scenes here.
- :code:`get_account_ending_balance`
    Retrieves the final balance for the provided account, based on transactions in the manager.
- :code:`get_account_starting_balance`
    Retrieves the starting balance (dollar amount of first transaction by posted date) for the provided account,
    based on transactions in the manager.
- :code:`get_balance_at_date`
    Retrieves the account balance for the specified account at a certain date. If the provided date is None, it will
    retrieve the ending balance.
- :code:`get_transactions`
    Generator function that retrieves transactions for a specified account. If no account is provided, all transactions
    will be returned by the generator.
- :code:`minimum_balance_past_date`
    Retrieves the minimum balance past a certain date for the given account. It returns a tuple of the date that the
    account is at the minimum balance, and the minimum balance itself.


Questions/Comments/Concerns?
----------------------------

That should be all you need to start using GNewCash. If you have any questions, comments, or concerns with the
documentation or implementation of GNewCash itself, please submit an issue on our `issue tracker <https://github.com/pbromwelljr/gnewcash/issues>`__.

Happy programming!