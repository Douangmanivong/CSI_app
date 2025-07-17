# main.py
# instantiate buffer, mutex, logger, threads for processing et receiving
# dont forget to add mutex, stop_event and buffer to constructors
# connect signals and slots
# show main_window and run app
# thread management is centralized here with simple start/stop functions

import os
import sys
import threading
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QMutex

# Qt plugin path for Windows
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(
    os.environ.get("CONDA_PREFIX", ""),
    "Library",
    "plugins",
    "platforms"
)

from core.signals import Signals
from core.buffer import CircularBuffer
from gui.main_window import MainWindow
from processing.csi_magnitude_processor import CSIMagnitudeProcessor
from csi_io.csi_receiver import CSIReceiver
from csi_io.logger import Logger
from processing.csi_parser import CSIParser
import config.settings as Settings
from remote.rpi_device import RPiDevice
from remote.router_device import RouterDevice

# Thread management state
stop_event = threading.Event()
threads = {}

def main():
    global threads

    app = QApplication(sys.argv)

    # Shared instances
    signals = Signals()
    logger = Logger()
    buffer = CircularBuffer(Settings.BUFFER_SIZE)
    mutex = QMutex()

    # UI
    main_window = MainWindow(signals, logger)
    logger.logs.connect(main_window.update_console)

    # Threads
    threads = {
        "receiver": CSIReceiver(signals, logger, stop_event),
        "parser": CSIParser(signals, logger, buffer, mutex, stop_event),
        "processor": CSIMagnitudeProcessor(signals, buffer, mutex, logger, stop_event, Settings.MA_WINDOW),
        "rpi": RPiDevice(signals, stop_event, logger),
        "router": RouterDevice(signals, stop_event, logger)
    }

    # Signal/slot wiring
    connect_signals(signals, main_window)

    # Show UI
    main_window.show()
    return app.exec_()

def connect_signals(signals, main_window):
    # Processing
    signals.threshold_value.connect(threads["processor"].update_threshold)
    signals.threshold_exceeded.connect(main_window.show_threshold_alert)
    signals.fft_data.connect(main_window.chart_view.update_chart)
    signals.logs.connect(main_window.update_console)

    # App control
    signals.start_app.connect(start_threads)
    signals.stop_app.connect(stop_threads)

    # Remote devices control
    signals.connect_ping_device.connect(threads["rpi"].request_connect)
    signals.start_ping.connect(threads["rpi"].request_start_ping)
    signals.stop_ping.connect(threads["rpi"].request_stop_ping)

    signals.connect_router.connect(threads["router"].request_connect)
    signals.start_stream.connect(threads["router"].request_start_stream)
    signals.stop_stream.connect(threads["router"].request_stop_stream)


def start_threads():
    stop_event.clear()
    for key in threads:
        if not threads[key].isRunning():
            threads[key].start()

def stop_threads():
    stop_event.set()
    for key in threads:
        thread = threads[key]
        if thread.isRunning():
            if not thread.wait(3000):
                thread.terminate()

if __name__ == "__main__":
    sys.exit(main())
