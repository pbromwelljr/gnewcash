"""
Module containing classes that read, manipulate, and write transactions.

.. module:: transaction
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""
import enum
import warnings
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Generator, Iterator, List, Optional, Tuple

from gnewcash.account import Account
from gnewcash.commodity import Commodity
from gnewcash.enums import AccountType
from gnewcash.guid_object import GuidObject
from gnewcash.slot import Slot, SlottableObject


class TransactionException(Exception):
    """Exception class used to handle transaction-related exceptions."""


class Transaction(GuidObject, SlottableObject):
    """Represents a transaction in GnuCash."""

    def __init__(
            self,
            guid: Optional[str] = None,
            slots: Optional[List[Slot]] = None,
            currency: Optional[Commodity] = None,
            date_posted: Optional[datetime] = None,
            date_entered: Optional[datetime] = None,
            description: str = '',
            splits: Optional[List['Split']] = None,
            memo: Optional[str] = None,
    ) -> None:
        GuidObject.__init__(self, guid)
        SlottableObject.__init__(self, slots)
        self.currency: Optional[Commodity] = currency
        self.date_posted: Optional[datetime] = date_posted
        self.date_entered: Optional[datetime] = date_entered
        self.description: str = description
        self.splits: List[Split] = splits or []
        self.memo: Optional[str] = memo

    def __str__(self) -> str:
        if self.date_posted:
            return f'{self.date_posted.strftime("%m/%d/%Y")} - {self.description}'
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
        return sum(1 for split in self.splits if split.reconciled_state.lower() == 'c') > 0

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
        return super().get_slot_value('notes')

    @notes.setter
    def notes(self, value: str) -> None:
        super().set_slot_value('notes', value, 'string')

    @property
    def reversed_by(self) -> str:
        """
        GUID of the transaction that reverses this transaction.

        :return: Transaction GUID
        :rtype: str
        """
        return super().get_slot_value('reversed-by')

    @reversed_by.setter
    def reversed_by(self, value: str) -> None:
        super().set_slot_value('reversed-by', value, 'guid')

    @property
    def voided(self) -> str:
        """
        Void status.

        :return: Void status
        :rtype: str
        """
        return super().get_slot_value('trans-read-only')

    @voided.setter
    def voided(self, value: str) -> None:
        super().set_slot_value('trans-read-only', value, 'string')

    @property
    def void_time(self) -> str:
        """
        Time that the transaction was voided.

        :return: Time that the transaction was voided
        :rtype: str
        """
        return super().get_slot_value('void-time')

    @void_time.setter
    def void_time(self, value: str) -> None:
        super().set_slot_value('void-time', value, 'string')

    @property
    def void_reason(self) -> str:
        """
        Reason that the transaction was voided.

        :return: Reason that the transaction was voided
        :rtype: str
        """
        return super().get_slot_value('void-reason')

    @void_reason.setter
    def void_reason(self, value: str) -> None:
        super().set_slot_value('void-reason', value, 'string')

    @property
    def associated_uri(self) -> str:
        """
        URI associated with the transaction.

        :return: URI associated with the transaction
        :rtype: str
        """
        return super().get_slot_value('assoc_uri')

    @associated_uri.setter
    def associated_uri(self, value: str) -> None:
        super().set_slot_value('assoc_uri', value, 'string')

    @property
    def from_splits(self) -> Generator['Split', None, None]:
        """
        Retrieves the "from" splits in the transaction.

        :return: Splits with a negative amount.
        :rtype: collections.Iterable[Split]
        """
        return (x for x in self.splits if x.amount is not None and x.amount < Decimal(0))

    @property
    def to_splits(self) -> Generator['Split', None, None]:
        """
        Retrieves the "to" splits in the transaction.

        :return: Splits with a positive amount.
        :rtype: collections.Iterable[Split]
        """
        return (x for x in self.splits if x.amount is not None and x.amount > Decimal(0))

    @property
    def split_accounts(self) -> Generator[Account, None, None]:
        """
        Retrieves the accounts involved in the splits.

        :return: Accounts involved in splits.
        :rtype: collections.Iterable[Account]
        """
        return (x.account for x in self.splits if x.account is not None)

    @property
    def split_account_names(self) -> Generator[str, None, None]:
        """
        Retrieves the names of the accounts involved in the splits.

        :return: Names of the accounts involved in the splits.
        :rtype: collections.Iterable[str]
        """
        return (x.account.name for x in self.splits if x.account is not None)

    @property
    def from_split_accounts(self) -> Generator[Account, None, None]:
        """
        Retrieves the accounts that are associated with the "from" splits.

        :return: Accounts associated with splits that have a negative amount.
        :rtype: collections.Iterable[Account]
        """
        return (x.account for x in self.from_splits if x.account is not None)

    @property
    def from_split_account_names(self) -> Generator[str, None, None]:
        """
        Retrieves the names of accounts that are associated with the "from" splits.

        :return: Names of accounts associated with splits that have a negative amount.
        :rtype: collections.Iterable[Account]
        """
        return (x.account.name for x in self.from_splits if x.account is not None)

    @property
    def to_split_accounts(self) -> Generator[Account, None, None]:
        """
        Retrieves the accounts that are associated with the "to" splits.

        :return: Accounts associated with splits that have a positive amount.
        :rtype: collections.Iterable[Account]
        """
        return (x.account for x in self.to_splits if x.account is not None)

    @property
    def to_split_account_names(self) -> Generator[str, None, None]:
        """
        Retrieves the names of accounts that are associated with the "to" splits.

        :return: Names of accounts associated with splits that have a positive amount.
        :rtype: collections.Iterable[str]
        """
        return (x.account.name for x in self.to_splits if x.account is not None)

    @property
    def splits_total(self) -> Decimal:
        """
        Retrieves the sum of all positive split amounts.

        :return: Sum of all positive split amounts.
        :rtype: decimal.Decimal
        """
        return sum((x.amount for x in self.to_splits if x.amount is not None), start=Decimal(0))


class Split(GuidObject):
    """Represents a split in GnuCash."""

    def __init__(
            self,
            account: Optional[Account],
            amount: Optional[Decimal],
            reconciled_state: str = 'n',
            guid: Optional[str] = None,
            action: Optional[str] = None,
            memo: Optional[str] = None,
            quantity_denominator: str = '100',
            reconcile_date: Optional[datetime] = None,
            quantity_num: Optional[int] = None,
            lot_guid: Optional[str] = None,
            value_num: Optional[int] = None,
            value_denom: Optional[int] = None,
    ):
        super().__init__(guid)
        self.reconciled_state: str = reconciled_state
        self.amount: Optional[Decimal] = amount
        self.account: Optional[Account] = account
        self.action: Optional[str] = action
        self.memo: Optional[str] = memo
        self.quantity_denominator: str = quantity_denominator
        self.reconcile_date: Optional[datetime] = reconcile_date
        self.quantity_num: Optional[int] = quantity_num
        self.lot_guid: Optional[str] = lot_guid
        self.value_num: Optional[int] = value_num
        self.value_denom: Optional[int] = value_denom

    def __str__(self) -> str:
        return f'{self.account} - {self.amount}'

    def __repr__(self) -> str:
        return str(self)


class TransactionManager:
    """Class used to add/remove transactions, maintaining a chronological order based on transaction posted date."""

    def __init__(
            self,
            transactions: Optional[List[Transaction]] = None,
            disable_sort: bool = False,
            sort_method: Optional['SortingMethod'] = None,
    ) -> None:
        self.transactions: List[Transaction] = transactions or []
        self.disable_sort: bool = disable_sort
        self.deleted_transaction_guids: List[str] = []
        self.sort_method: SortingMethod = sort_method or StandardSort()

    def add(self, new_transaction: Transaction) -> None:
        """
        Adds a transaction to the transaction manager.

        :param new_transaction: Transaction to add
        :type new_transaction: Transaction
        """
        if self.disable_sort:
            self.transactions.append(new_transaction)
        else:
            for index, transaction in enumerate(self.transactions):
                compare_result = self.sort_method.compare(transaction, new_transaction)
                if compare_result in (SortingResult.FIRST_GREATER, SortingResult.EQUAL):
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
        end_date: Optional[datetime] = max(x.date_posted for x in self.transactions if x.date_posted is not None)
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
        for transaction in self.transactions:
            transaction_accounts = list(map(lambda y: y.account, transaction.splits))
            is_applicable: bool = False
            if date is not None and account in transaction_accounts and transaction.date_posted is not None and \
                    transaction.date_posted <= date:
                is_applicable = True
            elif date is None and account in transaction_accounts:
                is_applicable = True

            if not is_applicable:
                continue

            if date is None or (transaction.date_posted is not None and transaction.date_posted <= date):
                applicable_split: Split = next(filter(lambda x: x.account == account, transaction.splits))
                amount: Decimal = applicable_split.amount or Decimal(0)
                if account.type == AccountType.CREDIT:
                    amount = amount * -1
                balance += amount
        return balance

    def get_balance_at_transaction(self, account: Account, transaction: Transaction) -> Decimal:
        """
        Retrieves the account balance for the specified account at a certain transaction.

        :param account: Account to get the balance of
        :type account: Account
        :param transaction: Last transaction to consider when determining the account balance.
        :type transaction: Transaction
        :return: Account balance at specified transaction or 0, if no applicable transactions were found.
        :rtype: decimal.Decimal
        """
        balance = Decimal(0)
        for iter_transaction in self.transactions:
            for split in iter_transaction.splits:
                if split.account != account or split.amount is None:
                    continue
                balance += split.amount
            if iter_transaction.guid == transaction.guid:
                break
        return abs(balance)

    def get_cleared_balance(self, account: Account) -> Decimal:
        """
        Retrieves the current cleared balance for the specified account.

        :param account: Account to get the cleared balance of.
        :type account: Account
        :return: Current cleared balance for the account
        :rtype: decimal.Decimal
        """
        cleared_balance = Decimal(0)
        for transaction in self.transactions:
            for split in transaction.splits:
                if (split.reconciled_state or '').lower() != 'c' or split.account != account or split.amount is None:
                    continue
                cleared_balance += split.amount
        return cleared_balance

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

    def __init__(
            self,
            guid: Optional[str] = None,
            name: Optional[str] = None,
            enabled: Optional[bool] = False,
            auto_create: Optional[bool] = False,
            auto_create_notify: Optional[bool] = False,
            advance_create_days: Optional[int] = -1,
            advance_remind_days: Optional[int] = -1,
            instance_count: Optional[int] = 0,
            start_date: Optional[datetime] = None,
            last_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None,
            template_account: Optional[Account] = None,
            recurrence_multiplier: Optional[int] = 0,
            recurrence_period: Optional[str] = None,
            recurrence_start: Optional[datetime] = None,
            num_occur: Optional[int] = None,
            rem_occur: Optional[int] = None,
            recurrence_weekend_adjust: Optional[str] = None,
    ) -> None:
        super().__init__(guid)
        self.name: Optional[str] = name
        self.enabled: Optional[bool] = enabled
        self.auto_create: Optional[bool] = auto_create
        self.auto_create_notify: Optional[bool] = auto_create_notify
        self.advance_create_days: Optional[int] = advance_create_days
        self.advance_remind_days: Optional[int] = advance_remind_days
        self.instance_count: Optional[int] = instance_count
        self.start_date: Optional[datetime] = start_date
        self.last_date: Optional[datetime] = last_date
        self.end_date: Optional[datetime] = end_date
        self.template_account: Optional[Account] = template_account
        self.recurrence_multiplier: Optional[int] = recurrence_multiplier
        self.recurrence_period: Optional[str] = recurrence_period
        self.recurrence_start: Optional[datetime] = recurrence_start
        self.num_occur: Optional[int] = num_occur
        self.rem_occur: Optional[int] = rem_occur
        self.recurrence_weekend_adjust: Optional[str] = recurrence_weekend_adjust


class SimpleTransaction(Transaction):
    """Class used to simplify creating and manipulating Transactions that only have 2 splits."""

    def __init__(
            self,
            from_account: Optional[Account] = None,
            to_account: Optional[Account] = None,
            amount: Optional[Decimal] = None,
            currency: Optional[Commodity] = None,
            date_posted: Optional[datetime] = None,
            date_entered: Optional[datetime] = None,
            description: str = '',
            memo: Optional[str] = None,
    ) -> None:
        super().__init__(
            currency=currency,
            date_posted=date_posted,
            date_entered=date_entered,
            description=description,
            memo=memo,
        )
        self.from_split: Split = Split(None, None)
        self.to_split: Split = Split(None, None)
        self.splits: List[Split] = [self.from_split, self.to_split]
        if from_account is not None:
            self.from_account = from_account
        if to_account is not None:
            self.to_account = to_account
        if amount is not None:
            self.amount = amount

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

        if len(simple.splits) > 2:
            raise TransactionException(
                'SimpleTransactions can only be created from transactions with 2 splits: ' +
                f'{other} has {len(simple.splits)} splits - {", ".join([str(x) for x in other.splits])}'
            )

        first_split = simple.splits[0]
        second_split = simple.splits[1] if len(simple.splits) > 1 else first_split
        first_split_amount = first_split.amount
        second_split_amount = second_split.amount

        if any((first_split_amount is None, second_split_amount is None, first_split_amount == second_split_amount)):
            warnings.warn(f'Could not determine to/from split on SimpleTransaction for {simple.guid}. ' +
                          'Assuming first split is "from" split, assuming second is "to" split.')
            simple.from_split = first_split
            simple.to_split = second_split
        elif first_split_amount is not None and second_split_amount is not None:
            if first_split_amount > second_split_amount:
                simple.to_split = first_split
                simple.from_split = second_split
            elif first_split_amount < second_split_amount:
                simple.to_split = second_split
                simple.from_split = first_split

        return simple


class SortingResult(enum.Enum):
    """Enumeration class that determines the result of the sort."""

    FIRST_GREATER = 1
    SECOND_GREATER = -1
    EQUAL = 0


class SortingMethod:
    """Base class for derivative sorting method classes."""

    def __init__(self, reverse: bool = False):
        self.reverse = reverse

    def compare(self, transaction1: Transaction, transaction2: Transaction) -> SortingResult:
        """
        Compares one transaction with another and returns which one is greater, or if they're equal.

        :param transaction1: First transaction in comparison.
        :type transaction1: Transaction
        :param transaction2: Second transaction in comparison.
        :type transaction2: Transaction
        :return: Enum result that contains if the first transaction is greater, second transaction is greater, or equal.
        :rtype: SortingResult
        """
        raise NotImplementedError

    def _reverse_sort_result(self, sorting_result: SortingResult) -> SortingResult:
        if not self.reverse:
            return sorting_result

        if sorting_result == SortingResult.FIRST_GREATER:
            return SortingResult.SECOND_GREATER
        if sorting_result == SortingResult.SECOND_GREATER:
            return SortingResult.FIRST_GREATER
        return SortingResult.EQUAL

    @classmethod
    def _get_compare_result(cls, first_value: Any, second_value: Any) -> SortingResult:
        if first_value is not None and (second_value is None or first_value > second_value):
            return SortingResult.FIRST_GREATER
        if second_value is not None and (first_value is None or first_value < second_value):
            return SortingResult.SECOND_GREATER
        return SortingResult.EQUAL


class StandardSort(SortingMethod):
    """Sort logic for GnuCash's standard sort."""

    def compare(self, transaction1: Transaction, transaction2: Transaction) -> SortingResult:
        """
        Compares one transaction with another and returns which one is greater, or if they're equal.

        :param transaction1: First transaction in comparison.
        :type transaction1: Transaction
        :param transaction2: Second transaction in comparison.
        :type transaction2: Transaction
        :return: Enum result that contains if the first transaction is greater, second transaction is greater, or equal.
        :rtype: SortingResult
        """
        result: SortingResult = SortingResult.EQUAL

        transaction_attrs = ('date_posted', 'date_entered', 'description', 'guid')
        for transaction_attr in transaction_attrs:
            transaction1_value = getattr(transaction1, transaction_attr)
            transaction2_value = getattr(transaction2, transaction_attr)
            result = self._get_compare_result(transaction1_value, transaction2_value)
            if result != SortingResult.EQUAL:
                break

        if result != SortingResult.EQUAL:
            return self._reverse_sort_result(result)

        split_attrs = ('memo', 'action', 'reconciled_state', 'amount', 'value_num', 'reconcile_date', 'guid')
        for split_attr in split_attrs:
            split1_value = getattr(transaction1.splits[0], split_attr)
            split2_value = getattr(transaction2.splits[0], split_attr)
            result = self._get_compare_result(split1_value, split2_value)
            if result != SortingResult.EQUAL:
                break

        return self._reverse_sort_result(result)


class InvalidSortFieldException(Exception):
    """Custom exception class for when the sort field isn't set."""


class SortBySingleTransactionFieldMethod(SortingMethod):
    """Abstract class for sorting methods that operate on a single transaction field."""

    def __init__(self, reverse: bool = False) -> None:
        super().__init__(reverse)
        self.sort_field: Optional[str] = None

    def compare(self, transaction1: Transaction, transaction2: Transaction) -> SortingResult:
        """
        Compares one transaction with another and returns which one is greater, or if they're equal.

        :param transaction1: First transaction in comparison.
        :type transaction1: Transaction
        :param transaction2: Second transaction in comparison.
        :type transaction2: Transaction
        :return: Enum result that contains if the first transaction is greater, second transaction is greater, or equal.
        :rtype: SortingResult
        """
        if self.sort_field is None:
            raise InvalidSortFieldException('Sort field not set.')

        transaction1_value = getattr(transaction1, self.sort_field)
        transaction2_value = getattr(transaction2, self.sort_field)
        result = self._get_compare_result(transaction1_value, transaction2_value)
        return self._reverse_sort_result(result)


class SortBySingleSplitFieldMethod(SortingMethod):
    """Abstract class for sorting methods that operate on a single split field."""

    def __init__(self, reverse: bool = False) -> None:
        super().__init__(reverse)
        self.sort_field: Optional[str] = None

    def compare(self, transaction1: Transaction, transaction2: Transaction) -> SortingResult:
        """
        Compares one transaction with another and returns which one is greater, or if they're equal.

        :param transaction1: First transaction in comparison.
        :type transaction1: Transaction
        :param transaction2: Second transaction in comparison.
        :type transaction2: Transaction
        :return: Enum result that contains if the first transaction is greater, second transaction is greater, or equal.
        :rtype: SortingResult
        """
        if self.sort_field is None:
            raise InvalidSortFieldException('Sort field not set.')

        split1_value = getattr(transaction1.splits[0], self.sort_field)
        split2_value = getattr(transaction2.splits[0], self.sort_field)
        result = self._get_compare_result(split1_value, split2_value)
        return self._reverse_sort_result(result)


class DateSort(SortBySingleTransactionFieldMethod):
    """Sort logic for GnuCash's date sort."""

    def __init__(self, reverse: bool = False) -> None:
        super().__init__(reverse)
        self.sort_field = 'date_posted'


class DateOfEntrySort(SortBySingleTransactionFieldMethod):
    """Sort logic for GnuCash's date of entry sort."""

    def __init__(self, reverse: bool = False) -> None:
        super().__init__(reverse)
        self.sort_field = 'date_entered'


class TransactionNumberSort(SortBySingleTransactionFieldMethod):
    """Sort logic for GnuCash's transaction number sort."""

    def __init__(self, reverse: bool = False) -> None:
        super().__init__(reverse)
        self.sort_field = 'guid'


class DescriptionSort(SortBySingleTransactionFieldMethod):
    """Sort logic for GnuCash's description sort."""

    def __init__(self, reverse: bool = False) -> None:
        super().__init__(reverse)
        self.sort_field = 'description'


class AmountSort(SortBySingleSplitFieldMethod):
    """Sort logic for GnuCash's split amount sort."""

    def __init__(self, reverse: bool = False) -> None:
        super().__init__(reverse)
        self.sort_field = 'amount'


class NumberActionSort(SortBySingleSplitFieldMethod):
    """Sort logic for GnuCash's number/action sort."""

    def __init__(self, reverse: bool = False) -> None:
        super().__init__(reverse)
        self.sort_field = 'action'


class MemoSort(SortBySingleSplitFieldMethod):
    """Sort logic for GnuCash's memo sort."""

    def __init__(self, reverse: bool = False) -> None:
        super().__init__(reverse)
        self.sort_field = 'memo'
