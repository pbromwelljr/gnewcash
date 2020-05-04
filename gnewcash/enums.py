"""
Module containing classes for enumerated values.

.. module:: account
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""


class AccountType:
    """Enumeration class to indicate the types of accounts available in GnuCash."""

    ROOT: str = 'ROOT'
    BANK: str = 'BANK'
    INCOME: str = 'INCOME'
    ASSET: str = 'ASSET'
    CREDIT: str = 'CREDIT'
    EXPENSE: str = 'EXPENSE'
    EQUITY: str = 'EQUITY'
    LIABILITY: str = 'LIABILITY'
