# processing/csi_parser.py
# CSI parser classes adapted from C++ version for Python/PyQt5 architecture
# base abstract class and BCM4366C0 specialization
# receives csi_data signal, accumulates 332-byte packets, parses CSI data
# stores parsed data in shared circular buffer for processor thread

import struct
import numpy as np
from abc import ABC, abstractmethod
from collections import deque
from PyQt5.QtCore import QObject, QThread
import math

class CSIParser(QObject, ABC):
    """Abstract base class for CSI data parsing"""
    
    def __init__(self, signals, logger, buffer, mutex):
        super().__init__()
        self.signals = signals
        self.logger = logger
        self.buffer = buffer  # Shared circular buffer
        self.mutex = mutex    # Thread synchronization
        
        # Connect to incoming CSI data signal
        self.signals.csi_data.connect(self.on_new_data)
    
    @abstractmethod
    def parse(self, data: bytes) -> None:
        """Parse raw bytes into CSI data"""
        pass
    
    @abstractmethod
    def get_start_time(self) -> float:
        """Get reference start time"""
        pass
    
    @abstractmethod
    def is_valid_subcarrier(self, subcarrier: int) -> bool:
        """Validate subcarrier index"""
        pass
    
    @abstractmethod
    def is_valid_antenna(self, antenna: int) -> bool:
        """Validate antenna index"""
        pass
    
    @abstractmethod
    def on_new_data(self, data: bytes, timestamp: float) -> None:
        """Handle new raw data from receiver"""
        pass


class BCM4366C0Parser(CSIParser, QThread):
    """BCM4366C0 chipset CSI parser implementation"""
    
    # Constants from C++ header
    PACKET_SIZE_BYTES = 332
    CSI_SIZE_BYTES = 274
    CSI_INDEX = PACKET_SIZE_BYTES - CSI_SIZE_BYTES
    DATA_INDEX = CSI_INDEX + 18
    DATA_SIZE_BYTES = 256
    
    # Magic numbers for PCAP detection
    MAGIC_NUM_MICRO = 0xA1B2C3D4
    MAGIC_NUM_NANO = 0xA1B23CD4
    
    # Core to antenna mapping (core 2 is invalid)
    CORE_TO_ANTENNA = {0: 2, 1: 0, 2: -1, 3: 1}
    
    def __init__(self, signals, logger, buffer, mutex):
        super().__init__(signals, logger, buffer, mutex)
        QThread.__init__(self)
        
        # Internal state
        self.time_shift_power = 0
        self.start_time = 0.0
        self.is_setup_complete = False
        
        # Internal buffer and queue for packet assembly
        self.internal_queue = deque()
        self.internal_buffer = bytearray()
        
        self.running = False
        self.logger.success(__file__)  # Parser initialized
    
    def run(self):
        """Thread main loop - processes queued data"""
        self.running = True
        self.logger.success(__file__)  # Parser thread started
        while self.running:
            self.process_queued_data()
            self.msleep(1)  # Small delay to prevent busy waiting
        self.logger.success(__file__)  # Parser thread stopped
    
    def stop(self):
        """Stop the parser thread"""
        self.running = False
        self.quit()
        self.wait()
    
    def on_new_data(self, data: bytes, timestamp: float):
        """Handle new raw data from CSI receiver"""
        try:
            self.parse(data)
        except Exception as e:
            self.logger.failure(__file__)
            print(f"Parse error: {e}")
    
    def parse(self, data: bytes):
        """Parse incoming raw bytes (adapted from C++ version)"""
        # Check for magic number at start of data
        if len(data) >= 4:
            magic_bytes = data[:4]
            magic_number = struct.unpack('<I', magic_bytes)[0]  # Little endian
            
            if (self.is_setup_complete and 
                (magic_number == self.MAGIC_NUM_MICRO or magic_number == self.MAGIC_NUM_NANO)):
                # Reset if we see a new magic number (new PCAP file)
                self.logger.success(__file__)  # New PCAP detected
                self.reset()
        
        # Add data to internal queue
        self.internal_queue.append(data)
        
        # Setup if not done yet
        if not self.is_setup_complete:
            self.setup(data)
        
        # Process all available data
        self.process_queued_data()
    
    def process_queued_data(self):
        """Process data from queue and internal buffer"""
        while self.internal_queue or len(self.internal_buffer) >= self.PACKET_SIZE_BYTES:
            # Fill buffer if not enough data for a complete packet
            if len(self.internal_buffer) < self.PACKET_SIZE_BYTES:
                if self.internal_queue:
                    self.internal_buffer.extend(self.internal_queue.popleft())
                    continue
                else:
                    break
            
            # Extract packet info
            packet_core = self.internal_buffer[self.CSI_INDEX + 13]
            antenna = self.CORE_TO_ANTENNA.get(packet_core, -1)
            
            if antenna != -1:  # Valid antenna (not dead core)
                try:
                    # Parse timestamp
                    time_primary = self.internal_buffer[0:4]
                    time_secondary = self.internal_buffer[4:8]
                    packet_time = self.parse_time(time_primary, time_secondary)
                    relative_time = packet_time - self.start_time
                    
                    # Extract CSI magnitude data
                    csi_data_bytes = self.internal_buffer[self.DATA_INDEX:self.DATA_INDEX + self.DATA_SIZE_BYTES]
                    magnitudes = self.extract_magnitude_data(csi_data_bytes)
                    
                    # Create CSI data structure
                    csi_packet = {
                        'antenna': antenna,
                        'timestamp': relative_time,
                        'magnitudes': magnitudes,
                        'subcarriers': len(magnitudes)
                    }
                    
                    # Store in shared circular buffer
                    self.buffer.put(csi_packet, self.mutex)
                    
                except Exception as e:
                    self.logger.failure(__file__)
                    print(f"Packet processing error: {e}")
            
            # Remove processed packet from buffer
            self.internal_buffer = self.internal_buffer[self.PACKET_SIZE_BYTES:]
    
    def setup(self, data: bytes):
        """Setup parser with PCAP header information"""
        if self.is_setup_complete or len(data) < 32:
            return
        
        try:
            # Extract magic number to determine time precision
            magic_bytes = data[:4]
            magic_number = struct.unpack('<I', magic_bytes)[0]
            
            if magic_number == self.MAGIC_NUM_MICRO:
                self.time_shift_power = 6  # Microseconds
            else:
                self.time_shift_power = 9  # Nanoseconds
            
            # Extract start time from first packet
            if len(data) >= 32:
                time_primary = data[24:28]
                time_secondary = data[28:32]
                self.start_time = self.parse_time(time_primary, time_secondary)
                
                # Remove PCAP header from queued data
                if self.internal_queue:
                    first_packet = self.internal_queue.popleft()
                    modified_packet = first_packet[24:]  # Remove 24-byte header
                    if modified_packet:
                        self.internal_queue.appendleft(modified_packet)
                
                self.is_setup_complete = True
                self.logger.success(__file__)  # Setup completed successfully
        
        except Exception as e:
            self.logger.failure(__file__)
            print(f"Setup error: {e}")
    
    def parse_time(self, time_primary: bytes, time_secondary: bytes) -> float:
        """Parse timestamp from PCAP packet"""
        primary = struct.unpack('<I', time_primary)[0]
        secondary = struct.unpack('<I', time_secondary)[0]
        return primary + secondary / (10 ** self.time_shift_power)
    
    def extract_magnitude_data(self, data: bytes) -> np.ndarray:
        """Extract CSI magnitude data (adapted from C++ algorithm)"""
        if len(data) != 256:
            self.logger.failure(__file__)
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
            
            # Process each 4-byte complex sample
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
                
                # Handle sign bits
                if h & sgnr_mask:
                    v_real |= k_tof_unpack_sgn_mask
                if h & sgni_mask:
                    v_imag |= k_tof_unpack_sgn_mask
                
                Hout[i << 1] = v_real
                Hout[(i << 1) + 1] = v_imag
            
            # Apply scaling
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
            
            # Calculate magnitudes
            magnitudes = np.zeros(count)
            for i in range(count):
                real_part = Hout[i * 2]
                imag_part = Hout[i * 2 + 1]
                magnitudes[i] = math.sqrt(real_part**2 + imag_part**2)
            
            # Apply FFT shift
            half = count // 2
            magnitudes = np.flip(magnitudes)
            magnitudes[:half] = np.flip(magnitudes[:half])
            magnitudes[half:] = np.flip(magnitudes[half:])
            
            return magnitudes
            
        except Exception as e:
            self.logger.failure(__file__)
            print(f"Magnitude extraction error: {e}")
            raise

    def stop(self):
        """Stop the parser thread"""
        try:
            self.running = False
            self.quit()
            self.wait()
            self.logger.success(__file__)  # Parser stopped
            
        except Exception as e:
            self.logger.failure(__file__)
            print(f"Stop error: {e}")
    
    def reset(self):
        """Reset parser state"""
        self.internal_queue.clear()
        self.internal_buffer.clear()
        self.time_shift_power = 0
        self.start_time = 0.0
        self.is_setup_complete = False
        self.logger.success(__file__)  # Parser reset completed
    
    # Validator methods
    def get_start_time(self) -> float:
        return self.start_time
    
    def is_valid_subcarrier(self, subcarrier: int) -> bool:
        return 0 <= subcarrier <= 63
    
    def is_valid_antenna(self, antenna: int) -> bool:
        return 0 <= antenna <= 2