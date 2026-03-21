from abc import ABC
from subprocess import PIPE, Popen
from typing import Optional, Union

from utils.return_value import ReturnCode, ReturnObject, StdResult


class CommandRunner(ABC):
    @classmethod
    def run_command(
        cls,
        command: Union[str, list[str]],
        log_command: bool = True,
        timeout: Optional[int] = None
    ) -> ReturnObject[StdResult]:
        if log_command:
            print(f"Running command: {command}")

        process = Popen(command, shell=True, stdout=PIPE, stderr=PIPE)
        if timeout:
            result = StdResult(process.communicate(timeout=timeout))
        else:
            result = StdResult((process.stdout, process.stderr))

        _, err = result.result()
        if err:
            return ReturnObject(ReturnCode.FAILURE, result)
        return ReturnObject(ReturnCode.SUCCESS, result)
