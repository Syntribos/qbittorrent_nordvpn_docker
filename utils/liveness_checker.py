import random
import re
import socket
import struct
from datetime import datetime
from multiprocessing import Manager, Process
from multiprocessing.managers import DictProxy
from time import sleep
from typing import Callable, Optional, TypeAlias

from utils.command_runner import CommandRunner
from utils.nord import Nord
from utils.return_value import ReturnCode, ReturnObject

PING_COMMAND = "ping -c 1 -w 1 8.8.8.8"
PING_REGEX_PATTERN = "transmitted, (\\d+) received"
PING_REGEX = re.compile(PING_REGEX_PATTERN)

TRACKERS = [
    ("open.tracker.cl", 1337),
    ("tracker.ololosh.space", 6969),
    ("tracker-udp.gbitt.info", 80),
    ("open.demonii.com", 1337),
    ("open.dstud.io", 6969),
    ("explodie.org", 6969),
    ("exodus.desync.com", 6969),
    ("open.stealth.si", 80),
    ("tracker.torrent.eu.org", 451),
    ("tracker.opentrackr.org", 1337)
]

LivenessFunc: TypeAlias = Callable[["LivenessTaskManager", str, bool], None]
LivenessTasks: TypeAlias = dict[str, "LivenessTask"]
LivenessResult: TypeAlias = Optional[ReturnObject[str]]


class LivenessTask:
    def __init__(self, key: str, task: LivenessFunc):
        self.key = key
        self.task = task

    def get_process(self, manager: "LivenessTaskManager", log_commands: bool):
        return Process(target=self.task, args=[manager, self.key, log_commands])


class LivenessTaskManager:
    def __init__(self, liveness_tasks: LivenessTasks, task_timeout: int):
        self.liveness_tasks = liveness_tasks
        self.task_timeout = task_timeout
        self._manager = Manager()
        self.liveness_results: DictProxy[str, LivenessResult] = self._manager.dict()
        self._running = False

    def run_liveness_check(self, log_commands: bool) -> ReturnObject[str]:
        if self._running:
            return ReturnObject(ReturnCode.UNKNOWN, "Liveness can't be run while already running.")

        self._init_results_dict()
        self._running = True
        start = datetime.now()
        try:
            tasks = [x.get_process(self, log_commands) for x in self.liveness_tasks.values()]

            for task in tasks:
                task.start()
            for task in tasks:
                time_diff = (datetime.now() - start).total_seconds()
                time_left = self.task_timeout - time_diff
                task.join(time_left)
                if task.is_alive():
                    task.kill()

            empty_results = [f"\t{x}" for x, y in self.liveness_results.items() if y is None]
            if empty_results:
                err = "ERROR: the following tasks were not completed:\n"
                err += "\n".join(empty_results)
                return ReturnObject(ReturnCode.FAILURE, err)

            successes = []
            failures = []
            for key, result in self.liveness_results.items():
                if result is None:
                    self._running = False
                    raise Exception("This should never happen as code should handle None results before this point. Hopefully this is just for type checking!")
                if result.return_code is not ReturnCode.SUCCESS:
                    failures.append(f"Task {key} FAILED with result {result.return_code} and message {result.value()}")
                    continue
                message = f" with message {result.value()}" if result.value() else ""
                successes.append(f"Task {key} succeeded{message}")

            if failures:
                return ReturnObject(ReturnCode.FAILURE, "\n".join(successes + failures))
            return ReturnObject(ReturnCode.SUCCESS, "\n".join(successes))
        finally:
            self._running = False

    def set_task_result(self, task_key: str, result: ReturnObject[str]):
        self.liveness_results[task_key] = result

    def _init_results_dict(self):
        if self._running:
            return
        self.liveness_results.clear()
        for task_key in self.liveness_tasks:
            self.liveness_results[task_key] = None


class LivenessChecker(CommandRunner):
    def __init__(
            self,
            nord_manager: Nord,
            failures_per_nord_kick: int = 5,
            kicks_per_abort: int = 3,
            task_timeout: int = 240,
            sleep_seconds: int = 300,
            log_commands: bool = False,
            log_results: bool = False
    ):
        self.nord_manager = nord_manager
        self.failures_per_nord_kick = failures_per_nord_kick
        self.kicks_per_abort = kicks_per_abort
        self.task_timeout = task_timeout
        self.sleep_seconds = sleep_seconds
        self.log_commands = log_commands
        self.log_results = log_results

    def start(self) -> int:
        tasks = [
            LivenessTask("trackers", self._check_udp_trackers),
            LivenessTask("ping", self._ping),
            LivenessTask("tables", self._check_tables)
        ]

        liveness_tasks: LivenessTasks = {}
        for task in tasks:
            liveness_tasks[task.key] = task
        liveness_task_manager = LivenessTaskManager(liveness_tasks, self.task_timeout)

        failures = 0 if self._run_check(liveness_task_manager) else 1
        failure_streaks = 0
        while True:
            sleep(self.sleep_seconds)

            if self._run_check(liveness_task_manager):
                failures = 0
                failure_streaks = 0
                continue

            failures += 1
            if failures >= 10:
                failure_streaks += 1
                failures = 0
                self.nord_manager.reset_nord()

            if failure_streaks >= self.kicks_per_abort:
                return 1

    def _run_check(self, liveness_task_manager: LivenessTaskManager) -> bool:
        result = liveness_task_manager.run_liveness_check(self.log_commands)
        if result.return_code is ReturnCode.SUCCESS:
            if self.log_results:
                print(result.value())
            return True

        print(result.value())
        return False

    def _ping(self, manager: LivenessTaskManager, task_key: str, log_commands: bool) -> None:
        result = self.run_command(PING_COMMAND, log_command=log_commands)

        result.raise_if_err(exception_type=RuntimeError, default_message="ping command failed.")

        ping_output = result.out_str()
        matches = PING_REGEX.findall(ping_output)
        if not matches:
            result = ReturnObject(ReturnCode.FAILURE, f"Couldn't parse PING output.\n\t{ping_output}")
            manager.set_task_result(task_key, result)
            return

        if str(matches[0]) == "1":
            result = ReturnObject(ReturnCode.SUCCESS)
        else:
            result = ReturnObject(ReturnCode.FAILURE, f"PING command did not complete correctly with following output:\n{ping_output}")
        manager.set_task_result(task_key, result)

    def _check_tables(self, manager: LivenessTaskManager, task_key: str, log_commands: bool) -> None:
        cmd = "ip route show table 205"
        expected_ip = "10.5.0.1"
        result = self.run_command(cmd, log_command=log_commands)
        if result.return_code != ReturnCode.SUCCESS:
            cmd_result = ReturnObject(ReturnCode.FAILURE, result.err_str())
            manager.set_task_result(task_key, cmd_result)

        valid_tables = expected_ip in result.out_str()
        if valid_tables:
            cmd_result = ReturnObject(ReturnCode.SUCCESS, result.out_str())
            manager.set_task_result(task_key, cmd_result)
            return

        cmd_result = ReturnObject(ReturnCode.FAILURE, f"Expected value [{expected_ip}] not found in result str: [{result.out_str()}]")
        manager.set_task_result(task_key, cmd_result)
        return

    def _check_udp_trackers(self, manager: LivenessTaskManager, task_key: str, log_commands: bool) -> None:
        for tracker in TRACKERS:
            if log_commands:
                print(f"Attempting to ping {tracker=}")
            if self._send_to(tracker):
                result = ReturnObject(ReturnCode.SUCCESS, f"{tracker[0]}:{tracker[1]} connection success!")
                manager.set_task_result(task_key, result)
                return

        result = ReturnObject(ReturnCode.FAILURE, "Couldn't connect to any trackers.")
        manager.set_task_result(task_key, result)

    def _send_to(self, tracker: tuple[str, int]) -> bool:
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            connection_id = 0x41727101980
            action = 0
            transaction_id = random.randint(0, 0xFFFFFFFF)
            packet = struct.pack(">QII", connection_id, action, transaction_id)
            sock.sendto(packet, tracker)
            response = sock.recv(16)
            return len(response) == 16
        except Exception:
            return False
        finally:
            if sock:
                sock.close()
