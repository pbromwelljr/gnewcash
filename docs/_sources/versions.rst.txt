Versions
********

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
