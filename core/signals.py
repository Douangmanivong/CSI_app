# core/signals.py
# create signals
# instantiate in main and connect signals to slots

from PyQt5.QtCore import QObject, pyqtSignal
import numpy as np

class AppSignals(QObject):
    # === Data Signals ===
    csi_data = pyqtSignal(bytes, float)             # From receiver to parser
    fft_data = pyqtSignal(np.ndarray, float)        # From processor to chart_view

    # === Alert & Status Signals ===
    threshold_exceeded = pyqtSignal(float, float)   # From processor to main_window

    # === Configuration Signals ===
    threshold_value = pyqtSignal(float)             # From main_window to processor

    # === Logging Signals ===
    logs = pyqtSignal(str)                           # From logger to main_window

    # === Control Signals ===

    start_app = pyqtSignal()                        # From UI to main
    stop_app = pyqtSignal()                         # From UI to main