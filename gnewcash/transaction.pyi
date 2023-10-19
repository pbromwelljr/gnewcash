from _typeshed import Incomplete
from datetime import datetime
from decimal import Decimal
from gnewcash.account import Account as Account
from gnewcash.commodity import Commodity as Commodity
from gnewcash.enums import AccountType as AccountType
from gnewcash.guid_object import GuidObject as GuidObject
from gnewcash.slot import SlottableObject as SlottableObject
from typing import Iterator, Optional, Tuple

class TransactionException(Exception): ...

class Transaction(GuidObject, SlottableObject):
    currency: Incomplete
    date_posted: Incomplete
    date_entered: Incomplete
    description: str
    splits: Incomplete
    memo: Incomplete
    def __init__(self) -> None: ...
    def __lt__(self, other: Transaction) -> bool: ...
    def __eq__(self, other: object) -> bool: ...
    @property
    def cleared(self) -> bool: ...
    def mark_transaction_cleared(self) -> None: ...
    @property
    def notes(self) -> str: ...
    @property
    def reversed_by(self) -> str: ...
    @property
    def voided(self) -> str: ...
    @property
    def void_time(self) -> str: ...
    @property
    def void_reason(self) -> str: ...
    @property
    def associated_uri(self) -> str: ...

class Split(GuidObject):
    reconciled_state: Incomplete
    amount: Incomplete
    account: Incomplete
    action: Incomplete
    memo: Incomplete
    quantity_denominator: str
    reconcile_date: Incomplete
    quantity_num: Incomplete
    lot_guid: Incomplete
    value_num: Incomplete
    value_denom: Incomplete
    def __init__(self, account: Optional[Account], amount: Optional[Decimal], reconciled_state: str = ...) -> None: ...

class TransactionManager:
    transactions: Incomplete
    disable_sort: bool
    deleted_transaction_guids: Incomplete
    def __init__(self) -> None: ...
    def add(self, new_transaction: Transaction) -> None: ...
    def delete(self, transaction: Transaction) -> None: ...
    def get_transactions(self, account: Optional[Account] = ...) -> Iterator[Transaction]: ...
    def get_account_starting_balance(self, account: Account) -> Decimal: ...
    def get_account_ending_balance(self, account: Account) -> Decimal: ...
    def minimum_balance_past_date(self, account: Account, date: datetime) -> Tuple[Optional[Decimal], Optional[datetime]]: ...
    def get_balance_at_date(self, account: Account, date: Optional[datetime] = ...) -> Decimal: ...
    def __getitem__(self, item: int) -> Transaction: ...
    def __len__(self) -> int: ...
    def __eq__(self, other: object) -> bool: ...
    def __iter__(self) -> Iterator[Transaction]: ...

class ScheduledTransaction(GuidObject):
    name: Incomplete
    enabled: bool
    auto_create: bool
    auto_create_notify: bool
    advance_create_days: int
    advance_remind_days: int
    instance_count: int
    start_date: Incomplete
    last_date: Incomplete
    end_date: Incomplete
    template_account: Incomplete
    recurrence_multiplier: int
    recurrence_period: Incomplete
    recurrence_start: Incomplete
    num_occur: Incomplete
    rem_occur: Incomplete
    recurrence_weekend_adjust: Incomplete
    def __init__(self) -> None: ...

class SimpleTransaction(Transaction):
    from_split: Incomplete
    to_split: Incomplete
    splits: Incomplete
    def __init__(self) -> None: ...
    @property
    def from_account(self) -> Optional[Account]: ...
    @property
    def to_account(self) -> Optional[Account]: ...
    @property
    def amount(self) -> Optional[Decimal]: ...
    @classmethod
    def from_transaction(cls, other: Transaction) -> SimpleTransaction: ...