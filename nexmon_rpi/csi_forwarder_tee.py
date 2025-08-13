#!/usr/bin/env python3
import socket
import struct
import sys
import signal
import time
import os
from datetime import datetime
from pathlib import Path
import threading

class CSIForwarderTee:
    def __init__(self, remote_ip="10.42.0.1", remote_port=4400):
        self.local_port = 4400
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        self.save_enabled = False
        self.save_dir = "csi_captures"
        self.file_prefix = "csi"
        self.running = False
        self.recv_sock = None
        self.send_sock = None
        self.save_file = None
        
        signal.signal(signal.SIGINT, self._stop)
        signal.signal(signal.SIGTERM, self._stop)
    
    def _setup_sockets(self):
        try:
            self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.recv_sock.bind(("127.0.0.1", self.local_port))
            
            self.send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            return True
        except Exception as e:
            print(f"Socket error: {e}")
            return False
    
    def _open_save_file(self):
        try:
            Path(self.save_dir).mkdir(exist_ok=True, parents=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.save_dir}/{self.file_prefix}_{timestamp}.bin"
            
            if self.save_file:
                self.save_file.close()
            
            self.save_file = open(filename, 'wb')
            print(f"Saving to: {filename}")
            return True
        except Exception as e:
            print(f"File error: {e}")
            return False
    
    def _check_control(self):
        try:
            if os.path.exists("/tmp/csi_control"):
                with open("/tmp/csi_control", 'r') as f:
                    cmd = f.read().strip()
                os.remove("/tmp/csi_control")
                
                if cmd.startswith("ENABLE_SAVE:"):
                    parts = cmd.split(":")
                    if len(parts) >= 3:
                        self.save_dir = parts[1]
                        self.file_prefix = parts[2]
                    if self._open_save_file():
                        self.save_enabled = True
                        print("Save ON")
                        
                elif cmd == "DISABLE_SAVE":
                    if self.save_file:
                        self.save_file.close()
                        self.save_file = None
                    self.save_enabled = False
                    print("Save OFF")
        except:
            pass
    
    def start(self):
        if not self._setup_sockets():
            return False
        
        print(f"Forward {self.local_port} -> {self.remote_ip}:{self.remote_port}")
        self.running = True
        
        while self.running:
            self._check_control()
            
            self.recv_sock.settimeout(0.1)
            try:
                data, addr = self.recv_sock.recvfrom(8192)
            except socket.timeout:
                continue
            
            try:
                self.send_sock.sendto(data, (self.remote_ip, self.remote_port))
            except:
                pass
            
            if self.save_enabled and self.save_file:
                try:
                    self.save_file.write(data)
                    self.save_file.flush()
                except:
                    pass
        
        self._cleanup()
        return True
    
    def _stop(self, signum=None, frame=None):
        self.running = False
    
    def _cleanup(self):
        if self.recv_sock:
            self.recv_sock.close()
        if self.send_sock:
            self.send_sock.close()
        if self.save_file:
            self.save_file.close()

def main():
    remote_ip = sys.argv[1] if len(sys.argv) > 1 else "10.42.0.1"
    remote_port = int(sys.argv[2]) if len(sys.argv) > 2 else 4400
    
    forwarder = CSIForwarderTee(remote_ip, remote_port)
    forwarder.start()

if __name__ == "__main__":
    main()
