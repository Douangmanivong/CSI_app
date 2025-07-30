# processing/rpi4_parser.py
# parser for BCM43455c0 chipset (Raspberry Pi 4) with protobuf data
# receives csi_data signal with protobuf-encoded CSI packets from port 4400
# parses protobuf format using csi_pb2.NexmonData
# stores raw CSI data in shared circular buffer for downstream processing

import numpy as np
from collections import deque
from processing.csi_parser import CSIParser
import proto.csi_pb2 as csi_pb2


class RPI4Parser(CSIParser):
    NULL_SUBCARRIERS_256 = [0, 1, 2, 3, 4, 5, 127, 128, 129, 130, 131, 251, 252, 253, 254, 255]
    
    def __init__(self, signals, logger, buffer, mutex, stop_event):
        super().__init__()
        self.signals = signals
        self.logger = logger
        self.buffer = buffer
        self.mutex = mutex
        self.stop_event = stop_event
        
        self.is_setup_complete = False
        self.internal_queue = deque()
        self.packet_count = 0
        
        self.signals.csi_data.connect(self.on_new_data)

    def run(self):
        while not self.stop_event.is_set():
            if self.internal_queue:
                self.process_queued_data()
            self.msleep(1)

    def on_new_data(self, data: bytes, timestamp: float) -> None:
        try:
            if len(data) > 0:
                self.internal_queue.append((data, timestamp))
                if not self.is_setup_complete:
                    self.setup(timestamp)
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<on_new_data>: failed to queue data - {e}")

    def setup(self, timestamp: float):
        if self.is_setup_complete:
            return
            
        try:
            self.start_time = timestamp
            self.is_setup_complete = True
            
            if self.logger:
                self.logger.success(__file__, "<setup>: RPi4 protobuf parser initialized")
                
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<setup>: setup failed - {e}")

    def process_queued_data(self):
        while self.internal_queue:
            try:
                data, timestamp = self.internal_queue.popleft()
                self.parse_protobuf_packet(data, timestamp)
                
            except Exception as e:
                if self.logger:
                    self.logger.failure(__file__, f"<process_queued_data>: failed to process packet - {e}")

    def parse_protobuf_packet(self, data: bytes, timestamp: float):
        try:
            if len(data) < 10:
                if self.logger:
                    self.logger.failure(__file__, f"<parse_protobuf_packet>: packet too small ({len(data)} bytes)")
                return
                
            nexmon_data = csi_pb2.NexmonData()
            
            try:
                nexmon_data.ParseFromString(data)
            except Exception as e:
                if self.logger:
                    self.logger.failure(__file__, f"<parse_protobuf_packet>: protobuf parsing failed - {e}, packet size: {len(data)}")
                return
            
            self.packet_count += 1
            
            if self.logger and self.packet_count % 1000 == 0:
                mac_addr = ':'.join(['{}{}'.format(a, b) for a, b in zip(*[iter('{:012x}'.format(nexmon_data.source_mac))]*2)])
                self.logger.success(__file__, f"<parse>: seq={nexmon_data.seq_num}, MAC={mac_addr}, RSSI={nexmon_data.rssi}")
            
            complex_csi = []
            for csi_element in nexmon_data.csi:
                complex_csi.append(csi_element.real + 1j * csi_element.imaginary)
            
            if len(complex_csi) == 0:
                if self.logger:
                    self.logger.failure(__file__, "<parse_protobuf_packet>: empty CSI data")
                return
            
            for null_carrier in self.NULL_SUBCARRIERS_256:
                if null_carrier < len(complex_csi):
                    complex_csi[null_carrier] = 0
            
            complex_array = np.array(complex_csi, dtype=np.complex64)
            raw_csi = complex_array.tobytes()
            
            relative_time = timestamp - self.start_time
            
            antenna_id = 0
            
            csi_packet = {
                'antenna': antenna_id,
                'timestamp': relative_time,
                'raw_csi': raw_csi
            }
            
            self.buffer.put(csi_packet, self.mutex)
            
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<parse_protobuf_packet>: parsing failed - {e}")

    def reset(self):
        self.internal_queue.clear()
        self.start_time = 0.0
        self.is_setup_complete = False
        self.packet_count = 0

    def is_valid_subcarrier(self, subcarrier: int) -> bool:
        return 0 <= subcarrier <= 255

    def is_valid_antenna(self, antenna: int) -> bool:
        return antenna == 0

    def get_csi_matrix_shape(self):
        return (256,)