"""
Module containing classes to indicate different file formats and their required methods.

.. module:: file_formats
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""
import abc
import enum

from sqlite3 import Cursor

from typing import Any, Dict, List, Optional, Tuple

from xml.etree import ElementTree


class FileFormat(enum.Enum):
    """Enumeration class for supported file formats."""

    XML = 1
    GZIP_XML = 2
    SQLITE = 3
    UNKNOWN = 99


class DBAction(enum.Enum):
    """Enumeration class for record operations in databases."""

    INSERT = 1
    UPDATE = 2


class GnuCashXMLObject(abc.ABC):
    """Abstract base classes for objects that can read from and write to XML."""

    @classmethod
    @abc.abstractmethod
    def from_xml(cls, node: ElementTree.Element, namespaces: Dict[str, str], *args: Any, **kwargs: Any) -> Any:
        """
        Abstract method for creating an object from an XML node.

        :param node: XML node from ElementTree.
        :type node: ElementTree.Element
        :param namespaces: GnuCash XML namespaces needed to find elements.
        :type namespaces: dict[str, str]
        """
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def as_xml(self) -> ElementTree.Element:
        """Abstract method for converting an object to an XML node."""
        raise NotImplementedError


class GnuCashSQLiteObject(abc.ABC):
    """Abstract base classes for objects that can read from and write to SQLite."""

    @classmethod
    @abc.abstractmethod
    def from_sqlite(cls, sqlite_cursor: Cursor) -> Any:
        """
        Abstract method for creating an object from a SQLite database.

        :param sqlite_cursor: Open cursor to a SQLite database.
        :type sqlite_cursor: sqlite3.Cursor
        """
        raise NotImplementedError

    @abc.abstractmethod
    def to_sqlite(self, sqlite_cursor: Cursor) -> None:
        """
        Abstract method for writing an object to a SQLite database.

        :param sqlite_cursor: Open cursor to a SQLite database.
        :type sqlite_cursor: sqlite3.Cursor
        """
        raise NotImplementedError

    @classmethod
    def get_sqlite_table_data(cls, sqlite_cursor: Cursor, table_name: str, where_condition: Optional[str] = None,
                              where_parameters: Optional[Tuple[Any]] = None) -> List[Dict[str, Any]]:
        """
        Helper method for retrieving data from a SQLite table.

        :param sqlite_cursor: Open cursor to a SQLite database.
        :type sqlite_cursor: sqlite3.Cursor
        :param table_name: SQLite table name
        :type table_name: str
        :param where_condition: SQL WHERE condition for the query (if any)
        :type where_condition: str
        :param where_parameters: SQL WHERE parameters for the query (if any)
        :type where_parameters: tuple
        :return: List of dictionaries (keys being the column names) for each row in the SQLite table
        :rtype: list[dict[str, Any]]
        """
        sql = 'SELECT * FROM {}'.format(table_name)
        if where_condition is not None:
            sql += ' WHERE ' + where_condition
        if where_parameters is not None:
            sqlite_cursor.execute(sql, where_parameters)
        else:
            sqlite_cursor.execute(sql)
        column_names = [column[0] for column in sqlite_cursor.description]
        rows = []
        for row in sqlite_cursor.fetchall():
            row_data = dict(zip(column_names, row))
            rows.append(row_data)
        return rows

    @classmethod
    def get_db_action(cls, sqlite_cursor: Cursor, table_name: str, column_name: str, row_identifier: Any) -> DBAction:
        """
        Helper method for determining the appropriate operation on a SQL table.

        :param sqlite_cursor: Open cursor to a SQLite database.
        :type sqlite_cursor: sqlite3.Cursor
        :param table_name: SQLite table name
        :type table_name: str
        :param column_name: Column to be used for existence check
        :type column_name: str
        :param row_identifier: Unique identifier for the row
        :type row_identifier: Any
        :return: Appropriate action based on record existence
        :rtype: DBAction
        """
        sql = 'SELECT 1 FROM {} WHERE {} = ?'.format(table_name, column_name)
        sqlite_cursor.execute(sql, (row_identifier,))

        record = sqlite_cursor.fetchone()
        if record is None:
            return DBAction.INSERT
        return DBAction.UPDATE
