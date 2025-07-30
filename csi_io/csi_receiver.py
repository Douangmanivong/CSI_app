# csi_io/csi_receiver.py
# UDP receiver for CSI data packets from Raspberry Pi (protobuf format)
# receives raw bytes and emits signal to parser
# logs connection status using logger instance

import socket
import time
from PyQt5.QtCore import QThread
from config.settings import PORT


class CSIReceiver(QThread):
    def __init__(self, signals, logger, stop_event):
        super().__init__()
        self.signals = signals
        self.logger = logger
        self.stop_event = stop_event
        self.first_packet_logged = False

    def run(self):
        if self.logger:
            self.logger.success(__file__, f"<run>: starting UDP listener on port {PORT}")

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", PORT))
            sock.settimeout(1.0)

            if self.logger:
                self.logger.success(__file__, f"<run>: bound to 0.0.0.0:{PORT}")

            last_packet_time = None
            start_time = time.time()
            last_no_data_log = start_time

            while not self.stop_event.is_set():
                current_time = time.time()
                
                try:
                    packet, addr = sock.recvfrom(4096)

                    if packet:
                        if not self.first_packet_logged and self.logger:
                            self.logger.success(__file__, f"<run>: first packet received ({len(packet)} bytes) from {addr}")
                            self.first_packet_logged = True

                        self.signals.csi_data.emit(packet, current_time)
                        last_packet_time = current_time

                except socket.timeout:
                    pass
                except Exception as e:
                    if self.logger:
                        self.logger.failure(__file__, f"<run>: socket error - {e}")
                    break

                if last_packet_time is None:
                    time_since_start = current_time - start_time
                    if time_since_start >= 5 and (current_time - last_no_data_log) >= 5:
                        if self.logger:
                            self.logger.failure(__file__, "<run>: no data received for 5s")
                        last_no_data_log = current_time
                else:
                    time_since_last_packet = current_time - last_packet_time
                    if time_since_last_packet >= 5 and (current_time - last_no_data_log) >= 5:
                        if self.logger:
                            self.logger.failure(__file__, "<run>: no data received for 5s")
                        last_no_data_log = current_time

            sock.close()

            if self.logger:
                self.logger.success(__file__, "<run>: UDP listener stopped")

        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<run>: fatal error - {e}")