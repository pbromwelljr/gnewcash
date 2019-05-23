"""
Module containing the base structure for file loading and saving.

.. module:: base
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""
import abc
from typing import Any

from gnewcash.gnucash_file import GnuCashFile


class BaseFileFormat(abc.ABC):
    """Class used to define base structure for file loading and saving."""
    @classmethod
    @abc.abstractmethod
    def load(cls, *args: Any, **kwargs: Any) -> GnuCashFile:
        """
        Method used to load a GnuCash file into memory
        :param args: Method args
        :param kwargs: Method kwargs
        :return: GnuCashFile object
        :rtype: GnuCashFile
        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def dump(cls, *args: Any, **kwargs: Any) -> None:
        """
        Method used to dump a GnuCash file from memory to disk
        :param args: Method args
        :param kwargs: Method kwargs
        """
        raise NotImplementedError
