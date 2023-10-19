from _typeshed import Incomplete
from decimal import Decimal
from gnewcash.account import Account as Account
from gnewcash.commodity import Commodity as Commodity
from gnewcash.guid_object import GuidObject as GuidObject
from gnewcash.slot import Slot as Slot, SlottableObject as SlottableObject
from gnewcash.transaction import ScheduledTransaction as ScheduledTransaction, SimpleTransaction as SimpleTransaction, Split as Split, Transaction as Transaction, TransactionManager as TransactionManager
from typing import Any, List, Optional

class GnuCashFile:
    books: Incomplete
    file_name: Incomplete
    def __init__(self, books: Optional[List['Book']] = ...) -> None: ...
    @classmethod
    def read_file(cls, source_file: str, file_format: Any, sort_transactions: bool = ...) -> GnuCashFile: ...
    def build_file(self, target_file: str, file_format: Any, prettify_xml: bool = ...) -> None: ...
    def simplify_transactions(self) -> None: ...
    def strip_transaction_timezones(self) -> None: ...

class Book(GuidObject, SlottableObject):
    root_account: Incomplete
    transactions: Incomplete
    commodities: Incomplete
    slots: Incomplete
    template_root_account: Incomplete
    template_transactions: Incomplete
    scheduled_transactions: Incomplete
    budgets: Incomplete
    def __init__(self, root_account: Optional[Account] = ..., transactions: Optional[TransactionManager] = ..., commodities: Optional[List[Commodity]] = ..., slots: Optional[List[Slot]] = ..., template_root_account: Optional[Account] = ..., template_transactions: Optional[List[Transaction]] = ..., scheduled_transactions: Optional[List[ScheduledTransaction]] = ..., budgets: Optional[List['Budget']] = ...) -> None: ...
    def get_account(self, *paths_to_account: str, **kwargs: Any) -> Optional[Account]: ...
    def get_account_balance(self, account: Account) -> Decimal: ...

class Budget(GuidObject, SlottableObject):
    name: Incomplete
    description: Incomplete
    period_count: Incomplete
    recurrence_multiplier: Incomplete
    recurrence_period_type: Incomplete
    recurrence_start: Incomplete
    def __init__(self) -> None: ...
