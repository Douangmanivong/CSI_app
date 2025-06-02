import socket
from threading import Thread
from PyQt5.QtCore import pyqtSignal, QObject

class TCPReceiver(QObject):
    packet_received = pyqtSignal(bytes)
    
    def __init__(self, host='0.0.0.0', port=5555):
        super().__init__()
        self.host = host
        self.port = port
        self.running = False
        
    def start(self):
        self.running = True
        self.thread = Thread(target=self._receive_loop)
        self.thread.start()
        
    def _receive_loop(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen()
            conn, _ = s.accept()
            while self.running:
                data = conn.recv(4096)
                if data:
                    self.packet_received.emit(data)