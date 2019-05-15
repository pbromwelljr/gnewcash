"""
Module containing classes that manage GUID objects.

.. module:: guid_object
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""
from typing import List
import uuid


class GuidObject:
    """Class used to generate unique GUIDs for various GNewCash objects."""

    used_guids: List[str] = []

    def __init__(self) -> None:
        super(GuidObject, self).__init__()
        self.guid: str = self.get_guid()

    def __str__(self) -> str:
        return str(self.guid)

    def __repr__(self) -> str:
        return str(self)

    @classmethod
    def get_guid(cls) -> str:
        """
        Retrieves a unique GUID and returns it.

        :return: New unique GUID
        :rtype: str
        """
        while True:
            random_uuid: uuid.UUID = uuid.uuid4()
            new_guid: str = str(random_uuid).replace('-', '').lower()
            if new_guid not in GuidObject.used_guids:
                GuidObject.used_guids.append(new_guid)
                return new_guid
