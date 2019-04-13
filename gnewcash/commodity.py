"""
Module containing classes that read, manipulate, and write commodities.

.. module:: commodity
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""

from typing import Optional, Dict

from xml.etree import ElementTree


class Commodity:
    """Represents a Commodity in GnuCash."""

    def __init__(self, commodity_id: str, space: str) -> None:
        self.commodity_id: str = commodity_id
        self.space: str = space
        self.get_quotes: bool = False
        self.quote_source: Optional[str] = None
        self.quote_tz: bool = False
        self.name: Optional[str] = None
        self.xcode: Optional[str] = None
        self.fraction: Optional[str] = None

    @property
    def as_xml(self) -> ElementTree.Element:
        """
        Returns the current commodity as GnuCash-compatible XML.

        :return: Current commodity as XML
        :rtype: xml.etree.ElementTree.Element
        """
        commodity_node = ElementTree.Element('gnc:commodity', {'version': '2.0.0'})
        ElementTree.SubElement(commodity_node, 'cmdty:space').text = self.space
        ElementTree.SubElement(commodity_node, 'cmdty:id').text = self.commodity_id
        if self.get_quotes:
            ElementTree.SubElement(commodity_node, 'cmdty:get_quotes')
        if self.quote_source:
            ElementTree.SubElement(commodity_node, 'cmdty:quote_source').text = self.quote_source
        if self.quote_tz:
            ElementTree.SubElement(commodity_node, 'cmdty:quote_tz')
        if self.name:
            ElementTree.SubElement(commodity_node, 'cmdty:name').text = self.name
        if self.xcode:
            ElementTree.SubElement(commodity_node, 'cmdty:xcode').text = self.xcode
        if self.fraction:
            ElementTree.SubElement(commodity_node, 'cmdty:fraction').text = self.fraction

        return commodity_node

    @classmethod
    def from_xml(cls, commodity_node, namespaces: Dict[str, str]) -> 'Commodity':
        """
        Creates a Commodity object from the GnuCash XML.

        :param commodity_node: XML node for the commodity
        :type commodity_node: ElementTree.Element
        :param namespaces: XML namespaces for GnuCash elements
        :type namespaces: dict[str, str]
        :return: Commodity object from XML
        :rtype: Commodity
        """
        commodity_id: str = commodity_node.find('cmdty:id', namespaces).text
        space: str = commodity_node.find('cmdty:space', namespaces).text
        new_commodity: 'Commodity' = cls(commodity_id, space)
        if commodity_node.find('cmdty:get_quotes', namespaces) is not None:
            new_commodity.get_quotes = True

        quote_source_node = commodity_node.find('cmdty:quote_source', namespaces)
        if quote_source_node is not None:
            new_commodity.quote_source = quote_source_node.text

        if commodity_node.find('quote_tz', namespaces) is not None:
            new_commodity.quote_tz = True

        name_node: Optional[ElementTree.Element] = commodity_node.find('cmdty:name', namespaces)
        if name_node is not None:
            new_commodity.name = name_node.text

        xcode_node: Optional[ElementTree.Element] = commodity_node.find('cmdty:xcode', namespaces)
        if xcode_node is not None:
            new_commodity.xcode = xcode_node.text

        fraction_node: Optional[ElementTree.Element] = commodity_node.find('cmdty:fraction', namespaces)
        if fraction_node is not None:
            new_commodity.fraction = fraction_node.text

        return new_commodity

    def as_short_xml(self, node_tag: str) -> ElementTree.Element:
        """
        Returns the current commodity as GnuCash-compatible XML (short version used for accounts).

        :param node_tag: XML element tag name for the commodity
        :type node_tag: str
        :return: Current commodity as short XML
        :rtype: xml.etree.ElementTree.Element
        """
        commodity_node: ElementTree.Element = ElementTree.Element(node_tag)
        ElementTree.SubElement(commodity_node, 'cmdty:space').text = self.space
        ElementTree.SubElement(commodity_node, 'cmdty:id').text = self.commodity_id
        return commodity_node
