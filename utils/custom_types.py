from enum import IntEnum
from typing import IO, Optional, TypeAlias, Union

OptBytes: TypeAlias = Union[Optional[bytes], Optional[IO]]
StdBytes: TypeAlias = tuple[OptBytes, OptBytes]
StdStr: TypeAlias = tuple[str, str]


class Output(IntEnum):
    STDOUT = 0
    STDERR = 1


class NordException(Exception):
    pass


class LivenessException(Exception):
    pass
