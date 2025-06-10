# io/csi_receiver.py
# TCP receiver for CSI data packets from OpenWRT router
# receives raw bytes and emits signal to parser
# logs connection status using logger instance

import socket
import time
from PyQt5.QtCore import QThread
from config.settings import HOST_ID, PORT

class CSIReceiver(QThread):
    def __init__(self, signals, buffer, mutex, logger, stop_event):
        super().__init__()
        self.signals = signals
        self.buffer = buffer
        self.mutex = mutex
        self.logger = logger
        self.stop_event = stop_event

    def run(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
                server_socket.bind((HOST_ID, PORT))
                server_socket.listen(1)
                self.logger.success(__file__)

                while not self.stop_event.is_set():
                    try:
                        client_socket, addr = server_socket.accept()
                        with client_socket:
                            self.logger.success(__file__)
                            while not self.stop_event.is_set():
                                packet = client_socket.recv(4096)
                                if not packet:
                                    break
                                timestamp = time.time()
                                self.signals.csi_data.emit(packet, timestamp)

                    except socket.error as e:
                        self.logger.failure(__file__)
                        break
        
        except Exception as e:
            self.logger.failure(__file__)