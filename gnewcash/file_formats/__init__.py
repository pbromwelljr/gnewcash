"""
Module containing classes to indicate different file formats and their required methods.

.. module:: file_formats
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""
import abc
import enum

from sqlite3 import Cursor

from typing import Any, Dict, List, Optional, Tuple

from .base import *
from .xml import *
from .sqlite import *
