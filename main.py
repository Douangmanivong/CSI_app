# main.py
# instantiate buffer, mutex, logger, threads for processing et receiving
# dont forget to add mutex, stop_event and buffer to constructors
# connect signals and slots
# show main_window and run app
# thread management is centralized here with simple start/stop functions

import sys
import threading
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QMutex
from core.signals import Signals
from core.buffer import CircularBuffer
from gui.main_window import MainWindow
from csi_io.csi_receiver import CSIReceiver
from processing.rpi4_parser import RPI4Parser
from processing.bcm4366c0_parser import BCM4366C0Parser
from csi_io.logger import Logger
import config.settings as Settings
if Settings.SOURCE_DEVICE == "RPi4":
    from processing.csi_magnitude_processor_rpi4 import CSIMagnitudeProcessor
else:
    from processing.csi_magnitude_processor_asus import CSIMagnitudeProcessor
from remote.rpi_device import RPiDevice
from remote.router_device import RouterDevice
from remote.laptop_ping import LaptopPing


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

    # Sniffing device
    if Settings.SOURCE_DEVICE == "RPi4":
        sniffer_device = RPiDevice(stop_event, logger)
    else:
        sniffer_device = RouterDevice(stop_event, logger)

    # Threads
    threads = {
        "receiver": CSIReceiver(signals, logger, stop_event),
        "parser": RPI4Parser(signals, logger, buffer, mutex, stop_event),
        "processor": CSIMagnitudeProcessor(signals, buffer, mutex, logger, stop_event, ma_window=Settings.MA_WINDOW),
        "sniffer": sniffer_device,
        "laptop_ping": LaptopPing(logger, stop_event)
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
    signals.toggle_ping.connect(threads["laptop_ping"].toggle_ping)
    signals.connect_sniffer.connect(threads["sniffer"].connect_sniffer)
    signals.setup_sniffer.connect(threads["sniffer"].setup_sniffer)
    signals.start_stream.connect(threads["sniffer"].start_stream)
    signals.stop_stream.connect(threads["sniffer"].stop_stream)
    signals.disconnect_sniffer.connect(threads["sniffer"].disconnect_sniffer)
    signals.save_data.connect(threads["sniffer"].save_data)

def start_threads():
    stop_event.clear()
    for key, thread in threads.items():
        if not thread.isRunning():
            if key == "receiver":
                thread.first_packet_logged = False
            thread.start()

def stop_threads():
    stop_event.set()
    for key, thread in threads.items():
        if thread.isRunning():
            if not thread.wait(3000):
                thread.terminate()

if __name__ == "__main__":
    sys.exit(main())
