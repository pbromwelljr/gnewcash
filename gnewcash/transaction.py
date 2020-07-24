"""
Module containing classes that read, manipulate, and write transactions.

.. module:: transaction
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""
import warnings
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Iterator, List, Optional, Tuple

from gnewcash.account import Account
from gnewcash.commodity import Commodity
from gnewcash.enums import AccountType
from gnewcash.guid_object import GuidObject
from gnewcash.slot import SlottableObject


class Transaction(GuidObject, SlottableObject):
    """Represents a transaction in GnuCash."""

    def __init__(self) -> None:
        super(Transaction, self).__init__()
        self.currency: Optional[Commodity] = None
        self.date_posted: Optional[datetime] = None
        self.date_entered: Optional[datetime] = None
        self.description: str = ''
        self.splits: List[Split] = []
        self.memo: Optional[str] = None

    def __str__(self) -> str:
        if self.date_posted:
            return '{} - {}'.format(self.date_posted.strftime('%m/%d/%Y'), self.description)
        return self.description

    def __repr__(self) -> str:
        return str(self)

    def __lt__(self, other: 'Transaction') -> bool:
        if self.date_posted is not None and other.date_posted is not None:
            return self.date_posted < other.date_posted
        if self.date_posted is not None and other.date_posted is None:
            return False
        if self.date_posted is None and other.date_posted is not None:
            return True
        return False

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Transaction):
            return NotImplemented
        return self.date_posted == other.date_posted

    @property
    def cleared(self) -> bool:
        """
        Checks if all splits in the transaction are cleared.

        :return: Boolean indicating if all splits in the transaction are cleared.
        :rtype: bool
        """
        return sum([1 for split in self.splits if split.reconciled_state.lower() == 'c']) > 0

    def mark_transaction_cleared(self) -> None:
        """Marks all splits in the transaction as cleared (reconciled_state = 'c')."""
        for split in self.splits:
            split.reconciled_state = 'c'

    @property
    def notes(self) -> str:
        """
        Notes on the transaction.

        :return: Notes tied to the transaction
        :rtype: str
        """
        return super(Transaction, self).get_slot_value('notes')

    @notes.setter
    def notes(self, value: str) -> None:
        super(Transaction, self).set_slot_value('notes', value, 'string')

    @property
    def reversed_by(self) -> str:
        """
        GUID of the transaction that reverses this transaction.

        :return: Transaction GUID
        :rtype: str
        """
        return super(Transaction, self).get_slot_value('reversed-by')

    @reversed_by.setter
    def reversed_by(self, value: str) -> None:
        super(Transaction, self).set_slot_value('reversed-by', value, 'guid')

    @property
    def voided(self) -> str:
        """
        Void status.

        :return: Void status
        :rtype: str
        """
        return super(Transaction, self).get_slot_value('trans-read-only')

    @voided.setter
    def voided(self, value: str) -> None:
        super(Transaction, self).set_slot_value('trans-read-only', value, 'string')

    @property
    def void_time(self) -> str:
        """
        Time that the transaction was voided.

        :return: Time that the transaction was voided
        :rtype: str
        """
        return super(Transaction, self).get_slot_value('void-time')

    @void_time.setter
    def void_time(self, value: str) -> None:
        super(Transaction, self).set_slot_value('void-time', value, 'string')

    @property
    def void_reason(self) -> str:
        """
        Reason that the transaction was voided.

        :return: Reason that the transaction was voided
        :rtype: str
        """
        return super(Transaction, self).get_slot_value('void-reason')

    @void_reason.setter
    def void_reason(self, value: str) -> None:
        super(Transaction, self).set_slot_value('void-reason', value, 'string')

    @property
    def associated_uri(self) -> str:
        """
        URI associated with the transaction.

        :return: URI associated with the transaction
        :rtype: str
        """
        return super(Transaction, self).get_slot_value('assoc_uri')

    @associated_uri.setter
    def associated_uri(self, value: str) -> None:
        super(Transaction, self).set_slot_value('assoc_uri', value, 'string')


class Split(GuidObject):
    """Represents a split in GnuCash."""

    def __init__(self, account: Optional[Account], amount: Optional[Decimal], reconciled_state: str = 'n'):
        super(Split, self).__init__()
        self.reconciled_state: str = reconciled_state
        self.amount: Optional[Decimal] = amount
        self.account: Optional[Account] = account
        self.action: Optional[str] = None
        self.memo: Optional[str] = None
        self.quantity_denominator: str = '100'
        self.reconcile_date: Optional[datetime] = None
        self.quantity_num: Optional[int] = None
        self.lot_guid: Optional[str] = None
        self.value_num: Optional[int] = None
        self.value_denom: Optional[int] = None

    def __str__(self) -> str:
        return '{} - {}'.format(self.account, str(self.amount))

    def __repr__(self) -> str:
        return str(self)


class TransactionManager:
    """Class used to add/remove transactions, maintaining a chronological order based on transaction posted date."""

    def __init__(self) -> None:
        self.transactions: List[Transaction] = []
        self.disable_sort: bool = False
        self.deleted_transaction_guids: List[str] = []

    def add(self, new_transaction: Transaction) -> None:
        """
        Adds a transaction to the transaction manager.

        :param new_transaction: Transaction to add
        :type new_transaction: Transaction
        """
        if new_transaction.date_posted is None or self.disable_sort:
            self.transactions.append(new_transaction)
        elif not self.disable_sort:
            # Inserting transactions in order
            for index, transaction in enumerate(self.transactions):
                if not transaction.date_posted:
                    continue
                if transaction.date_posted > new_transaction.date_posted:
                    self.transactions.insert(index, new_transaction)
                    break
                elif transaction.date_posted == new_transaction.date_posted:
                    self.transactions.insert(index, new_transaction)
                    break
            else:
                self.transactions.append(new_transaction)

    def delete(self, transaction: Transaction) -> None:
        """
        Removes a transaction from the transaction manager.

        :param transaction: Transaction to remove
        :type transaction: Transaction
        """
        # We're looking up by GUID here because a simple list remove doesn't work
        for index, iter_transaction in enumerate(self.transactions):
            if iter_transaction.guid == transaction.guid:
                self.deleted_transaction_guids.append(transaction.guid)
                del self.transactions[index]
                break

    def get_transactions(self, account: Optional[Account] = None) -> Iterator[Transaction]:
        """
        Generator function that gets transactions based on a from account and/or to account for the transaction.

        :param account: Account to retrieve transactions for (default None, all transactions)
        :type account: Account
        :return: Generator that produces transactions based on the given from account and/or to account
        :rtype: Iterator[Transaction]
        """
        for transaction in self.transactions:
            if account is None or account in list(map(lambda x: x.account, transaction.splits)):
                yield transaction

    def get_account_starting_balance(self, account: Account) -> Decimal:
        """
        Retrieves the starting balance for the current account, given the list of transactions.

        :param account: Account to get starting balance of.
        :type account: Account
        :return: First transaction amount if the account has transactions, otherwise 0.
        :rtype: decimal.Decimal
        """
        account_transactions: List[Transaction] = [x for x in self.transactions
                                                   if account in [y.account for y in x.splits
                                                                  if y.amount is not None and y.amount >= 0]]
        amount: Decimal = Decimal(0)
        if account_transactions:
            first_transaction: Transaction = account_transactions[0]
            amount = next(filter(lambda x: x.account == account and x.amount is not None and x.amount >= 0,
                                 first_transaction.splits)).amount or Decimal(0)
        return amount

    def get_account_ending_balance(self, account: Account) -> Decimal:
        """
        Retrieves the ending balance for the provided account given the list of transactions in the manager.

        :param account: Account to get the ending balance for
        :type account: Account
        :return: Account starting balance
        :rtype: decimal.Decimal
        """
        return self.get_balance_at_date(account)

    def minimum_balance_past_date(self, account: Account, date: datetime) \
            -> Tuple[Optional[Decimal], Optional[datetime]]:
        """
        Gets the minimum balance for the account after a certain date, given the list of transactions.

        :param account: Account to get the minimum balance information of
        :type account: Account
        :param date: datetime object representing the date you want to find the minimum balance for.
        :type date: datetime.datetime
        :return: Tuple containing the minimum balance (element 0) and the date it's at that balance (element 1)
        :rtype: tuple
        """
        minimum_balance: Optional[Decimal] = None
        minimum_balance_date: Optional[datetime] = None
        iterator_date: datetime = date
        end_date: Optional[datetime] = max(map(lambda x: x.date_posted, self.transactions))
        if end_date is None:
            return None, None
        while iterator_date < end_date:
            iterator_date += timedelta(days=1)
            current_balance: Decimal = self.get_balance_at_date(account, iterator_date)
            if minimum_balance is None or current_balance < minimum_balance:
                minimum_balance, minimum_balance_date = current_balance, iterator_date
        if minimum_balance_date and minimum_balance_date > end_date:
            minimum_balance_date = end_date
        return minimum_balance, minimum_balance_date

    def get_balance_at_date(self, account: Account, date: Optional[datetime] = None) -> Decimal:
        """
        Retrieves the account balance for the current account at a certain date, given the list of transactions.

        If the provided date is None, it will retrieve the ending balance.

        :param account: Account to get the balance of
        :type account: Account
        :param date: Last date to consider when determining the account balance.
        :type date: datetime.datetime
        :return: Account balance at specified date (or ending balance) or 0, if no applicable transactions were found.
        :rtype: decimal.Decimal
        """
        balance: Decimal = Decimal(0)
        applicable_transactions: List[Transaction] = []
        for transaction in self.transactions:
            transaction_accounts = list(map(lambda y: y.account, transaction.splits))
            if date is not None and account in transaction_accounts and transaction.date_posted is not None and \
                    transaction.date_posted <= date:
                applicable_transactions.append(transaction)
            elif date is None and account in transaction_accounts:
                applicable_transactions.append(transaction)

        for transaction in applicable_transactions:
            if date is None or (transaction.date_posted is not None and transaction.date_posted <= date):
                applicable_split: Split = next(filter(lambda x: x.account == account, transaction.splits))
                amount: Decimal = applicable_split.amount or Decimal(0)
                if account.type == AccountType.CREDIT:
                    amount = amount * -1
                balance += amount
        return balance

    # Making TransactionManager iterable
    def __getitem__(self, item: int) -> Transaction:
        if item > len(self):
            raise IndexError
        return self.transactions[item]

    def __len__(self) -> int:
        return len(self.transactions)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TransactionManager):
            return NotImplemented
        for my_transaction, other_transaction in zip(self.transactions, other.transactions):
            if my_transaction != other_transaction:
                return False
        return True

    def __iter__(self) -> Iterator[Transaction]:
        yield from self.transactions


class ScheduledTransaction(GuidObject):
    """Class that represents a scheduled transaction in Gnucash."""

    def __init__(self) -> None:
        super(ScheduledTransaction, self).__init__()
        self.name: Optional[str] = None
        self.enabled: Optional[bool] = False
        self.auto_create: Optional[bool] = False
        self.auto_create_notify: Optional[bool] = False
        self.advance_create_days: Optional[int] = -1
        self.advance_remind_days: Optional[int] = -1
        self.instance_count: Optional[int] = 0
        self.start_date: Optional[datetime] = None
        self.last_date: Optional[datetime] = None
        self.end_date: Optional[datetime] = None
        self.template_account: Optional[Account] = None
        self.recurrence_multiplier: Optional[int] = 0
        self.recurrence_period: Optional[str] = None
        self.recurrence_start: Optional[datetime] = None
        self.num_occur: Optional[int] = None
        self.rem_occur: Optional[int] = None
        self.recurrence_weekend_adjust: Optional[str] = None


class SimpleTransaction(Transaction):
    """Class used to simplify creating and manipulating Transactions that only have 2 splits."""

    def __init__(self) -> None:
        super(SimpleTransaction, self).__init__()
        self.from_split: Split = Split(None, None)
        self.to_split: Split = Split(None, None)
        self.splits: List[Split] = [self.from_split, self.to_split]

    @property
    def from_account(self) -> Optional[Account]:
        """
        Account which the transaction transfers funds from.

        :return: Account which the transaction transfers funds from.
        :rtype: Account
        """
        return self.from_split.account

    @from_account.setter
    def from_account(self, value: 'Account') -> None:
        self.from_split.account = value

    @property
    def to_account(self) -> Optional[Account]:
        """
        Account which the transaction transfers funds to.

        :return: Account which the transaction transfers funds to.
        :rtype: Account
        """
        return self.to_split.account

    @to_account.setter
    def to_account(self, value: Account) -> None:
        self.to_split.account = value

    @property
    def amount(self) -> Optional[Decimal]:
        """
        Dollar amount for funds transferred.

        :return: Dollar amount for funds transferred.
        :rtype: decimal.Decimal
        """
        return self.to_split.amount

    @amount.setter
    def amount(self, value: Decimal) -> None:
        self.from_split.amount = value * -1
        self.to_split.amount = value

    @classmethod
    def from_transaction(cls, other: Transaction) -> 'SimpleTransaction':
        """Creates a SimpleTransaction from a regular Transaction."""
        simple: SimpleTransaction = cls()
        simple.guid = other.guid
        simple.currency = other.currency
        simple.date_posted = other.date_posted
        simple.date_entered = other.date_entered
        simple.description = other.description
        simple.splits = other.splits
        simple.memo = other.memo

        if len(simple.splits) != 2:
            raise Exception('SimpleTransactions can only be created from transactions with 2 splits')

        first_split_amount = simple.splits[0].amount
        second_split_amount = simple.splits[1].amount
        if first_split_amount is None or second_split_amount is None or first_split_amount == second_split_amount:
            warnings.warn(f'Could not determine to/from split on SimpleTransaction for {simple.guid}.' +
                          'Assuming first split is "from" split, assuming second is "to" split.')
            simple.from_split = simple.splits[0]
            simple.to_split = simple.splits[1]
        elif first_split_amount > second_split_amount:
            simple.to_split = simple.splits[0]
            simple.from_split = simple.splits[1]
        elif first_split_amount < second_split_amount:
            simple.to_split = simple.splits[1]
            simple.from_split = simple.splits[0]

        return simple
