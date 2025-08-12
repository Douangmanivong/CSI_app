# remote/rpi_device.py
# RPi device implementation for CSI collection control

from remote.remote_device import RemoteDevice
from remote.ssh_manager import SSHManager
from PyQt5.QtCore import QTimer
import config.settings as Settings
from datetime import datetime
import os
import time

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
        self.save_enabled = False
        self.setup_done = False
        self.current_save_dir = None
        self.current_experiment_name = None
    
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
            
            if self._start_csi_forwarder():
                self.stream_active = True
                if self.logger:
                    self.logger.success(__file__, "<start_stream>: CSI streaming started successfully")
                return True
            else:
                if self.logger:
                    self.logger.failure(__file__, "<start_stream>: failed to start csi_forwarder.py")
                return False
            
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<start_stream>: {str(e)}")
            return False
        
    def start_save(self):
        if not self.forward_running:
            if self.logger:
                self.logger.failure(__file__, "<start_save>: stream not running")
            return False
    
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            experiment_name = f"experiment_{timestamp}"
            self.current_save_dir = "csi_captures"
            self.current_experiment_name = experiment_name
        
            save_control_cmd = f"echo 'ENABLE_SAVE:{self.current_save_dir}:{experiment_name}' > /tmp/csi_control"
            stdout, stderr = self.forward_ssh.exec(save_control_cmd)
            
            time.sleep(0.2)
        
            self.save_enabled = True
        
            if self.logger:
                self.logger.success(__file__, f"<start_save>: Saving enabled - {experiment_name}")
            return True
        
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<start_save>: {str(e)}")
            return False

    def stop_save(self):
        if not self.save_enabled:
            return True
        
        try:
            save_control_cmd = "echo 'DISABLE_SAVE' > /tmp/csi_control"
            stdout, stderr = self.forward_ssh.exec(save_control_cmd)
            
            time.sleep(0.2)
        
            self.save_enabled = False
        
            if self.logger:
                self.logger.success(__file__, "<stop_save>: Saving disabled")
            return True
        
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<stop_save>: {str(e)}")
            return False

    def save_data(self):
        if self.save_enabled:
            success = self.stop_save()
            if success:
                return self.transfer_data()
            return False
        else:
            return self.start_save()
    
    def stop_stream(self):
        if not self.connected:
            if self.logger:
                self.logger.failure(__file__, "<stop_stream>: not connected to RPi")
            return False
        
        try:
            if self.save_enabled:
                self.stop_save()
            
            self._stop_csi_forwarder()
            
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
    
    def transfer_data(self):
        if not self.current_experiment_name:
            if self.logger:
                self.logger.failure(__file__, "<transfer_data>: no experiment name set")
            return False

        try:
            os.makedirs("./stream/", exist_ok=True)
            
            remote_path = f"{self.current_save_dir}/{self.current_experiment_name}_*.bin"
            local_path = "./stream/"

            scp_cmd = (
                f"sshpass -p '{Settings.RPi_PASSWORD}' "
                f"scp {Settings.RPi_ID}@{Settings.RPi_IP}:{remote_path} {local_path}"
            )

            result = os.system(scp_cmd)
            if result != 0:
                if self.logger:
                    self.logger.failure(__file__, f"<transfer_data>: SCP failed with code {result}")
                return False

            if self.logger:
                self.logger.success(__file__, f"<transfer_data>: file transferred to {local_path}")
            return True

        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<transfer_data>: {str(e)}")
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
    
    def _start_csi_forwarder(self):
        try:
            if self.logger:
                self.logger.success(__file__, "<_start_csi_forwarder>: starting csi_forwarder_tee.py")
            
            forwarder_cmd = f"python3 csi_forwarder_tee.py {Settings.Laptop_IP_FROM_RPi} {Settings.PORT}"
            
            stdin, stdout, stderr = self.forward_ssh.client.exec_command(forwarder_cmd)
            
            self.forward_running = True
            self.forward_process_started = True
            
            self.forward_timer.start(2000)
            
            return True
                
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<_start_csi_forwarder>: {str(e)}")
            return False
    
    def _check_forward_status(self):
        if not self.forward_running or self.stop_event.is_set():
            self.forward_timer.stop()
            return
        
        try:
            stdout, stderr = self.forward_ssh.exec("pgrep -f csi_forwarder_tee.py")
            
            if not stdout.strip():
                if self.logger:
                    self.logger.failure(__file__, "<_check_forward_status>: csi_forwarder_tee.py process not found")
                self.forward_running = False
                self.forward_timer.stop()
            else:
                if self.logger:
                    self.logger.success(__file__, "<_check_forward_status>: csi_forwarder_tee.py running normally")
                    
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<_check_forward_status>: {str(e)}")
    
    def _stop_csi_forwarder(self):
        try:
            self.forward_timer.stop()
            self.forward_running = False
            
            if self.forward_ssh and self.forward_process_started:
                stdout, stderr = self.forward_ssh.exec("pkill -f csi_forwarder_tee.py")
                
                if self.logger:
                    self.logger.success(__file__, "<_stop_csi_forwarder>: csi_forwarder_tee.py stopped")
            
            if self.forward_ssh:
                self.forward_ssh.close()
                self.forward_ssh = None
            
            self.forward_process_started = False
            
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<_stop_csi_forwarder>: {str(e)}")
    
    def run(self):
        self.exec_()