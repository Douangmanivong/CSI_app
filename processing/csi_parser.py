# processing/csi_parser.py
from abc import ABC, abstractmethod
from PyQt5.QtCore import QThread


class CSIParser(QThread):
    def __init__(self):
        super().__init__()
        self.start_time = 0.0

    @abstractmethod
    def on_new_data(self, data: bytes, timestamp: float) -> None:
        pass

    @abstractmethod
    def is_valid_subcarrier(self, subcarrier: int) -> bool:
        pass

    @abstractmethod
    def is_valid_antenna(self, antenna: int) -> bool:
        pass

    def get_start_time(self) -> float:
        return self.start_time