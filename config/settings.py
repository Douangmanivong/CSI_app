# config/settings.py
# macros for buffer, csi_receiver and csi_processing
# threshold value is the default value, value can be changed with ui slider
# ip, id, password, key path, file path for remote device must be added here

HOST_ID = "127.0.0.1"
PORT = 5000
BUFFER_SIZE = 1024
THRESHOLD_VALUE = 100
THRESHOLD_DISABLED = -1
MA_WINDOW = 5
SUBCARRIER = 32

# RPi macros
RPi_IP = "192.168.50.203"
RPi_ID = "douangmanivong"
RPi_PASSWORD = "TPTPTPTP"
RPi_PATH = ""

# Asus Router macros
Router_IP = "192.168.50.1"
Router_ID = "TPTPTPTP"
Router_PASSWORD = "TPTPTPTP"
Router_PATH = ""

# Laptop macros
Laptop_IP = "192.168.50.67"
USE_WSL = True
