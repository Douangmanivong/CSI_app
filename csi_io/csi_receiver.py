# csi_io/csi_receiver.py
# TCP receiver for CSI data packets from OpenWRT router
# receives raw bytes and emits signal to parser
# logs connection status using logger instance

import socket
import time
from PyQt5.QtCore import QThread
from config.settings import HOST_ID, PORT


class CSIReceiver(QThread):
    def __init__(self, signals, logger, stop_event):
        super().__init__()
        self.signals = signals
        self.logger = logger
        self.stop_event = stop_event

        # if self.logger:
        #     self.logger.success(__file__, "<__init__>")

    def run(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
                server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server_socket.bind((HOST_ID, PORT))
                server_socket.listen(1)

                # if self.logger:
                #     self.logger.success(__file__, "<run>: server started")

                last_no_client_log = time.time()

                while not self.stop_event.is_set():
                    server_socket.settimeout(1.0)
                    try:
                        client_socket, addr = server_socket.accept()
                    except socket.timeout:
                        now = time.time()
                        if now - last_no_client_log >= 10:
                            if self.logger:
                                self.logger.failure(__file__, "<run>: no client connected")
                            last_no_client_log = now
                        continue

                    # if self.logger:
                    #     self.logger.success(__file__, "<run>: client connected")

                    with client_socket:
                        last_data_time = time.time()
                        last_no_data_log = time.time()

                        while not self.stop_event.is_set():
                            try:
                                packet = client_socket.recv(4096)
                                now = time.time()

                                if not packet:
                                    if self.logger:
                                        self.logger.failure(__file__, "<run>: client disconnected")
                                    break

                                self.signals.csi_data.emit(packet, now)
                                last_data_time = now

                                # if self.logger:
                                #     self.logger.success(__file__, "<run>: data received")

                            except socket.error:
                                if self.logger:
                                    self.logger.failure(__file__, "<run>: socket error")
                                break

                            now = time.time()
                            if now - last_data_time >= 5 and now - last_no_data_log >= 5:
                                if self.logger:
                                    self.logger.failure(__file__, "<run>: no data received for 5s")
                                last_no_data_log = now

            if not self.stop_event.is_set():
                if self.logger:
                    self.logger.failure(__file__, "<run>: server socket closed unexpectedly")
            else:
                if self.logger:
                    self.logger.success(__file__, "<run>: server stopped")

        except Exception:
            if self.logger:
                self.logger.failure(__file__, "<run>: fatal error")
