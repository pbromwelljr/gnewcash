import json
import unittest
from xml.etree import ElementTree

import gnewcash.gnucash_file as gcf


class TestGnuCashFile(unittest.TestCase):
    def test_read_write(self):
        gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash')
        gnucash_file.build_file('test_files/Test1.testresult.gnucash')

        original_tree = ElementTree.parse(source='test_files/Test1.gnucash')
        original_root = original_tree.getroot()

        test_tree = ElementTree.parse(source='test_files/Test1.testresult.gnucash')
        test_root = test_tree.getroot()

        self.check_gnucash_elements(original_root, test_root)

    def check_gnucash_elements(self, original_element, test_element):
        self.assertEqual(original_element.tag, test_element.tag)
        self.assertEqual(json.dumps(original_element.attrib), json.dumps(test_element.attrib))
        if original_element.text:
            original_element.text = original_element.text.strip()
        if test_element.text:
            test_element.text = test_element.text.strip()
        self.assertEqual(original_element.text, test_element.text)
        for original_subelement, test_subelement in zip(list(original_element), list(test_element)):
            self.check_gnucash_elements(original_subelement, test_subelement)
