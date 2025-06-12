# processing/csi_parser.py
# CSI parser classes adapted from C++ version for Python/PyQt5 architecture
# base abstract class and BCM4366C0 specialization
# receives csi_data signal, accumulates 332-byte packets, parses CSI data
# stores parsed data in shared circular buffer for processor thread

import struct
import numpy as np
from collections import deque
from PyQt5.QtCore import QThread
import math

class CSIParser(QThread):
    PACKET_SIZE_BYTES = 332
    CSI_SIZE_BYTES = 274
    CSI_INDEX = PACKET_SIZE_BYTES - CSI_SIZE_BYTES
    DATA_INDEX = CSI_INDEX + 18
    DATA_SIZE_BYTES = 256

    MAGIC_NUM_MICRO = 0xA1B2C3D4
    MAGIC_NUM_NANO = 0xA1B23CD4

    CORE_TO_ANTENNA = {0: 2, 1: 0, 2: -1, 3: 1}

    def __init__(self, signals, logger, buffer, mutex, stop_event):
        super().__init__()
        self.signals = signals
        self.logger = logger
        self.buffer = buffer
        self.mutex = mutex
        self.stop_event = stop_event

        self.time_shift_power = 0
        self.start_time = 0.0
        self.is_setup_complete = False

        self.internal_queue = deque()
        self.internal_buffer = bytearray()

        self.signals.csi_data.connect(self.on_new_data)
        self.logger.success(__file__, "<__init__>")

    def run(self):
        self.logger.success(__file__, "<run>: parsing")
        while not self.stop_event.is_set():
            if self.internal_queue:
                self.process_queued_data()
            self.msleep(1)

    def on_new_data(self, data: bytes, timestamp: float) -> None:
        try:
            if len(data) >= 4:
                magic_number = struct.unpack('<I', data[:4])[0]
                if self.is_setup_complete and magic_number in (self.MAGIC_NUM_MICRO, self.MAGIC_NUM_NANO):
                    self.logger.success(__file__, "<on_new_data>: reset triggered")
                    self.reset()
            self.internal_queue.append(data)
            if not self.is_setup_complete:
                self.setup(data)
        except Exception as e:
            self.logger.failure(__file__, "<on_new_data>: failed to append data")
            print(f"Parse error: {e}")

    def setup(self, data: bytes):
        if self.is_setup_complete or len(data) < 32:
            return
        try:
            magic_number = struct.unpack('<I', data[:4])[0]
            self.time_shift_power = 6 if magic_number == self.MAGIC_NUM_MICRO else 9
            time_primary = data[24:28]
            time_secondary = data[28:32]
            self.start_time = self.parse_time(time_primary, time_secondary)
            if self.internal_queue:
                packet = self.internal_queue.popleft()
                self.internal_queue.appendleft(packet[24:])
            self.is_setup_complete = True
            self.logger.success(__file__, "<setup>: MN and format ok")
        except Exception as e:
            self.logger.failure(__file__, "<setup>: setup failed")
            print(f"Setup error: {e}")

    def process_queued_data(self):
        while self.internal_queue or len(self.internal_buffer) >= self.PACKET_SIZE_BYTES:
            if len(self.internal_buffer) < self.PACKET_SIZE_BYTES:
                if self.internal_queue:
                    self.internal_buffer.extend(self.internal_queue.popleft())
                    continue
                else:
                    break

            packet_core = self.internal_buffer[self.CSI_INDEX + 13]
            antenna = self.CORE_TO_ANTENNA.get(packet_core, -1)
            if antenna != -1:
                try:
                    time_primary = self.internal_buffer[0:4]
                    time_secondary = self.internal_buffer[4:8]
                    packet_time = self.parse_time(time_primary, time_secondary)
                    relative_time = packet_time - self.start_time

                    csi_data_bytes = self.internal_buffer[self.DATA_INDEX:self.DATA_INDEX + self.DATA_SIZE_BYTES]
                    magnitudes = self.extract_magnitude_data(csi_data_bytes)

                    csi_packet = {
                        'antenna': antenna,
                        'timestamp': relative_time,
                        'magnitudes': magnitudes,
                        'subcarriers': len(magnitudes)
                    }
                    self.buffer.put(csi_packet, self.mutex)

                except Exception as e:
                    self.logger.failure(__file__, "<process_queued_data>: failed to process")
                    print(f"Packet processing error: {e}")

            self.internal_buffer = self.internal_buffer[self.PACKET_SIZE_BYTES:]

    def parse_time(self, time_primary: bytes, time_secondary: bytes) -> float:
        primary = struct.unpack('<I', time_primary)[0]
        secondary = struct.unpack('<I', time_secondary)[0]
        return primary + secondary / (10 ** self.time_shift_power)

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
            sgnr_mask = 1 << (E + 2 * M - 1)
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
            print(f"Magnitude extraction error: {e}")
            raise

    def reset(self):
        self.internal_queue.clear()
        self.internal_buffer.clear()
        self.time_shift_power = 0
        self.start_time = 0.0
        self.is_setup_complete = False
        self.logger.success(__file__, "<reset>: reset done")

    def get_start_time(self) -> float:
        return self.start_time

    def is_valid_subcarrier(self, subcarrier: int) -> bool:
        return 0 <= subcarrier <= 63

    def is_valid_antenna(self, antenna: int) -> bool:
        return 0 <= antenna <= 2