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

    def to_sqlite(self, sqlite_cursor):
        db_action = self.get_db_action(sqlite_cursor, 'commodities', 'guid', self.guid)
        if db_action == DBAction.INSERT:
            sql = 'INSERT INTO commodities(guid, namespace, mnemonic, fullname, cusip, fraction, quote_flag, '\
                  'quote_source, quote_tz) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)'
            sql_args = (self.guid, self.space, self.commodity_id, self.name, self.xcode, self.fraction,
                        1 if self.get_quotes else 0, self.quote_source, self.quote_tz,)
            sqlite_cursor.execute(sql, sql_args)
        elif db_action == DBAction.UPDATE:
            sql = 'UPDATE commodities SET namespace = ?, mnemonic = ?, fullname = ?, cusip = ?, fraction = ?, '\
                  'quote_flag = ?, quote_source = ?, quote_tz = ? WHERE guid = ?'
            sql_args = (self.space, self.commodity_id, self.name, self.xcode, self.fraction,
                        1 if self.get_quotes else 0, self.quote_source, self.quote_tz, self.guid,)
            sqlite_cursor.execute(sql, sql_args)


GnuCashSQLiteObject.register(Commodity)
