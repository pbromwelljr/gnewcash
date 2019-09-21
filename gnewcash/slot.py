"""
Module containing classes that read, manipulate, and write slots.

.. module:: slot
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""
from typing import Any, List, Optional, Union


class Slot:
    """Represents a slot in GnuCash."""

    def __init__(self, key: str, value: Any, slot_type: str) -> None:
        self.key: str = key
        self.value: Any = value
        self.type: str = slot_type
        self.sqlite_id: Optional[int] = None


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
