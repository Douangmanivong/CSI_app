# main.py
# instantiate buffer, mutex, logger, threads for processing et receiving
# dont forget to add mutex, stop_event and buffer to constructors
# connect signals and slots
# show main_window and run app
# thread management is centralized here with simple start/stop functions

import os
import sys
# Force the correct Qt plugin path for PyQt5 to find qwindows.dll
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(
    os.environ.get("CONDA_PREFIX", ""),
    "Library",
    "plugins",
    "platforms"
)

import threading
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QMutex

from core.signals import Signals
from core.buffer import CircularBuffer
from gui.main_window import MainWindow
from processing.csi_magnitude_processor import CSIMagnitudeProcessor
from csi_io.csi_receiver import CSIReceiver
from csi_io.logger import Logger
from processing.csi_parser import CSIParser
import config.settings as Settings

# Global thread management variables
stop_event = threading.Event()
threads_running = False
csi_receiver = None
csi_processor = None
csi_parser = None
logger = None


def main():
    global csi_receiver, csi_processor, csi_parser, logger

    app = QApplication(sys.argv)

    # Shared resources
    signals = Signals()
    buffer = CircularBuffer(Settings.BUFFER_SIZE)
    buffer_mutex = QMutex()
    logger = Logger()

    # UI (main thread)
    main_window = MainWindow(signals, logger)
    logger.logs.connect(main_window.update_console)

    # Parser thread
    csi_parser = CSIParser(signals, logger, buffer, buffer_mutex, stop_event)

    # Processor and receiver threads
    csi_processor = CSIMagnitudeProcessor(signals, buffer, buffer_mutex, logger, stop_event)
    csi_receiver = CSIReceiver(signals, logger, stop_event)

    # Connect signals and slots
    connect_signals(signals, main_window, csi_processor)

    # Show UI
    main_window.show()

    if logger:
        logger.success(__file__, "<main>")

    return app.exec_()


def connect_signals(signals, main_window, csi_processor):
    signals.threshold_value.connect(csi_processor.update_threshold)
    signals.threshold_exceeded.connect(main_window.show_threshold_alert)
    signals.fft_data.connect(main_window.chart_view.update_chart)
    signals.logs.connect(main_window.update_console)
    signals.start_app.connect(start_threads)
    signals.stop_app.connect(stop_threads)

    if logger:
        logger.success(__file__, "<connect_signals>")


def start_threads():
    global threads_running, stop_event, csi_receiver, csi_processor, csi_parser, logger

    if threads_running:
        if logger:
            logger.success(__file__, "<start_threads>: already running")
        return
    try:
        stop_event.clear()

        if not csi_receiver.isRunning():
            csi_receiver.start()
            if logger:
                logger.success(__file__, "<start_threads>: csi_receiver started")

        if not csi_processor.isRunning():
            csi_processor.start()
            if logger:
                logger.success(__file__, "<start_threads>: csi_processor started")

        if not csi_parser.isRunning():
            csi_parser.start()
            if logger:
                logger.success(__file__, "<start_threads>: csi_parser started")

        threads_running = True
        if logger:
            logger.success(__file__, "<start_threads>: all threads started")

    except Exception as e:
        if logger:
            logger.failure(__file__, "<start_threads>: exception occurred")
        stop_threads()


def stop_threads():
    global threads_running, stop_event, csi_receiver, csi_processor, csi_parser, logger

    if not threads_running:
        return
    try:
        stop_event.set()
        if logger:
            logger.success(__file__, "<stop_threads>: stop_event set")

        if csi_receiver.isRunning():
            if not csi_receiver.wait(3000):
                csi_receiver.terminate()
            if logger:
                logger.success(__file__, "<stop_threads>: csi_receiver stopped")

        if csi_processor.isRunning():
            if not csi_processor.wait(3000):
                csi_processor.terminate()
            if logger:
                logger.success(__file__, "<stop_threads>: csi_processor stopped")

        if csi_parser.isRunning():
            if not csi_parser.wait(3000):
                csi_parser.terminate()
            if logger:
                logger.success(__file__, "<stop_threads>: csi_parser stopped")

        threads_running = False
        if logger:
            logger.success(__file__, "<stop_threads>: all threads stopped")

    except Exception as e:
        if logger:
            logger.failure(__file__, "<stop_threads>: exception occurred")
        threads_running = False


if __name__ == "__main__":
    sys.exit(main())