from datetime import datetime

def delete_log_files(gnucash_file_path: str) -> None: ...
def safe_iso_date_parsing(date_string: str) -> datetime: ...
def safe_iso_date_formatting(date_obj: datetime) -> str: ...