# processing/csi_magnitude_processor.py
# CSI magnitude processor thread
# specialization of abstract CSIProcessor for magnitude analysis
# applies threshold detection on magnitudes per subcarrier
# emits fft_data signal for chart visualization
# emits threshold_exceeded signal when thresholds are breached
# moving average filtering using deque for performance

import numpy as np
import time
import math
import struct
from collections import deque
from config.settings import THRESHOLD_VALUE, THRESHOLD_DISABLED, SUBCARRIER
from processing.csi_processor import CSIProcessor
from core.buffer import CircularBuffer

class CSIMagnitudeProcessor(CSIProcessor):
    def __init__(self, signals, buffer, mutex, logger, stop_event, batch_size=10, ma_window=5):
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
                # if self.logger:
                #     self.logger.success(__file__, f"<process_batch>: t0 initialized at {self.t0}")

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
            magnitude_value = magnitude_matrix[0, SUBCARRIER]
            if magnitude_value > self.threshold_value:
                relative_time = timestamp - self.t0 if self.t0 else timestamp
                message = f"value={magnitude_value:.2f}, time={relative_time:.2f}s"

                self.signals.threshold_exceeded.emit(message)

                # if self.logger:
                #     self.logger.success(__file__, f"<_detect_thresholds>: threshold exceeded on subcarrier {SUBCARRIER}")

        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<_detect_thresholds>: {e}")

    def _emit_fft_data(self, magnitude_matrix, timestamp):
        try:
            if self.t0 is None:
                self.t0 = timestamp
                # if self.logger:
                #     self.logger.success(__file__, f"<_emit_fft_data>: t0 initialized at {self.t0}")

            relative_time = timestamp - self.t0
            selected_magnitude = magnitude_matrix[0, SUBCARRIER]
            self.signals.fft_data.emit({
                'time': relative_time,
                'magnitude': float(selected_magnitude)
            })

            # if self.logger:
            #     self.logger.success(__file__, f"<_emit_fft_data>: subcarrier {SUBCARRIER} magnitude sent to chart")

        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<_emit_fft_data>: {e}")

    def update_threshold(self, new_threshold):
        try:
            if new_threshold == THRESHOLD_DISABLED:
                self.threshold_value = THRESHOLD_DISABLED
            else:
                self.threshold_value = float(new_threshold)

            # if self.logger:
            #     self.logger.success(__file__, "<update_threshold>: new threshold")

        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<update_threshold>: failed to get value: {e}")

    def extract_magnitude_data(self, data: bytes) -> np.ndarray:
        if len(data) != 256:
            self.logger.failure(__file__, "<extract_magnitude_data>: wrong data length")
            raise ValueError(f"Expected 256 bytes, got {len(data)}")

        try:
            count = 64
            M = 12
            E = 6
            nbits = 10
            e_p = 1 << (E - 1)
            e_zero = -M
            maxbit = -e_p
            k_tof_unpack_sgn_mask = 1 << 31
            ri_mask = (1 << (M - 1)) - 1
            E_mask = (1 << E) - 1
            sgnr_mask = (1 << (E + 2 * M - 1))
            sgni_mask = sgnr_mask >> M

            He = [0] * 256
            Hout = [0] * 512

            for i in range(count):
                h_bytes = data[4*i:4*i+4]
                h = struct.unpack('<I', h_bytes)[0]

                v_real = (h >> (E + M)) & ri_mask
                v_imag = (h >> E) & ri_mask
                e = h & E_mask

                if e >= e_p:
                    e -= (e_p << 1)

                He[i] = e
                x = v_real | v_imag

                if x:
                    m = 0xffff0000
                    b = 0xffff
                    s = 16
                    while s > 0:
                        if x & m:
                            e += s
                            x >>= s
                        s >>= 1
                        m = (m >> s) & b
                        b >>= s

                    if e > maxbit:
                        maxbit = e

                if h & sgnr_mask:
                    v_real |= k_tof_unpack_sgn_mask
                if h & sgni_mask:
                    v_imag |= k_tof_unpack_sgn_mask

                Hout[i << 1] = v_real
                Hout[(i << 1) + 1] = v_imag

            shft = nbits - maxbit
            for i in range(count * 2):
                e = He[i >> 1] + shft
                sgn = 1
                if Hout[i] & k_tof_unpack_sgn_mask:
                    sgn = -1
                    Hout[i] &= ~k_tof_unpack_sgn_mask

                if e < e_zero:
                    Hout[i] = 0
                elif e < 0:
                    Hout[i] = Hout[i] >> (-e)
                else:
                    Hout[i] = Hout[i] << e

                Hout[i] *= sgn

            magnitudes = np.zeros(count)
            for i in range(count):
                real_part = Hout[i * 2]
                imag_part = Hout[i * 2 + 1]
                magnitudes[i] = math.sqrt(real_part**2 + imag_part**2)

            half = count // 2
            magnitudes = np.flip(magnitudes)
            magnitudes[:half] = np.flip(magnitudes[:half])
            magnitudes[half:] = np.flip(magnitudes[half:])

            return magnitudes

        except Exception as e:
            self.logger.failure(__file__, "<extract_magnitude_data>: failed to return fft")
            raise
