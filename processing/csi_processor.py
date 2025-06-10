# processing/csi_processor.py
# CSI data processor thread
# retrieves CSI packets from circular buffer in batches
# applies threshold detection on magnitudes per subcarrier
# emits fft_data signal for chart visualization
# emits threshold_exceeded signal when thresholds are breached

import numpy as np
import time
from PyQt5.QtCore import QThread
from config.settings import THRESHOLD_VALUE, THRESHOLD_DISABLED

class CSIProcessor(QThread):
    def __init__(self, signals, buffer, mutex, logger, stop_event, batch_size=10):
        super().__init__()
        self.signals = signals
        self.buffer = buffer
        self.mutex = mutex
        self.logger = logger
        self.stop_event = stop_event
        self.batch_size = batch_size
        self.threshold_value = THRESHOLD_VALUE

    def run(self):
        self.logger.success(__file__)
        while not self.stop_event.is_set():
            try:
                if not self._retrieve_batch():
                    self.msleep(10)
            except Exception as e:
                self.logger.failure(__file__)
                self.msleep(100)

    def _retrieve_batch(self):
        buffer_size = self.buffer.size(self.mutex)
        if buffer_size < self.batch_size:
            return False
        data_batch, time_batch = self.buffer.get_batch(self.batch_size, self.mutex)
        if not data_batch:
            return False
        self._process_batch(data_batch, time_batch)
        return True

    def _process_batch(self, data_batch, time_batch):
        all_magnitudes = []
        latest_timestamp = 0
        for csi_packet, timestamp in zip(data_batch, time_batch):
            if isinstance(csi_packet, dict) and 'magnitudes' in csi_packet:
                all_magnitudes.append(csi_packet['magnitudes'])
                latest_timestamp = max(latest_timestamp, timestamp)
        if not all_magnitudes:
            self.logger.failure(__file__)
            return
        magnitude_matrix = np.array(all_magnitudes)
        self._detect_thresholds(magnitude_matrix, latest_timestamp)
        self._emit_fft_data(magnitude_matrix, latest_timestamp)

    def _detect_thresholds(self, magnitude_matrix, timestamp):
        if self.threshold_value == THRESHOLD_DISABLED:
            return

        mean_magnitudes = np.mean(magnitude_matrix, axis=0)
        exceeded_mask = mean_magnitudes > self.threshold_value

        if np.any(exceeded_mask):
            max_exceeded_value = np.max(mean_magnitudes[exceeded_mask])
            message = f"value={max_exceeded_value:.2f}, time={timestamp:.2f}s"
            self.signals.threshold_exceeded.emit(message)
            self.logger.success(__file__)

    def _emit_fft_data(self, magnitude_matrix, timestamp):
        mean_spectrum = np.mean(magnitude_matrix, axis=0)
        self.signals.fft_data.emit({'time': timestamp, 'magnitude': float(np.mean(mean_spectrum))})
        self.logger.success(__file__)

    def update_threshold(self, new_threshold):
        try:
            if new_threshold == THRESHOLD_DISABLED:
                self.threshold_value = THRESHOLD_DISABLED
            else:
                self.threshold_value = float(new_threshold)
            self.logger.success(__file__)
        except Exception as e:
            self.logger.failure(__file__)