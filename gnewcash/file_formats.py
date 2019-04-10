import abc
import enum


class FileFormat(enum.Enum):
    XML = 1
    GZIP_XML = 2
    SQLITE = 3
    UNKNOWN = 99


class DBAction(enum.Enum):
    INSERT = 1
    UPDATE = 2


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
    @classmethod
    @abc.abstractmethod
    def from_sqlite(cls, sqlite_cursor):
        raise NotImplementedError

    @abc.abstractmethod
    def to_sqlite(self, sqlite_cursor):
        raise NotImplementedError

    @classmethod
    def get_sqlite_table_data(cls, sqlite_cursor, table_name, where_condition=None, where_parameters=None):
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
    def get_db_action(cls, sqlite_cursor, table_name, column_name, column_identifier):
        sql = 'SELECT 1 FROM {} WHERE {} = ?'.format(table_name, column_name)
        sqlite_cursor.execute(sql, (column_identifier,))

        record = sqlite_cursor.fetchone()
        if record is None:
            return DBAction.INSERT
        return DBAction.UPDATE
