"""
Module containing classes that read, manipulate, and write commodities.

.. module:: commodity
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""
from typing import Optional

from gnewcash.guid_object import GuidObject


class Commodity(GuidObject):
    """Represents a Commodity in GnuCash."""

    def __init__(
            self,
            commodity_id: str,
            space: str,
            guid: Optional[str] = None,
            get_quotes: bool = False,
            quote_source: Optional[str] = None,
            quote_tz: bool = False,
            name: Optional[str] = None,
            xcode: Optional[str] = None,
            fraction: Optional[str] = None,
    ) -> None:
        super().__init__(guid)
        self.commodity_id: str = commodity_id
        self.space: str = space
        self.get_quotes: bool = get_quotes
        self.quote_source: Optional[str] = quote_source
        self.quote_tz: bool = quote_tz
        self.name: Optional[str] = name
        self.xcode: Optional[str] = xcode
        self.fraction: Optional[str] = fraction
