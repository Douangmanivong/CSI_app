# processing/csi_magnitude_processor_rpi4.py
# CSI magnitude processor thread for RPi4
# specialization of abstract CSIProcessor for magnitude analysis
# applies threshold detection on magnitudes per subcarrier
# emits fft_data signal for chart visualization
# emits threshold_exceeded signal when thresholds are breached
# moving average filtering using deque for performance

import numpy as np
import time
from collections import deque
from config.settings import THRESHOLD_VALUE, THRESHOLD_DISABLED, SUBCARRIER_RANGE, SUBCARRIER
from processing.csi_processor import CSIProcessor


class CSIMagnitudeProcessor(CSIProcessor):
    def __init__(self, signals, buffer, mutex, logger, stop_event, ma_window, batch_size=10):
        super().__init__(signals, buffer, mutex, logger, stop_event, batch_size)
        self.threshold_value = THRESHOLD_VALUE
        self.ma_window = ma_window
        self.ma_buffer = deque(maxlen=ma_window)

    def process_batch(self, data_batch, time_batch):
        try:
            all_magnitudes = []
            latest_timestamp = time.time()

            if self.t0 is None:
                self.t0 = latest_timestamp

            for csi_packet, _ in zip(data_batch, time_batch):
                if isinstance(csi_packet, dict) and 'raw_csi' in csi_packet:
                    magnitudes = self.extract_magnitude_data(csi_packet['raw_csi'])
                    all_magnitudes.append(magnitudes)

            if not all_magnitudes:
                if self.logger:
                    self.logger.failure(__file__, "<process_batch>: no magnitudes found")
                return

            for spectrum in all_magnitudes:
                self.ma_buffer.append(spectrum)

            if len(self.ma_buffer) < self.ma_window:
                return

            magnitude_matrix = np.mean(np.stack(self.ma_buffer), axis=0, keepdims=True)

            self._detect_thresholds(magnitude_matrix, latest_timestamp)
            self._emit_fft_data(magnitude_matrix, latest_timestamp)

        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<process_batch>: {e}")

    def _detect_thresholds(self, magnitude_matrix, timestamp):
        if self.threshold_value == THRESHOLD_DISABLED:
            return

        try:
            # magnitude_value = magnitude_matrix[0, SUBCARRIER]           uncomment to use one subcarrier
            start, end = SUBCARRIER_RANGE
            magnitude_value = np.mean(magnitude_matrix[0, start:end])   # comment to use one subcarrier
            if magnitude_value > self.threshold_value:
                relative_time = timestamp - self.t0 if self.t0 else timestamp
                message = f"value={magnitude_value:.2f}, time={relative_time:.2f}s"

                self.signals.threshold_exceeded.emit(message)

        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<_detect_thresholds>: {e}")

    def _emit_fft_data(self, magnitude_matrix, timestamp):
        try:
            if self.t0 is None:
                self.t0 = timestamp

            relative_time = timestamp - self.t0
            # selected_magnitude = magnitude_matrix[0, SUBCARRIER]           same as above
            start, end = SUBCARRIER_RANGE
            selected_magnitude = np.mean(magnitude_matrix[0, start:end])
            self.signals.fft_data.emit({
                'time': relative_time,
                'magnitude': float(selected_magnitude)
            })

        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<_emit_fft_data>: {e}")

    def update_threshold(self, new_threshold):
        try:
            if new_threshold == THRESHOLD_DISABLED:
                self.threshold_value = THRESHOLD_DISABLED
            else:
                self.threshold_value = float(new_threshold)

        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<update_threshold>: failed to get value: {e}")

    def extract_magnitude_data(self, data: bytes) -> np.ndarray:
        try:
            complex_array = np.frombuffer(data, dtype=np.complex64)
            
            if len(complex_array) != 256:
                if self.logger:
                    self.logger.failure(__file__, f"<extract_magnitude_data>: expected 256 complex values, got {len(complex_array)}")
                raise ValueError(f"Expected 256 complex values, got {len(complex_array)}")
            
            magnitudes = np.abs(complex_array)
            
            return magnitudes

        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<extract_magnitude_data>: failed to extract magnitudes - {e}")
            raise