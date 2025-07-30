# core/signals.py
# create signals
# instantiate in main and connect signals to slots

from PyQt5.QtCore import QObject, pyqtSignal


class Signals(QObject):
    # Data Signals
    csi_data = pyqtSignal(bytes, float)             # From receiver to parser
    fft_data = pyqtSignal(dict)                     # From processor to chart_view

    # Alert & Status Signals 
    threshold_exceeded = pyqtSignal(str)            # From processor to main_window

    # Configuration Signals 
    threshold_value = pyqtSignal(float)             # From main_window to processor

    # Logging Signals
    logs = pyqtSignal(str)                          # From logger to main_window

    # Control Signals
    start_app = pyqtSignal()                        # From UI to main
    stop_app = pyqtSignal()                         # From UI to main

    # Remote SSH Signals
    toggle_ping = pyqtSignal()                      # From UI to laptop
    connect_sniffer = pyqtSignal()                  # From UI to remote
    setup_sniffer = pyqtSignal()                    # From UI to remote
    start_stream = pyqtSignal()                     # From UI to remote
    stop_stream = pyqtSignal()                      # From UI to remote
    disconnect_sniffer = pyqtSignal()               # From UI to remote
    save_data = pyqtSignal()                        # From UI to remote