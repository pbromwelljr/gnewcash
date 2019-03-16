"""
Module containing classes that read, manipulate, and write slots.

.. module:: slot
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""
from datetime import datetime
from decimal import Decimal
from xml.etree import ElementTree

from gnewcash.file_formats import GnuCashXMLObject


class Slot(GnuCashXMLObject):
    """Represents a slot in GnuCash."""

    # TODO: SQLite support

    def __init__(self, key, value, slot_type):
        self.key = key
        self.value = value
        self.type = slot_type

    @property
    def as_xml(self):
        """
        Returns the current slot as GnuCash-compatible XML.

        :return: Current slot as XML
        :rtype: xml.etree.ElementTree.Element
        """
        slot_node = ElementTree.Element('slot')
        ElementTree.SubElement(slot_node, 'slot:key').text = self.key

        slot_value_node = ElementTree.SubElement(slot_node, 'slot:value', {'type': self.type})
        if self.type == 'gdate':
            ElementTree.SubElement(slot_value_node, 'gdate').text = datetime.strftime(self.value, '%Y-%m-%d')
        elif self.type in ['string', 'guid', 'numeric']:
            slot_value_node.text = self.value
        elif self.type in ['integer', 'double']:
            slot_value_node.text = str(self.value)
        elif isinstance(self.value, list) and self.value:
            for sub_slot in self.value:
                slot_value_node.append(sub_slot.as_xml)
        elif self.type == 'frame':
            pass  # Empty frame element, just leave it
        else:
            raise NotImplementedError('Slot type {} is not implemented.'.format(self.type))

        return slot_node

    @classmethod
    def from_xml(cls, slot_node, namespaces):
        """
        Creates a Slot object from the GnuCash XML.

        :param slot_node: XML node for the slot
        :type slot_node: ElementTree.Element
        :param namespaces: XML namespaces for GnuCash elements
        :type namespaces: dict[str, str]
        :return: Slot object from XML
        :rtype: Slot
        """
        key = slot_node.find('slot:key', namespaces).text
        value_node = slot_node.find('slot:value', namespaces)
        slot_type = value_node.attrib['type']
        if slot_type == 'gdate':
            value = datetime.strptime(value_node.find('gdate').text, '%Y-%m-%d')
        elif slot_type in ['string', 'guid', 'numeric']:
            value = value_node.text
        elif slot_type == 'integer':
            value = int(value_node.text)
        elif slot_type == 'double':
            value = Decimal(value_node.text)
        else:
            child_tags = list(set(map(lambda x: x.tag, value_node)))
            if len(child_tags) == 1 and child_tags[0] == 'slot':
                value = [Slot.from_xml(x, namespaces) for x in value_node]
            elif slot_type == 'frame':
                value = None   # Empty frame element, just leave it
            else:
                raise NotImplementedError('Slot type {} is not implemented.'.format(slot_type))

        return cls(key, value, slot_type)


class SlottableObject(object):
    """Class used to consolidate storing and retrieving slot values."""

    def __init__(self):
        super(SlottableObject, self).__init__()
        self.slots = []

    def get_slot_value(self, key):
        """
        Retrieves the value of the slot given a certain key.

        :param key: Name of the slot
        :type key: str

        :return: Slot value
        :rtype: Any
        """
        if not self.slots:
            return None

        target_slot = list(filter(lambda x: x.key == key, self.slots))
        if not target_slot:
            return None

        return target_slot[0].value

    def set_slot_value(self, key, value, slot_type):
        """
        Sets the value of the slot given a certain key and slot type.

        :param key: Name of the slot
        :type key: str
        :param value: New value of the slot
        :type value: Any
        :param slot_type: Type of slot
        :type slot_type: str
        """
        target_slot = list(filter(lambda x: x.key == key, self.slots))
        if target_slot:
            target_slot[0].value = value
        else:
            self.slots.append(Slot(key, value, slot_type))

    def set_slot_value_bool(self, key, value, slot_type):
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
