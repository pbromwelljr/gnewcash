"""
Module containing classes that read, manipulate, and write commodities.

.. module:: commodity
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""

from xml.etree import ElementTree

from gnewcash.guid_object import GuidObject
from gnewcash.file_formats import DBAction, GnuCashXMLObject, GnuCashSQLiteObject


class Commodity(GuidObject, GnuCashXMLObject, GnuCashSQLiteObject):
    """Represents a Commodity in GnuCash."""

    def __init__(self, commodity_id, space):
        super().__init__()
        self.commodity_id = commodity_id
        self.space = space
        self.get_quotes = False
        self.quote_source = None
        self.quote_tz = False
        self.name = None
        self.xcode = None
        self.fraction = None

    @property
    def as_xml(self):
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
    def from_xml(cls, commodity_node, namespaces):
        """
        Creates a Commodity object from the GnuCash XML.

        :param commodity_node: XML node for the commodity
        :type commodity_node: ElementTree.Element
        :param namespaces: XML namespaces for GnuCash elements
        :type namespaces: dict[str, str]
        :return: Commodity object from XML
        :rtype: Commodity
        """
        commodity_id = commodity_node.find('cmdty:id', namespaces).text
        space = commodity_node.find('cmdty:space', namespaces).text
        new_commodity = cls(commodity_id, space)
        if commodity_node.find('cmdty:get_quotes', namespaces) is not None:
            new_commodity.get_quotes = True

        quote_source_node = commodity_node.find('cmdty:quote_source', namespaces)
        if quote_source_node is not None:
            new_commodity.quote_source = quote_source_node.text

        if commodity_node.find('quote_tz', namespaces) is not None:
            new_commodity.quote_tz = True

        name_node = commodity_node.find('cmdty:name', namespaces)
        if name_node is not None:
            new_commodity.name = name_node.text

        xcode_node = commodity_node.find('cmdty:xcode', namespaces)
        if xcode_node is not None:
            new_commodity.xcode = xcode_node.text

        fraction_node = commodity_node.find('cmdty:fraction', namespaces)
        if fraction_node is not None:
            new_commodity.fraction = fraction_node.text

        return new_commodity

    def as_short_xml(self, node_tag):
        """
        Returns the current commodity as GnuCash-compatible XML (short version used for accounts).

        :return: Current commodity as short XML
        :rtype: xml.etree.ElementTree.Element
        """
        commodity_node = ElementTree.Element(node_tag)
        ElementTree.SubElement(commodity_node, 'cmdty:space').text = self.space
        ElementTree.SubElement(commodity_node, 'cmdty:id').text = self.commodity_id
        return commodity_node

    @classmethod
    def from_sqlite(cls, sqlite_cursor, commodity_guid=None):
        if commodity_guid is None:
            commodity_data = cls.get_sqlite_table_data(sqlite_cursor, 'commodities')
        else:
            commodity_data = cls.get_sqlite_table_data(sqlite_cursor, 'commodities', 'guid = ?', (commodity_guid,))

        new_commodities = []
        for commodity in commodity_data:
            commodity_id = commodity['mnemonic']
            space = commodity['namespace']

            new_commodity = cls(commodity_id, space)
            new_commodity.guid = commodity['guid']
            new_commodity.get_quotes = commodity['quote_flag'] == 1
            new_commodity.quote_source = commodity['quote_source']
            new_commodity.quote_tz = commodity['quote_tz']
            new_commodity.name = commodity['fullname']
            new_commodity.xcode = commodity['cusip']
            new_commodity.fraction = commodity['fraction']
            new_commodities.append(new_commodity)

        if commodity_guid is None:
            return new_commodities
        return new_commodities[0]

    def to_sqlite(self, sqlite_cursor):
        db_action = self.get_db_action(sqlite_cursor, 'commodities', 'guid', self.guid)
        if db_action == DBAction.INSERT:
            sql = 'INSERT INTO commodities(guid, namespace, mnemonic, fullname, cusip, fraction, quote_flag, '\
                  'quote_source, quote_tz) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)'
            sql_args = (self.guid, self.space, self.commodity_id, self.name, self.xcode, self.fraction,
                        1 if self.get_quotes else 0, self.quote_source, self.quote_tz,)
            sqlite_cursor.execute(sql, sql_args)
        elif db_action == DBAction.UPDATE:
            sql = 'UPDATE commodities SET namespace = ?, mnemonic = ?, fullname = ?, cusip = ?, fraction = ?, '\
                  'quote_flag = ?, quote_source = ?, quote_tz = ? WHERE guid = ?'
            sql_args = (self.space, self.commodity_id, self.name, self.xcode, self.fraction,
                        1 if self.get_quotes else 0, self.quote_source, self.quote_tz, self.guid,)
            sqlite_cursor.execute(sql, sql_args)


GnuCashSQLiteObject.register(Commodity)
