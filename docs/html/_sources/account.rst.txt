Account
*********

.. module:: account

Standard Accounts
-----------------

.. autoclass:: Account
   :members:
   :show-inheritance:

.. autoclass:: AccountType


Shortcut Accounts
-----------------

.. autoclass:: AssetAccount
    :show-inheritance:

.. autoclass:: BankAccount
    :show-inheritance:

.. autoclass:: CreditAccount
    :show-inheritance:

.. autoclass:: EquityAccount
    :show-inheritance:

.. autoclass:: ExpenseAccount
    :show-inheritance:

.. autoclass:: IncomeAccount
    :show-inheritance:

.. autoclass:: LiabilityAccount
    :show-inheritance:

Special Accounts
----------------

.. autoclass:: InterestAccountBase
   :members:

.. autoclass:: InterestAccount
   :members:
   :special-members:
   :exclude-members: __repr__,__str__,__weakref__

.. autoclass:: InterestAccountWithSubaccounts
   :members:
   :special-members:
   :exclude-members: __repr__,__str__,__weakref__

.. autoclass:: LoanStatus
   :show-inheritance:
   :members:

.. autoclass:: LoanExtraPayment
   :show-inheritance:
   :members:
