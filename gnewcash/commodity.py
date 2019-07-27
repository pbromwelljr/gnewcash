"""
Module containing classes that read, manipulate, and write commodities.

.. module:: commodity
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""
from sqlite3 import Cursor

from typing import Optional, Union, List

from gnewcash.guid_object import GuidObject
from gnewcash.file_formats import DBAction


class Commodity(GuidObject):
    """Represents a Commodity in GnuCash."""

    def __init__(self, commodity_id: str, space: str) -> None:
        super().__init__()
        self.commodity_id: str = commodity_id
        self.space: str = space
        self.get_quotes: bool = False
        self.quote_source: Optional[str] = None
        self.quote_tz: bool = False
        self.name: Optional[str] = None
        self.xcode: Optional[str] = None
        self.fraction: Optional[str] = None
