"""
Catch-all module containing methods that might be helpful to GNewCash users.

.. module:: account
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""
import pathlib
import re
from datetime import datetime
from os import PathLike
from typing import Union


def delete_log_files(
        gnucash_folder: Union[str, PathLike],
        ignore_permission_errors: bool = True
) -> None:
    """
    Deletes log files at the specified directory.

    :param gnucash_folder: Directory to delete log files
    :type gnucash_folder: Union[str, PathLike]
    :param ignore_permission_errors: Ignore PermissionError thrown when deleting files. (default true)
    :type ignore_permission_errors: bool
    """
    backup_file_format: re.Pattern = re.compile(r'.*[0-9]{14}\.gnucash$')
    gnucash_path = pathlib.Path(gnucash_folder)
    for file in gnucash_path.glob('*.*'):
        if not file.is_file():
            continue
        if ('.gnucash' in file.name and file.name.endswith('.log')) or backup_file_format.match(file.name):
            try:
                file.unlink()
            except PermissionError as e:
                if not ignore_permission_errors:
                    raise e


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
