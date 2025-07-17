# remote/router_device.py
# asus router controller using SSH
# starts and stops CSI packet streaming to laptop via TCP

import os
import subprocess
from datetime import datetime
from remote.remote_device import RemoteDevice
from PyQt5.QtCore import pyqtSlot
from config.settings import Router_IP, Router_ID, Router_PASSWORD, USE_WSL, PORT

class RouterDevice(RemoteDevice):
    def __init__(self, signals, stop_event, logger=None):
        super().__init__(Router_IP, Router_ID, stop_event, password=Router_PASSWORD, logger=logger)
        self.signals = signals
        self.stream_proc = None

    @pyqtSlot()
    def request_connect(self):
        if self.logger:
            self.logger.success(__file__, "trying to connect to Router...")
        try:
            self.connect()
            if self.logger:
                self.logger.success(__file__, "<connect>: connected to Router")
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<connect to router> failed: {e}")

    @pyqtSlot()
    def request_start_stream(self):
        if not self.connected:
            if self.logger:
                self.logger.failure(__file__, "<start stream>: device not connected")
            return
        try:
            self.stream_folder = new_stream_folder("csi_stream")
            if self.logger:
                self.logger.success(__file__, f"<start stream>: created session folder {self.stream_folder}")

            cmd_meta = (
                "source /jffs/setup_env && "
                "echo '__PARAM__'; "
                "echo \"AP_0_X=$AP_0_X\"; echo \"AP_0_Y=$AP_0_Y\"; echo \"AP_0_THETA=$AP_0_THETA\"; "
                "echo \"TX_IP=$TX_IP\"; echo \"TX_ROUTER_IP=$TX_ROUTER_IP\"; echo \"PKT_TIME=$PKT_TIME\"; echo \"DURATION=$DURATION\"; "
                "echo '__SURVEY__'; "
                "echo \"EXP_NAME=$EXP_NAME\"; echo \"CH_NO=$CH_NO\"; echo \"BW=$BW\"; echo \"IF=$IF\"; echo \"MAC_ADDR=$MAC_ADDR\"; "
                "echo '__TIME__'; date -Iseconds"
            )
            stdout, stderr = self.ssh.exec(cmd_meta)
            if stderr:
                self.logger.failure(__file__, f"<read setup_env stderr>: {stderr.strip()}")

            sections = {"__PARAM__": [], "__SURVEY__": [], "__TIME__": []}
            current = None
            for line in stdout.strip().splitlines():
                if line.strip() in sections:
                    current = line.strip()
                elif current:
                    sections[current].append(line.strip())

            with open(os.path.join(self.stream_folder, "param.txt"), "w") as f:
                f.write("\n".join(sections["__PARAM__"]))
            with open(os.path.join(self.stream_folder, "survey.txt"), "w") as f:
                f.write("\n".join(sections["__SURVEY__"]))
            with open(os.path.join(self.stream_folder, "time.txt"), "w") as f:
                f.write("\n".join(sections["__TIME__"]))

            if self.logger:
                self.logger.success(__file__, f"<start stream>: saved metadata to {self.stream_folder}")

            if USE_WSL:
                script_path = "/mnt/c/Users/douangmanivong/Desktop/stage/appliQT/remote/stream_router.sh"
                self.stream_proc = subprocess.Popen(["wsl", script_path])
                self.logger.success(__file__, f"<start stream>: stream launched via WSL script: {script_path}")
            else:
                ssh_cmd = [
                    "ssh",
                    f"{Router_ID}@{Router_IP}",
                    "source /jffs/setup_env && /jffs/tcpdump -i \"$IF\" -U -s 0 -w - icmp"
                ]
                nc_cmd = ["nc", "127.0.0.1", str(PORT)]
                self.stream_proc = subprocess.Popen(
                    ssh_cmd,
                    stdout=subprocess.PIPE
                )
                self.nc_proc = subprocess.Popen(
                    nc_cmd,
                    stdin=self.stream_proc.stdout,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                self.logger.success(__file__, "<start stream>: stream piped via local SSH/NC (Linux/macOS)")
        except Exception as e:
            self.logger.failure(__file__, f"<start stream>: {e}")

    @pyqtSlot()
    def request_stop_stream(self):
        try:
            if self.stream_proc:
                self.stream_proc.terminate()
                self.logger.success(__file__, "<stop stream>: stream process terminated")
        except Exception as e:
            self.logger.failure(__file__, f"<stop stream>: {e}")

def new_stream_folder(base_dir="csi_stream"):
    timestamp = datetime.now().strftime("stream_%Y-%m-%d_%H-%M-%S")
    folder_path = os.path.join(base_dir, timestamp)
    os.makedirs(folder_path, exist_ok=True)
    return folder_path
