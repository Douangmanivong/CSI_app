# processing/csi_processor.py
# abstract CSI data processor thread
# retrieves CSI packets from circular buffer in batches
# defines abstract interface for processing CSI data
# concrete subclasses should implement specific signal extraction (magnitude, phase, Doppler)

from abc import ABC, abstractmethod
import time
from PyQt5.QtCore import QThread


class CSIProcessor(QThread):
    def __init__(self, signals, buffer, mutex, logger, stop_event, batch_size=10):
        super().__init__()
        self.signals = signals
        self.buffer = buffer
        self.mutex = mutex
        self.logger = logger
        self.stop_event = stop_event
        self.batch_size = batch_size
        self.t0 = None

        # if self.logger:
        #     self.logger.success(__file__, "<__init__>")

    def run(self):
        # if self.logger:
        #     self.logger.success(__file__, "<run>: processing")

        while not self.stop_event.is_set():
            try:
                if not self._retrieve_batch():
                    self.msleep(10)
            except Exception as e:
                if self.logger:
                    self.logger.failure(__file__, f"<run>: exception: {e}")
                self.msleep(100)

    def _retrieve_batch(self):
        buffer_size = self.buffer.size(self.mutex)
        if buffer_size < self.batch_size:
            return False

        data_batch, time_batch = self.buffer.get_batch(self.batch_size, self.mutex)
        if not data_batch:
            return False

        self.process_batch(data_batch, time_batch)
        return True

    @abstractmethod
    def process_batch(self, data_batch, time_batch):
        # Process a CSI data batch
        # Should be implemented by concrete subclasses
        pass
