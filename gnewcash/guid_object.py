"""
.. module:: guid_object
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""
import uuid


class GuidObject:
    """
    Class used to generate unique GUIDs for various GNewCash objects.
    """
    used_guids = []

    def __init__(self):
        self.guid = self.get_guid()

    def __str__(self):
        return str(self.guid)

    def __repr__(self):
        return str(self)

    @classmethod
    def get_guid(cls):
        """
        Retrieves a unique GUID and returns it

        :return: New unique GUID
        :rtype: str
        """
        while True:
            random_uuid = uuid.uuid4()
            new_guid = str(random_uuid).replace('-', '').lower()
            if new_guid not in GuidObject.used_guids:
                GuidObject.used_guids.append(new_guid)
                return new_guid
