from _typeshed import Incomplete
from typing import Set

class GuidObject:
    used_guids: Set[str]
    guid: Incomplete
    def __init__(self) -> None: ...
    @classmethod
    def get_guid(cls) -> str: ...
