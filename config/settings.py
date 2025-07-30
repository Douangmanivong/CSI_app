# config/settings.py
# macros for buffer, csi_receiver and csi_processing
# threshold value is the default value, value can be changed with ui slider
# ip, id, password, key path, file path for remote device must be added here

HOST_ID = "127.0.0.1"
PORT = 4400
BUFFER_SIZE = 1024
THRESHOLD_VALUE = 100
THRESHOLD_DISABLED = -1
MA_WINDOW = 5
SUBCARRIER = 32
SUBCARRIER_RANGE = (28, 36)
SOURCE_DEVICE = "RPi4"  # or "ASUS"
CHANNEL = "44"
BANDWIDTH = "80"
AP_MAC = "24:4B:FE:E6:C0:64"
PING_FREQUENCY = 0.01

# RPi macros
RPi_IP = "10.42.0.207"
RPi_ID = "pi"
RPi_PASSWORD = "raspberry"

# Asus Router macros
Router_IP = "192.168.50.1"
Router_ID = "TPTPTPTP"
Router_PASSWORD = "TPTPTPTP"
SSID5GHZ = "nope"
KEY5GHZ = "nopenope"
SSID24GHZ = "TPTPTPTP"
KEY24GHZ = "TPTPTPTP"

# Laptop macros
Laptop_IP = "192.168.50.67"
Laptop_IP_FROM_RPi = "10.42.0.1"