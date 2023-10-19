import abc
from gnewcash.gnucash_file import GnuCashFile as GnuCashFile
from typing import Any

class BaseFileReader(abc.ABC, metaclass=abc.ABCMeta):
    @classmethod
    @abc.abstractmethod
    def load(cls, *args: Any, **kwargs: Any) -> GnuCashFile: ...

class BaseFileWriter(abc.ABC, metaclass=abc.ABCMeta):
    @classmethod
    @abc.abstractmethod
    def dump(cls, *args: Any, **kwargs: Any) -> None: ...

class BaseFileFormat(BaseFileReader, BaseFileWriter, abc.ABC):
    @classmethod
    def load(cls, *args: Any, **kwargs: Any) -> GnuCashFile: ...
    @classmethod
    def dump(cls, *args: Any, **kwargs: Any) -> None: ...
