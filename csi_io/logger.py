# io/logger.py
# logger class with a logs signal for debugging
# instantiate Logger once in main_window to avoid multiple instances across threads
# to use Logger in other classes, import it and pass the instance in their constructor
# def __init__(self, logger): self.logger = logger
# use logger.success(__file__, "custom message") or logger.failure(__file__, "error details")

from PyQt5.QtCore import QObject, pyqtSignal
from datetime import datetime
import os


class Logger(QObject):
    logs = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def _format_log(self, filename: str, status: str, msg: str = "") -> str:
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        base_name = os.path.basename(filename)
        log = f"[{base_name}:{time_str}:{status}]"
        if msg:
            log += f" {msg}"
        return log

    def success(self, filename: str, msg: str = ""):
        log_str = self._format_log(filename, "success", msg)
        print(log_str)
        self.logs.emit(log_str)

    def failure(self, filename: str, msg: str = ""):
        log_str = self._format_log(filename, "failure", msg)
        print(log_str)
        self.logs.emit(log_str)
