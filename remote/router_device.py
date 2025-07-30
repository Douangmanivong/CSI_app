# remote/router_device.py
# router device implementation for CSI collection control

from remote.remote_device import RemoteDevice
import config.settings as Settings

class RouterDevice(RemoteDevice):
    def __init__(self, stop_event, logger):
        super().__init__(
            ip=Settings.ROUTER_IP,
            username=Settings.ROUTER_ID,
            stop_event=stop_event,
            password=Settings.ROUTER_PASSWORD,
            logger=logger
        )
        self.nexutil_running = False
    
    def connect_sniffer(self):
        try:
            result = super().connect_sniffer()
            if result and self.logger:
                self.logger.success(__file__, f"<connect_sniffer>: connected to Router at {Settings.ROUTER_IP}")
            return result
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<connect_sniffer>: {str(e)}")
            return False
    
    def setup_sniffer(self):
        if not self.connected:
            if self.logger:
                self.logger.failure(__file__, "<setup_sniffer>: not connected to Router")
            return False
        
        try:
            stdout, stderr = self.ssh.exec("cd /jffs && source ./setup_env")
            
            if "ERROR:" in stdout or stderr:
                if self.logger:
                    self.logger.failure(__file__, f"<setup_sniffer>: {stdout}{stderr}")
                return False
            
            self.setup_done = True
            if self.logger:
                self.logger.success(__file__, "<setup_sniffer>: environment setup completed")
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<setup_sniffer>: {str(e)}")
            return False
    
    def start_stream(self):
        if not self.connected:
            if self.logger:
                self.logger.failure(__file__, "<start_stream>: not connected to Router")
            return False
        
        if not self.setup_done:
            if self.logger:
                self.logger.failure(__file__, "<start_stream>: setup not completed")
            return False
        
        try:
            nexutil_cmd = 'nexutil -Ieth6 -s500 -b -l34 -v "\\x0a\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00"'
            stdout, stderr = self.ssh.exec(nexutil_cmd)
            
            if stderr and "error" in stderr.lower():
                if self.logger:
                    self.logger.failure(__file__, f"<start_stream>: nexutil failed - {stderr}")
                return False
            
            stdout, stderr = self.ssh.exec("cd /jffs && source ./setup_env && source ./start_stream")
            
            if "SUCCESS:" not in stdout:
                if self.logger:
                    self.logger.failure(__file__, f"<start_stream>: {stdout}{stderr}")
                return False
            
            self.stream_active = True
            self.nexutil_running = True
            if self.logger:
                self.logger.success(__file__, "<start_stream>: CSI streaming started successfully")
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<start_stream>: {str(e)}")
            return False
    
    def stop_stream(self):
        if not self.connected:
            if self.logger:
                self.logger.failure(__file__, "<stop_stream>: not connected to Router")
            return False
        
        try:
            stdout, stderr = self.ssh.exec("cd /jffs && source ./setup_env && source ./stop_stream")
            
            self.ssh.exec("pkill -f nexutil")
            
            self.stream_active = False
            self.nexutil_running = False
            if self.logger:
                self.logger.success(__file__, "<stop_stream>: CSI streaming stopped successfully")
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<stop_stream>: {str(e)}")
            return False
    
    def save_data(self, laptop_ip=None, port=5000):
        if not self.connected:
            if self.logger:
                self.logger.failure(__file__, "<save_data>: not connected to Router")
            return False
        
        try:
            if laptop_ip:
                cmd = f"cd /jffs && source ./setup_env && source ./save_data {laptop_ip} {port}"
            else:
                cmd = "cd /jffs && source ./setup_env && source ./save_data"
            
            stdout, stderr = self.ssh.exec(cmd)
            
            if "SUCCESS:" in stdout or "INFO:" in stdout:
                if self.logger:
                    self.logger.success(__file__, f"<save_data>: {stdout.strip()}")
                return True
            else:
                if self.logger:
                    self.logger.failure(__file__, f"<save_data>: {stdout}{stderr}")
                return False
            
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<save_data>: {str(e)}")
            return False
    
    def disconnect_sniffer(self):
        if not self.connected:
            if self.logger:
                self.logger.failure(__file__, "<disconnect_sniffer>: already disconnected")
            return True
        
        try:
            if self.stream_active:
                self.stop_stream()

            stdout, stderr = self.ssh.exec("rmmod dhd && modprobe dhd")
            
            if stderr and "error" in stderr.lower():
                if self.logger:
                    self.logger.failure(__file__, f"<disconnect_sniffer>: driver reload warning - {stderr}")
                    self.logger.info(__file__, "<disconnect_sniffer>: attempting router reboot...")
                self.ssh.exec("reboot")
            
            result = super().disconnect_sniffer()
            self.setup_done = False
            self.nexutil_running = False
            
            if self.logger:
                self.logger.success(__file__, "<disconnect_sniffer>: router disconnected and firmware restored")
            return result
            
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<disconnect_sniffer>: {str(e)}")
            return False
    
    def run(self):
        self.exec_()