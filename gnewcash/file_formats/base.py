"""
Module containing the base structure for file loading and saving.

.. module:: base
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""
import abc
from typing import Any

from gnewcash.gnucash_file import GnuCashFile


class BaseFileReader(abc.ABC):
    """Class used to define base structure for file loading."""

    @classmethod
    @abc.abstractmethod
    def load(cls, *args: Any, **kwargs: Any) -> GnuCashFile:
        """
        Method used to load a GnuCash file into memory.

        :param args: Method args
        :param kwargs: Method kwargs
        :return: GnuCashFile object
        :rtype: GnuCashFile
        """
        raise NotImplementedError


class BaseFileWriter(abc.ABC):
    """Class used to define base structure for file saving."""

    @classmethod
    @abc.abstractmethod
    def dump(cls, *args: Any, **kwargs: Any) -> None:
        """
        Method used to dump a GnuCash file from memory to disk.

        :param args: Method args
        :param kwargs: Method kwargs
        """
        raise NotImplementedError


class BaseFileFormat(BaseFileReader, BaseFileWriter, abc.ABC):
    """Class used to define base structure for file loading and saving."""

    @classmethod
    def load(cls, *args: Any, **kwargs: Any) -> GnuCashFile:
        """
        Method used to load a GnuCash file into memory.

        :param args: Method args
        :param kwargs: Method kwargs
        :return: GnuCashFile object
        :rtype: GnuCashFile
        """
        return super().load(*args, **kwargs)

    @classmethod
    def dump(cls, *args: Any, **kwargs: Any) -> None:
        """
        Method used to dump a GnuCash file from memory to disk.

        :param args: Method args
        :param kwargs: Method kwargs
        """
        super().dump(*args, **kwargs)
