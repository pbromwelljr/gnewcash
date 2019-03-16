import abc
import enum


class FileFormat(enum.Enum):
    XML = 1
    GZIP_XML = 2
    SQLITE = 3
    UNKNOWN = 99


class GnuCashXMLObject(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def from_xml(cls, node, namespaces, *args, **kwargs):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def as_xml(self):
        raise NotImplementedError


class GnuCashSQLiteObject(abc.ABC):
    sqlite_table_name = None

    @classmethod
    @abc.abstractmethod
    def from_sqlite(cls, sqlite_row):
        raise NotImplementedError

    @abc.abstractmethod
    def to_sqlite(self, sqlite_handle):
        raise NotImplementedError
