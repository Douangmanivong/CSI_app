# remote/remote_device.py
# abstract remote device controller using SSH
# inherits QThread, class must be specialized for each remote device
# defines methods for connecting and checking device

from PyQt5.QtCore import QThread
from remote.ssh_manager import SSHManager

from PyQt5.QtCore import QThread
from remote.ssh_manager import SSHManager
from abc import ABC, abstractmethod

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

    @abstractmethod
    def run(self):
        pass

    def connect(self):
        self.connected = self.ssh.connect()
        if not self.connected and self.logger:
            self.logger.failure(__file__, "<connect>: SSH connection failed")
        return self.connected
