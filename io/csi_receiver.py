# io/csi_receiver.py
# TCP receiver for CSI data packets from OpenWRT router
# receives raw bytes and emits signal to parser
# logs connection status using logger instance

import socket
import time
from PyQt5.QtCore import QThread
from config.settings import HOST_ID, PORT

class CSIReceiver(QThread):
    def __init__(self, signals, logger):
        super().__init__()
        self.signals = signals
        self.logger = logger
        self.running = False

    def start_socket_server(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
                server_socket.bind((HOST_ID, PORT))
                server_socket.listen(1)
                self.logger.success(__file__)  # Connection setup successful
                print(f"Server started on port {PORT}")

                while self.running:
                    try:
                        client_socket, addr = server_socket.accept()
                        with client_socket:
                            self.logger.success(__file__)  # Client connected
                            print(f"Connection from {addr}")
                            while self.running:
                                packet = client_socket.recv(4096)
                                if not packet:
                                    break
                                if packet:
                                    # Emit signal directly to parser with timestamp
                                    timestamp = time.time()
                                    self.signals.csi_data.emit(packet, timestamp)
                                
                    except socket.error as e:
                        self.logger.failure(__file__)
                        print(f"Socket error: {e}")
                        break
                        
        except Exception as e:
            self.logger.failure(__file__)
            print(f"Failed to start server: {e}")

    def run(self):
        self.running = True
        self.start_socket_server()

    def stop(self):
        self.running = False
        self.quit()
        self.wait()