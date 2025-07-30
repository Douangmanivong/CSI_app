# remote/rpi_device.py
# RPi device implementation for CSI collection control

from remote.remote_device import RemoteDevice
from remote.ssh_manager import SSHManager
from PyQt5.QtCore import QTimer
import config.settings as Settings
import os
from datetime import datetime

class RPiDevice(RemoteDevice):
    def __init__(self, stop_event, logger):
        super().__init__(
            ip=Settings.RPi_IP,
            username=Settings.RPi_ID,
            stop_event=stop_event,
            password=Settings.RPi_PASSWORD,
            logger=logger
        )
        self.forward_ssh = None 
        self.forward_timer = QTimer()
        self.forward_timer.timeout.connect(self._check_forward_status)
        self.forward_timer.moveToThread(self)
        self.forward_running = False
        self.forward_process_started = False
        self.setup_done = False
    
    def connect_sniffer(self):
        try:
            result = super().connect_sniffer()
            if result and self.logger:
                self.logger.success(__file__, f"<connect_sniffer>: connected to RPi at {Settings.RPi_IP}")
            return result
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<connect_sniffer>: {str(e)}")
            return False
    
    def setup_sniffer(self):
        if not self.connected:
            if self.logger:
                self.logger.failure(__file__, "<setup_sniffer>: not connected to RPi")
            return False
        
        try:
            stdout, stderr = self.ssh.exec("sudo cspi apply")
            
            if stderr and "error" in stderr.lower():
                if self.logger:
                    self.logger.failure(__file__, f"<setup_sniffer>: cspi apply failed - {stderr}")
                return False
            
            self.setup_done = True
            if self.logger:
                self.logger.success(__file__, "<setup_sniffer>: cspi apply completed successfully")
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<setup_sniffer>: {str(e)}")
            return False
    
    def start_stream(self):
        if not self.connected:
            if self.logger:
                self.logger.failure(__file__, "<start_stream>: not connected to RPi")
            return False
        
        if not self.setup_done:
            if self.logger:
                self.logger.failure(__file__, "<start_stream>: setup not completed")
            return False
        
        try:
            cspi_cmd = f"sudo cspi start -c {Settings.CHANNEL} -b {Settings.BANDWIDTH} -m {Settings.AP_MAC}"
            stdout, stderr = self.ssh.exec(cspi_cmd)
            
            if stderr and "error" in stderr.lower():
                if self.logger:
                    self.logger.failure(__file__, f"<start_stream>: cspi start failed - {stderr}")
                return False
            
            self.forward_ssh = SSHManager(
                Settings.RPi_IP, 
                Settings.RPi_ID, 
                Settings.RPi_PASSWORD, 
                logger=self.logger
            )
            
            if not self.forward_ssh.connect():
                if self.logger:
                    self.logger.failure(__file__, "<start_stream>: failed to create forward SSH connection")
                return False
            
            if self._start_forward_udp():
                self.stream_active = True
                if self.logger:
                    self.logger.success(__file__, "<start_stream>: CSI streaming started successfully")
                return True
            else:
                if self.logger:
                    self.logger.failure(__file__, "<start_stream>: failed to start forward_udp.py")
                return False
            
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<start_stream>: {str(e)}")
            return False
        
    def save_data(self):
        if not self.connected:
            if self.logger:
                self.logger.failure(__file__, "<save_data>: not connected to RPi")
            return False
        
        try:
            stream_dir = "stream"
            if not os.path.exists(stream_dir):
                os.makedirs(stream_dir)
                if self.logger:
                    self.logger.success(__file__, f"<save_data>: created directory {stream_dir}")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pcap_filename = f"csi_data_{timestamp}.pcap"
            remote_pcap = f"/tmp/{pcap_filename}"
            local_pcap = os.path.join(stream_dir, pcap_filename)
            
            if self.logger:
                self.logger.success(__file__, f"<save_data>: starting PCAP collection - {pcap_filename}")
            
            collect_cmd = f"sudo cspi collect -o {remote_pcap}"
            stdout, stderr = self.ssh.exec(collect_cmd)
            
            if stderr and "error" in stderr.lower():
                if self.logger:
                    self.logger.failure(__file__, f"<save_data>: cspi collect failed - {stderr}")
                return False
            
            check_cmd = f"ls -la {remote_pcap}"
            stdout, stderr = self.ssh.exec(check_cmd)
            
            if not stdout or "No such file" in stderr:
                if self.logger:
                    self.logger.failure(__file__, f"<save_data>: PCAP file not created on RPi")
                return False
            
            scp_cmd = f"scp {Settings.RPi_ID}@{Settings.RPi_IP}:{remote_pcap} {local_pcap}"
            
            import subprocess
            try:
                result = subprocess.run(
                    scp_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    if self.logger:
                        self.logger.success(__file__, f"<save_data>: PCAP saved successfully - {local_pcap}")
                    
                    cleanup_cmd = f"rm {remote_pcap}"
                    self.ssh.exec(cleanup_cmd)
                    
                    return True
                else:
                    if self.logger:
                        self.logger.failure(__file__, f"<save_data>: SCP transfer failed - {result.stderr}")
                    return False
                    
            except subprocess.TimeoutExpired:
                if self.logger:
                    self.logger.failure(__file__, "<save_data>: SCP transfer timeout")
                return False
            except Exception as scp_error:
                if self.logger:
                    self.logger.failure(__file__, f"<save_data>: SCP error - {str(scp_error)}")
                return False
            
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<save_data>: {str(e)}")
            return False
    
    def stop_stream(self):
        if not self.connected:
            if self.logger:
                self.logger.failure(__file__, "<stop_stream>: not connected to RPi")
            return False
        
        try:
            self._stop_forward_udp()
            
            stdout, stderr = self.ssh.exec("sudo cspi stop")
            
            if stderr and "error" in stderr.lower():
                if self.logger:
                    self.logger.failure(__file__, f"<stop_stream>: cspi stop failed - {stderr}")
                return False
            
            self.stream_active = False
            if self.logger:
                self.logger.success(__file__, "<stop_stream>: CSI streaming stopped successfully")
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<stop_stream>: {str(e)}")
            return False
    
    def disconnect_sniffer(self):
        if not self.connected:
            if self.logger:
                self.logger.failure(__file__, "<disconnect_sniffer>: already disconnected")
            return True
        
        try:
            if self.stream_active:
                self.stop_stream()
            
            stdout, stderr = self.ssh.exec("sudo cspi restore")
            
            if stderr and "error" in stderr.lower():
                if self.logger:
                    self.logger.failure(__file__, f"<disconnect_sniffer>: cspi restore warning - {stderr}")
            
            result = super().disconnect_sniffer()
            self.setup_done = False
            
            if self.logger:
                self.logger.success(__file__, "<disconnect_sniffer>: RPi disconnected and restored")
            return result
            
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<disconnect_sniffer>: {str(e)}")
            return False
    
    def _start_forward_udp(self):
        try:
            if self.logger:
                self.logger.success(__file__, "<_start_forward_udp>: starting forward_udp.py")
            
            stdin, stdout, stderr = self.forward_ssh.client.exec_command("python forward_udp.py")
            
            self.forward_running = True
            self.forward_process_started = True
            
            self.forward_timer.start(2000)
            
            return True
                
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<_start_forward_udp>: {str(e)}")
            return False
    
    def _check_forward_status(self):
        if not self.forward_running or self.stop_event.is_set():
            self.forward_timer.stop()
            return
        
        try:
            stdout, stderr = self.forward_ssh.exec("pgrep -f forward_udp.py")
            
            if not stdout.strip():
                if self.logger:
                    self.logger.failure(__file__, "<_check_forward_status>: forward_udp.py process not found")
                self.forward_running = False
                self.forward_timer.stop()
            else:
                if self.logger:
                    self.logger.success(__file__, "<_check_forward_status>: forward_udp.py running normally")
                    
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<_check_forward_status>: {str(e)}")
    
    def _stop_forward_udp(self):
        try:
            self.forward_timer.stop()
            self.forward_running = False
            
            if self.forward_ssh and self.forward_process_started:
                stdout, stderr = self.forward_ssh.exec("pkill -f forward_udp.py")
                
                if self.logger:
                    self.logger.success(__file__, "<_stop_forward_udp>: forward_udp.py stopped")
            
            if self.forward_ssh:
                self.forward_ssh.close()
                self.forward_ssh = None
            
            self.forward_process_started = False
            
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<_stop_forward_udp>: {str(e)}")
    
    def run(self):
        self.exec_()