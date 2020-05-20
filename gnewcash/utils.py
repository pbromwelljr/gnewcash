"""
Catch-all ,odule containing methods that might be helpful to GNewCash users.

.. module:: account
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""
import re
from datetime import datetime
from genericpath import isfile, exists
from os import listdir, remove
from os.path import join

from typing import Pattern


def delete_log_files(gnucash_file_path: str) -> None:
    """
    Deletes log files at the specified directory.

    :param gnucash_file_path: Directory to delete log files
    :type gnucash_file_path: str
    """
    backup_file_format: Pattern = re.compile(r'.*[0-9]{14}\.gnucash$')
    for file in [x for x in listdir(gnucash_file_path) if isfile(join(gnucash_file_path, x))]:
        full_file_path: str = join(gnucash_file_path, file)
        if (('.gnucash' in file and file.endswith('.log')) or backup_file_format.match(file)) \
                and exists(full_file_path):
            try:
                remove(full_file_path)
            except PermissionError:
                # Fine, ignore it.
                pass


def safe_iso_date_parsing(date_string: str) -> datetime:
    """
    Attempts to parse a date with timezone information. If it fails, it tries to parse without timezone information.

    :param date_string: Date string to parse
    :type date_string: str
    :return: Parsed date object
    :rtype: datetime.datetime
    """
    try:
        return datetime.strptime(date_string.strip(), '%Y-%m-%d %H:%M:%S %z')
    except ValueError:
        return datetime.strptime(date_string.strip(), '%Y-%m-%d %H:%M:%S')


def safe_iso_date_formatting(date_obj: datetime) -> str:
    """
    Attempts for format a date with timezone information. If it fails, it tries to format without timezone information.

    :param date_obj: Date object to format
    :type date_obj: datetime.datetime
    :return: Formatted date string
    :rtype: str
    """
    if date_obj.tzinfo is not None:
        return date_obj.strftime('%Y-%m-%d %H:%M:%S %z')
    return date_obj.strftime('%Y-%m-%d %H:%M:%S')
