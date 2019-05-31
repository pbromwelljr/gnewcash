"""
Module containing classes that read, manipulate, and write slots.

.. module:: slot
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""
from datetime import datetime
from sqlite3 import Cursor
from typing import Any, List, Union

from gnewcash.file_formats import GnuCashSQLiteObject


class Slot(GnuCashSQLiteObject):
    """Represents a slot in GnuCash."""

    sqlite_slot_type_mapping = {
        1: 'integer',
        2: 'double',
        3: 'numeric',
        4: 'string',
        5: 'guid',
        9: 'guid',
        10: 'gdate'
    }

    def __init__(self, key: str, value: Any, slot_type: str) -> None:
        self.key: str = key
        self.value: Any = value
        self.type: str = slot_type

    @classmethod
    def from_sqlite(cls, sqlite_cursor: Cursor, object_id: str) -> List['Slot']:
        """
        Creates Slot objects from the GnuCash SQLite database.

        :param sqlite_cursor: Open cursor to the SQLite database
        :type sqlite_cursor: sqlite3.Cursor
        :param object_id: ID of the object that the slot belongs to
        :type object_id: str
        :return: Slot objects from SQLite
        :rtype: list[Slot]
        """
        slot_info = cls.get_sqlite_table_data(sqlite_cursor, 'slots', 'obj_guid = ?', (object_id,))
        new_slots = []
        for slot in slot_info:
            slot_type = cls.sqlite_slot_type_mapping[slot['slot_type']]
            slot_name = slot['name']
            if slot_type == 'guid':
                slot_value = slot['guid_val']
            elif slot_type == 'string':
                slot_value = slot['string_val']
            elif slot_type == 'gdate':
                slot_value = datetime.strptime(slot['gdate_val'], '%Y%m%d')
            else:
                raise NotImplementedError('Slot type {} is not implemented.'.format(slot['slot_type']))
            new_slot = cls(slot_name, slot_value, slot_type)
            new_slots.append(new_slot)
        return new_slots

    def to_sqlite(self, sqlite_cursor: Cursor) -> None:
        # slot_action = self.get_db_action(sqlite_cursor, 'slots', )
        # TODO: Slots don't have GUIDs. Need to store the DB ID in the object.
        raise NotImplementedError


class SlottableObject(object):
    """Class used to consolidate storing and retrieving slot values."""

    def __init__(self) -> None:
        super(SlottableObject, self).__init__()
        self.slots: List[Slot] = []

    def get_slot_value(self, key: str) -> Any:
        """
        Retrieves the value of the slot given a certain key.

        :param key: Name of the slot
        :type key: str

        :return: Slot value
        :rtype: Any
        """
        if not self.slots:
            return None

        target_slot: List[Slot] = list(filter(lambda x: x.key == key, self.slots))
        if not target_slot:
            return None

        return target_slot[0].value

    def set_slot_value(self, key: str, value: Any, slot_type: str) -> None:
        """
        Sets the value of the slot given a certain key and slot type.

        :param key: Name of the slot
        :type key: str
        :param value: New value of the slot
        :type value: Any
        :param slot_type: Type of slot
        :type slot_type: str
        """
        target_slot: List[Slot] = list(filter(lambda x: x.key == key, self.slots))
        if target_slot:
            target_slot[0].value = value
        else:
            self.slots.append(Slot(key, value, slot_type))

    def set_slot_value_bool(self, key: str, value: Union[str, bool], slot_type: str) -> None:
        """
        Helper function for slots that expect "true" or "false" GnuCash-side.

        Converts "true" (case insensitive) and True to "true".
        Converts "false" (case insensitive) and False to "false".

        :param key:
        :type key: str
        :param value: New value of the slot
        :type value: bool|str
        :param slot_type: Type of slot
        :type slot_type: str
        """
        if isinstance(value, str) and value.lower() == 'true':
            value = True
        elif isinstance(value, str) and value.lower() == 'false':
            value = False
        elif isinstance(value, bool):
            value = value
        else:
            raise ValueError('"bool" slot values must be "true", "false", True, or False.')

        value = 'true' if value else 'false'

        self.set_slot_value(key, value, slot_type)
