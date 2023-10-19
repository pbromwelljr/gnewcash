from _typeshed import Incomplete
from gnewcash.guid_object import GuidObject as GuidObject

class Commodity(GuidObject):
    commodity_id: Incomplete
    space: Incomplete
    get_quotes: bool
    quote_source: Incomplete
    quote_tz: bool
    name: Incomplete
    xcode: Incomplete
    fraction: Incomplete
    def __init__(self, commodity_id: str, space: str) -> None: ...
