# remote/rpi_device.py
# raspberry Pi controller
# starts and stops a continuous ping to the router via SSH

from remote.remote_device import RemoteDevice
from PyQt5.QtCore import pyqtSlot
from config.settings import RPi_IP, RPi_ID, RPi_PASSWORD

class RPiDevice(RemoteDevice):
    def __init__(self, signals, stop_event, logger=None):
        super().__init__(RPi_IP, RPi_ID, stop_event, password=RPi_PASSWORD, logger=logger)
        self.signals = signals

    @pyqtSlot()
    def request_connect(self):
        if self.logger:
            self.logger.success(__file__, "trying to connect to RPi...")
        try:
            self.connect()
            if self.logger:
                self.logger.success(__file__, "<connect>: connected to RPi")
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, "<connect to RPi> failed: {e}")

    @pyqtSlot()
    def request_start_ping(self):
        if not self.connected:
            if self.logger:
                self.logger.failure(__file__, "<start ping>: device not connected")
            return
        try:
            cmd = "ping 192.168.50.1 -i 0.05 > /dev/null 2>&1 & echo $!"
            stdout, stderr = self.ssh.exec(cmd)
            self.ping_pid = stdout.strip()
            if self.logger:
                self.logger.success(__file__, f"<start ping>: started with PID {self.ping_pid}")
                if stderr:
                    self.logger.failure(__file__, f"<start ping stderr>: {stderr.strip()}")
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<start ping> failed: {e}")

    @pyqtSlot()
    def request_stop_ping(self):
        if not self.connected:
            if self.logger:
                self.logger.failure(__file__, "<stop ping>: device not connected")
            return
        try:
            if hasattr(self, "ping_pid"):
                cmd = f"kill {self.ping_pid}"
                stdout, stderr = self.ssh.exec(cmd)
                if self.logger:
                    self.logger.success(__file__, f"<stop ping>: stopped PID {self.ping_pid}")
                    if stderr:
                        self.logger.failure(__file__, f"<stop ping stderr>: {stderr.strip()}")
            else:
                if self.logger:
                    self.logger.failure(__file__, "<stop ping>: no PID recorded")
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<stop ping> failed: {e}")