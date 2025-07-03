# ssh/ssh_scripter.py
# thread to automate SSH control of RPi (ping) and Router (start CSI)
# uses Paramiko for SSH communication
# logs activity and errors

import paramiko
from PyQt5.QtCore import QThread
import time


class SSHScripter(QThread):
    def __init__(self, signals, logger, stop_event,
                 rpi_ip, rpi_user, rpi_pass,
                 router_ip, router_user, router_pass,
                 router_script="router_script.sh",
                 rpi_ping_cmd="ping 192.168.50.1 -i 0.1 -w 60"):
        super().__init__()
        self.signals = signals
        self.logger = logger
        self.stop_event = stop_event

        self.rpi_ip = rpi_ip
        self.rpi_user = rpi_user
        self.rpi_pass = rpi_pass
        self.router_ip = router_ip
        self.router_user = router_user
        self.router_pass = router_pass

        self.router_script = router_script
        self.rpi_ping_cmd = rpi_ping_cmd

    def run(self):
        if self.logger:
            self.logger.success(__file__, "<run>: SSH thread started")

        try:
            # 1. Start stream on router
            if self.logger:
                self.logger.success(__file__, "<run>: connecting to router")

            router_ssh = paramiko.SSHClient()
            router_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            router_ssh.connect(self.router_ip, username=self.router_user, password=self.router_pass)

            cmd_router = f"sh /jffs/{self.router_script}"
            router_ssh.exec_command(cmd_router)

            if self.logger:
                self.logger.success(__file__, f"<run>: router command launched ({cmd_router})")

            router_ssh.close()

            # 2. Start ping script on RPi
            if self.logger:
                self.logger.success(__file__, "<run>: connecting to RPi")

            rpi_ssh = paramiko.SSHClient()
            rpi_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            rpi_ssh.connect(self.rpi_ip, username=self.rpi_user, password=self.rpi_pass)

            _, stdout, stderr = rpi_ssh.exec_command(self.rpi_ping_cmd)

            for line in stdout:
                if self.stop_event.is_set():
                    break
                if self.logger:
                    self.logger.success(__file__, f"<run>: [RPi ping] {line.strip()}")

            rpi_ssh.close()

        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<run>: SSH error - {str(e)}")

        if self.logger:
            self.logger.success(__file__, "<run>: SSH thread finished")
