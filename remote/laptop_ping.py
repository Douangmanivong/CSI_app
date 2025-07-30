# remote/laptop_ping.py
# pings AP at given frequency

import time
import subprocess
from PyQt5.QtCore import QThread
import config.settings as Settings


class LaptopPing(QThread):
    def __init__(self, logger, stop_event):
        super().__init__()
        self.logger = logger
        self.stop_event = stop_event
        self.ping_active = False
        self.ping_frequency = Settings.PING_FREQUENCY
        self.router_ip = Settings.Router_IP
    
    def start_ping(self):
        if not self.ping_active:
            self.ping_active = True
            if self.logger:
                self.logger.success(__file__, f"<start_ping>: Ping started to {self.router_ip}")
    
    def stop_ping(self):
        if self.ping_active:
            self.ping_active = False
            if self.logger:
                self.logger.success(__file__, f"<stop_ping>: Ping stopped to {self.router_ip}")
    
    def toggle_ping(self):
        if self.ping_active:
            self.stop_ping()
        else:
            self.start_ping()
    
    def run(self):
        while not self.stop_event.is_set():
            if self.ping_active:
                self._perform_ping()
                time.sleep(1.0 / self.ping_frequency)
            else:
                time.sleep(0.1)
    
    def _perform_ping(self):
        try:
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '2', self.router_ip],
                capture_output=True,
                text=True,
                timeout=3
            )
            
            if result.returncode == 0:
                output = result.stdout
                if "time=" in output:
                    time_part = output.split("time=")[1].split(" ")[0]
                else:
                    if self.logger:
                        self.logger.failure(__file__, f"<_perform_ping>: Ping successful but no time found")
            else:
                if self.logger:
                    self.logger.failure(__file__, f"<_perform_ping>: Ping failed to {self.router_ip}")
                    
        except subprocess.TimeoutExpired:
            if self.logger:
                self.logger.failure(__file__, f"<_perform_ping>: Ping timeout to {self.router_ip}")
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<_perform_ping>: {str(e)}")
    
    def is_ping_active(self):
        return self.ping_active