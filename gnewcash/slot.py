"""
.. module:: slot
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""
from datetime import datetime
from decimal import Decimal
from xml.etree import ElementTree


class Slot:
    """
    Represents a slot in GnuCash.
    """
    def __init__(self, key, value, slot_type):
        self.key = key
        self.value = value
        self.type = slot_type

    @property
    def as_xml(self):
        """
        Returns the current slot as GnuCash-compatible XML

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
        Creates a Slot object from the GnuCash XML

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
