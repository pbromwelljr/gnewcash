Versions
********

- 1.1.1 (July 24, 2020)
    - Bugfixes
- 1.1.0 (May 4, 2020)
    - **BREAKING CHANGE**: Only Python 3.6+ supported in favor of variable-level typing.
    - **BREAKING CHANGE**: as_xml and from_xml have been removed from most classes.
    - **BREAKING CHANGE**: AccountType moved to new `enum <enums.html>`__ module.
    - **BREAKING CHANGE**: get_starting_balance, get_balance_at_date, get_ending_balance, and minimum_balance_past_date have been removed from the Account class. Please use the methods in the `TransactionManager <transaction.html#transaction.TransactionManager>`__.
    - **BREAKING CHANGE**: Subaccount support has been removed from `InterestAccount <account.html#account.InterestAccount>`__. Please use `InterestAccountWithSubaccounts <account.InterestAccountWithSubaccounts>`__ instead in those situations.
    - **BREAKING CHANGE**: Book class's `build_file <gnucash_file.html#gnucash_file.GnuCashFile.build_file>`__ and `read_file <gnucash_file.html#gnucash_file.GnuCashFile.read_file>`__ now require the "file_format" parameter. This should be an object that extends the BaseFileFormat class. See `XMLFileFormat <file_formats.html#file_formats.xml.XMLFileFormat>`__, `GZipXMLFileFormat <file_formats.html#file_formats.xml.GZipXMLFileFormat>`__, and `SqliteFileFormat <file_formats.html#file_formats.sqlite.SqliteFileFormat>`__.
    - MyPy type annotations added to all function calls and variables.
    - List of used GUIDs are kept in a set, rather than a list. Thanks to `Eric Petersen (peap) <https://www.github.com/peap/>`_ for this contribution!
    - The file_formats package was inaccessable/not provided through the pip installer. Thanks to `Eric Petersen (peap) <https://www.github.com/peap/>`_ for catching this and providing the fix!
- 1.0.2 (Jan 26, 2019)
    - Added `SimpleTransaction <transaction.html#transaction.SimpleTransaction>`__ to make transactions with only 2 splits easier to manipulate.
    - Added properties to `Account <account.html#account.Account>`__.
        - color
        - notes
        - hidden
        - placeholder
    - Added properties to `Transaction <transaction.html#transaction.Transaction>`__.
        - notes
        - reversed_by
        - voided
        - void_time
        - void_reason
        - associated_uri

- 1.0.1 (Jan 9, 2019)
    - Bugfixes
    - Adding support for `ScheduledTransactions <transaction.html#transaction.ScheduledTransaction>`__.
    - Adding support for `Budgets <gnucash_file.html#gnucash_file.Budget>`__.
    - Added method `get_subaccount_by_id <account.html#account.Account.get_subaccount_by_id>`__  for retrieving a subaccount by its GUID

- 1.0.0 (Jan 4, 2019)
    - Initial Release
