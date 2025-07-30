# processing/bcm4366c0_parser.py
# parser for bcm4366c0 broadcom chips
# receives csi_data signal, accumulates 332-byte packets
# parses timestamp and raw CSI bytes
# stores raw CSI data in shared circular buffer for downstream processing

import struct
from collections import deque
from processing.csi_parser import CSIParser


class BCM4366C0Parser(CSIParser):
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
        self.is_setup_complete = False

        self.internal_queue = deque()
        self.internal_buffer = bytearray()

        self.signals.csi_data.connect(self.on_new_data)

    def run(self):
        while not self.stop_event.is_set():
            if self.internal_queue:
                self.process_queued_data()
            self.msleep(1)

    def on_new_data(self, data: bytes, timestamp: float) -> None:
        try:
            if len(data) >= 4:
                magic_number = struct.unpack('<I', data[:4])[0]
                if self.is_setup_complete and magic_number in (self.MAGIC_NUM_MICRO, self.MAGIC_NUM_NANO):
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

                    raw_csi = self.internal_buffer[self.DATA_INDEX:self.DATA_INDEX + self.DATA_SIZE_BYTES]

                    csi_packet = {
                        'antenna': antenna,
                        'timestamp': relative_time,
                        'raw_csi': raw_csi
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

    def reset(self):
        self.internal_queue.clear()
        self.internal_buffer.clear()
        self.time_shift_power = 0
        self.start_time = 0.0
        self.is_setup_complete = False

    def is_valid_subcarrier(self, subcarrier: int) -> bool:
        return 0 <= subcarrier <= 63

    def is_valid_antenna(self, antenna: int) -> bool:
        return 0 <= antenna <= 2