"""
Module containing classes that read, manipulate, and write slots.

.. module:: slot
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional, List, Union
from xml.etree import ElementTree


class Slot:
    """Represents a slot in GnuCash."""

    def __init__(self, key: str, value: Any, slot_type: str) -> None:
        self.key: str = key
        self.value: Any = value
        self.type: str = slot_type

    @property
    def as_xml(self) -> ElementTree.Element:
        """
        Returns the current slot as GnuCash-compatible XML.

        :return: Current slot as XML
        :rtype: xml.etree.ElementTree.Element
        """
        slot_node: ElementTree.Element = ElementTree.Element('slot')
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
    def from_xml(cls, slot_node: ElementTree.Element, namespaces: Dict[str, str]) -> 'Slot':
        """
        Creates a Slot object from the GnuCash XML.

        :param slot_node: XML node for the slot
        :type slot_node: ElementTree.Element
        :param namespaces: XML namespaces for GnuCash elements
        :type namespaces: dict[str, str]
        :return: Slot object from XML
        :rtype: Slot
        """
        key_node: Optional[ElementTree.Element] = slot_node.find('slot:key', namespaces)
        if key_node is None or not key_node.text:
            raise ValueError('slot:key missing or empty in slot node')
        key: str = key_node.text
        value_node: Optional[ElementTree.Element] = slot_node.find('slot:value', namespaces)
        if value_node is None:
            raise ValueError('slot:value missing in slot node')
        slot_type = value_node.attrib['type']
        value: Any = None
        if slot_type == 'gdate':
            value_gdate_node: Optional[ElementTree.Element] = value_node.find('gdate')
            if value_gdate_node is None:
                raise ValueError('slot type is gdate but missing gdate node')
            if not value_gdate_node.text:
                raise ValueError('slot type is gdate but gdate node is empty')
            value = datetime.strptime(value_gdate_node.text, '%Y-%m-%d')
        elif slot_type in ['string', 'guid', 'numeric']:
            value = value_node.text
        elif slot_type == 'integer' and value_node.text:
            value = int(value_node.text)
        elif slot_type == 'double' and value_node.text:
            value = Decimal(value_node.text)
        else:
            child_tags: List[str] = list(set(map(lambda x: x.tag, value_node)))
            if len(child_tags) == 1 and child_tags[0] == 'slot':
                value = [Slot.from_xml(x, namespaces) for x in value_node]
            elif slot_type == 'frame':
                value = None   # Empty frame element, just leave it
            else:
                raise NotImplementedError('Slot type {} is not implemented.'.format(slot_type))

        return cls(key, value, slot_type)


class SlottableObject:
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
