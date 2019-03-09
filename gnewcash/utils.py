"""
.. module:: account
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""
import re
from genericpath import isfile, exists
from os import listdir, remove
from os.path import join


def delete_log_files(gnucash_file_path):
    """
    Deletes log files at the specified directory.

    :param gnucash_file_path: Directory to delete log files
    :type gnucash_file_path: str
    """
    backup_file_format = re.compile(r'.*[0-9]{14}\.gnucash$')
    for file in [x for x in listdir(gnucash_file_path) if isfile(join(gnucash_file_path, x))]:
        full_file_path = join(gnucash_file_path, file)
        if (('.gnucash' in file and file.endswith('.log')) or backup_file_format.match(file)) \
                and exists(full_file_path):
            try:
                remove(full_file_path)
            except PermissionError:
                # Fine, ignore it.
                pass
