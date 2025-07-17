# remote/ssh_manager.py
# SSH connection handler using Paramiko
# encapsulates SSH setup, command execution and closing
# supports both password and key-based authentication

import paramiko

class SSHManager:
    def __init__(self, ip, username, password=None, keyfile=None, logger=None):
        self.ip = ip
        self.username = username
        self.password = password
        self.keyfile = keyfile
        self.logger = logger
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def connect(self):
        try:
            if self.keyfile:
                self.client.connect(self.ip, username=self.username, key_filename=self.keyfile)
            else:
                self.client.connect(self.ip, username=self.username, password=self.password)
            return True
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<connect>: {e}")
            return False

    def exec(self, cmd):
        try:
            stdin, stdout, stderr = self.client.exec_command(cmd)
            return stdout.read().decode(), stderr.read().decode()
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<exec>: {e}")
            return "", str(e)

    def close(self):
        try:
            self.client.close()
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<close>: {e}")