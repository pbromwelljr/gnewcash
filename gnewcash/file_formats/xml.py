"""
Module containing the logic for loading and saving XML files.

.. module:: xml
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""
import gzip
import logging
import pathlib
from typing import Any
from xml.etree import ElementTree

from gnewcash.file_formats.base import BaseFileFormat
from gnewcash.gnucash_file import GnuCashFile


class XMLFileFormat(BaseFileFormat):
    """Class containing the logic for loading and saving XML files."""

    LOGGER = logging.getLogger()

    @classmethod
    def load(cls, *args: Any, source_file: str = '', **kwargs: Any) -> GnuCashFile:
        built_file: 'GnuCashFile' = GnuCashFile()
        built_file.file_name = source_file

        source_path: pathlib.Path = pathlib.Path(source_file)
        if not source_path.exists():
            cls.LOGGER.warning('Could not find %s', source_file)
            return built_file

    @classmethod
    def get_xml_root(cls, source_path: pathlib.Path) -> ElementTree.Element:
        return ElementTree.parse(source=str(source_path)).getroot()

    @classmethod
    def dump(cls, *args: Any, **kwargs: Any) -> None:
        pass


class GZipXMLFileFormat(XMLFileFormat):
    """Class containing the logic for loading and saving XML files with GZip compression."""
    @classmethod
    def get_xml_root(cls, source_path: pathlib.Path) -> ElementTree.Element:
        with gzip.open(source_path, 'rb') as gzipped_file:
            contents = gzipped_file.read().decode('utf-8')
        return ElementTree.fromstring(contents)
