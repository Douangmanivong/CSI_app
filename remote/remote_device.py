# remote/remote_device.py
# Abstract base class for remote devices controlling CSI collection

from PyQt5.QtCore import QThread
from abc import ABC, abstractmethod
from remote.ssh_manager import SSHManager

class RemoteDevice(QThread):
    def __init__(self, ip, username, stop_event, password=None, keyfile=None, logger=None):
        super().__init__()
        self.ip = ip
        self.username = username
        self.password = password
        self.keyfile = keyfile
        self.logger = logger
        self.stop_event = stop_event
        self.ssh = SSHManager(ip, username, password, keyfile, logger)
        self.connected = False

    def connect_sniffer(self):
        self.connected = self.ssh.connect()
        if not self.connected and self.logger:
            self.logger.failure(__file__, "<connect_to_sniffer>: SSH connection failed")
        return self.connected

    @abstractmethod
    def setup_sniffer(self):
        pass

    @abstractmethod
    def start_stream(self):
        pass

    @abstractmethod
    def save_data(self):
        pass

    @abstractmethod
    def stop_stream(self):
        pass

    def disconnect_sniffer(self):
        self.ssh.close()
        self.connected = False
        if self.logger:
            self.logger.success(__file__, "<disconnect_sniffer>: SSH session closed")

    def run(self):
        pass
