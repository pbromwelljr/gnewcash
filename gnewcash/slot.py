from datetime import datetime
from xml.etree import ElementTree


class Slot(object):
    def __init__(self, key, value, type):
        self.key = key
        self.value = value
        self.type = type

    @property
    def as_xml(self):
        slot_node = ElementTree.Element('slot')
        ElementTree.SubElement(slot_node, 'slot:key').text = self.key

        slot_value_node = ElementTree.SubElement(slot_node, 'slot:value', {'type': self.type})
        if self.type == 'gdate':
            ElementTree.SubElement(slot_value_node, 'gdate').text = datetime.strftime(self.value, '%Y-%m-%d')
        elif self.type == 'string':
            slot_value_node.text = self.value
        else:
            raise NotImplementedError('Slot type {} is not implemented.'.format(self.type))

        return slot_node

    @classmethod
    def from_xml(cls, slot_node, namespaces):
        key = slot_node.find('slot:key', namespaces).text
        value_node = slot_node.find('slot:value', namespaces)
        slot_type = value_node.attrib['type']
        if slot_type == 'gdate':
            value = datetime.strptime(value_node.find('gdate').text, '%Y-%m-%d')
        elif slot_type == 'string':
            value = value_node.text
        else:
            raise NotImplementedError('Slot type {} is not implemented.'.format(slot_type))

        return cls(key, value, slot_type)
