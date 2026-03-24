from enum import IntEnum
from io import BufferedReader
from os import linesep
from typing import IO, Generic, Optional, TypeVar

from utils.custom_types import Output, StdBytes, StdStr


class StdResult:
    def __init__(self, result_bytes: StdBytes):
        self.result_bytes = result_bytes
        self._stdout_str = None
        self._stderr_str = None

    def stdout(self) -> str:
        if self._stdout_str is None:
            self._stdout_str = self._decode(Output.STDOUT)
        return self._stdout_str

    def stderr(self) -> str:
        if self._stderr_str is None:
            self._stderr_str = self._decode(Output.STDERR)
        return self._stderr_str

    def result(self) -> StdStr:
        return self.stdout(), self.stderr()

    def _decode(self, stream: Output) -> str:
        to_decode = self.result_bytes[0] if stream == Output.STDOUT else self.result_bytes[1]
        if not to_decode:
            return ""
        if isinstance(to_decode, IO) or isinstance(to_decode, BufferedReader):
            to_decode = to_decode.read()
        if isinstance(to_decode, bytes):
            return to_decode.decode()
        return f"Couldn't parse stream {stream.name} of type {type(to_decode)}"


class ReturnCode(IntEnum):
    message: str

    def __new__(cls, value: int, message: str):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.message = message
        return obj

    @classmethod
    def from_value(cls, value: int) -> "ReturnCode":
        for member in cls:
            if member.value == value:
                return member
        return cls.UNKNOWN

    @classmethod
    def to_message(cls, value: int) -> str:
        return cls.from_value(value).message

    UNKNOWN = -1, "Unknown"
    SUCCESS = 0, "Success"
    FAILURE = 1, "Failure"


T = TypeVar("T")


class ReturnObject(Generic[T]):
    def __init__(self, return_code: ReturnCode, return_value: Optional[T] = None):
        self.return_code = return_code
        self.return_value = return_value

    def value(self):
        return self.return_value

    def out_str(self, default: str = "") -> str:
        if not self.return_value:
            return default
        if isinstance(self.return_value, StdResult):
            return self.return_value.stdout() or default
        return default

    def err_str(self, default: str = "") -> str:
        if not self.return_value:
            return default
        if isinstance(self.return_value, StdResult):
            return self.return_value.stderr() or default

        # More error parsing logic maybe if I make more types
        return default

    def raise_if_err(
        self,
        *,
        exception_type: Optional[type[Exception]] = Exception,
        prepend_default_message: bool = True,
        force_default_message: bool = False,
        default_message: str = ""
    ):
        if self.return_code is ReturnCode.SUCCESS:
            return
        if prepend_default_message:
            err = self.err_str(default_message)
            err = linesep + err if err else ""
            msg = default_message + err
        else:
            msg = default_message if force_default_message \
            else self.err_str(default_message)
        if not exception_type:
            exception_type = Exception
        raise exception_type(msg)

    def __str__(self):
        return f"[\n\tRETURN_CODE: {self.return_code.name}\n\tOUT: {self.out_str()}\n\tERR: {self.err_str()}\n]"
