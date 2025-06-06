# main.py
# instantiate buffer, mutex, logger, threads for processing et receiving
# dont forget to add mutex and buffer to constructors
# connect signals and slots
# show main_window and run app

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QMutex

from core.signals import AppSignals
from core.buffer import CircularBuffer
from gui.main_window import MainWindow
from processing.csi_processor import CSIProcessor
from io.csi_receiver import CSIReceiver
from io.logger import AppLogger
from processing.parsers.bcm_parser import BCM4366C0Parser
import config.settings as Settings


def main():
    app = QApplication(sys.argv)
    
    # Shared resources
    signals = AppSignals()
    buffer = CircularBuffer(Settings.BUFFER_MAX_SIZE)
    buffer_mutex = QMutex()
    logger = AppLogger(signals)
    
    # Parser CSI with logs
    parser = BCM4366C0Parser(logger=logger)

    # UI (main thread)
    main_window = MainWindow(signals, logger)
    
    # Receiver and processor (other threads)
    csi_processor = CSIProcessor(signals, buffer, buffer_mutex, logger)
    csi_receiver = CSIReceiver(signals, buffer, buffer_mutex, logger)
    
    # Connection signal/slot
    connect_signals(signals, main_window, csi_processor, csi_receiver, parser)
    
    # Show UI
    main_window.show()
    
    return app.exec_()


def connect_signals(signals, main_window, csi_processor, csi_receiver, parser):
    # UI -> Processor (slider threshold)
    signals.threshold_value.connect(csi_processor.update_threshold)

    # Processor -> UI (alertes & données)
    signals.threshold_exceeded.connect(main_window.show_threshold_alert)
    signals.fft_data.connect(main_window.chart_view.update_chart)

    # Logger -> UI (logs)
    signals.logs.connect(main_window.update_console)

    # (Optionnel) Receiver -> Parser
    signals.raw_data_received.connect(parser.on_new_data)  # À émettre depuis CSIReceiver

    # UI Start/Stop control
    signals.start_app.connect(lambda: start_threads(csi_receiver, csi_processor))
    signals.stop_app.connect(lambda: stop_threads(csi_receiver, csi_processor))


def start_threads(receiver, processor):
    if not receiver.isRunning():
        receiver.start()
    if not processor.isRunning():
        processor.start()


def stop_threads(receiver, processor):
    if receiver.isRunning():
        receiver.stop()
    if processor.isRunning():
        processor.stop()


if __name__ == "__main__":
    sys.exit(main())
