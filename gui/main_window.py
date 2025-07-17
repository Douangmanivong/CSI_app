# gui/main_window.py
# MainWindow loads UI, handles user interactions and displays data/alerts
# connects threshold slider to processor via threshold_value signal
# receives threshold_exceeded signal from processor to show motion alerts
# displays logs from logger in console and updates chart with CSI data
# manages start/stop button states and emits start_app/stop_app signals

from PyQt5.QtWidgets import QMainWindow, QMessageBox
from PyQt5.QtCore import pyqtSlot, QTimer
from PyQt5.uic import loadUi
import os

from core.signals import Signals
from gui.chart_view import ChartView
import config.settings as Settings


class MainWindow(QMainWindow):
    def __init__(self, signals: Signals, logger):
        super().__init__()

        self.signals = signals
        self.logger = logger
        self.chart_view = None
        self.is_running = False

        # Load UI file
        self._load_ui()

        # Setup chart view
        self._setup_chart()

        # Connect UI signals
        self._connect_ui_signals()

        # Setup alert timer (for clearing alerts)
        self.alert_timer = QTimer()
        self.alert_timer.timeout.connect(self._clear_alert)
        self.alert_timer.setSingleShot(True)

        # if self.logger:
        #     self.logger.success(__file__, "<__init__>")

    def _load_ui(self):
        try:
            ui_path = os.path.join(os.path.dirname(__file__), 'main_window.ui')
            loadUi(ui_path, self)

            self.stopButton.setEnabled(False)
            self.thresholdValueLabel.setText(str(self.thresholdSlider.value()))

            # if self.logger:
            #     self.logger.success(__file__, "<_load_ui>: ui loaded")

        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, "<_load_ui>: failed to load ui")
            self.setWindowTitle("CSI Motion Detection")
            self.resize(1000, 700)

    def _setup_chart(self):
        try:
            self.chart_view = ChartView(
                parent=self.plotGroupBox,
                logger=self.logger,
                title="CSI Spectrogram",
                x_name="Time (s)",
                y_name="Magnitude",
                x_width=20.0
            )

            if hasattr(self, 'plot_layout'):
                self.plot_layout.addWidget(self.chart_view)

            # if self.logger:
            #     self.logger.success(__file__, "<_setup_chart>: chart created")

        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, "<_setup_chart>: failed to create chart")

    def _connect_ui_signals(self):
        try:
            self.thresholdSlider.valueChanged.connect(self._on_threshold_changed)
            self.defaultThresholdCheckBox.toggled.connect(self._on_no_threshold_toggled)
            self.startButton.clicked.connect(self._on_start_clicked)
            self.stopButton.clicked.connect(self._on_stop_clicked)
            self.rpiConnectButton.clicked.connect(self.signals.connect_ping_device.emit)
            self.rpiStartPingButton.clicked.connect(self.signals.start_ping.emit)
            self.rpiStopPingButton.clicked.connect(self.signals.stop_ping.emit)
            self.routerConnectButton.clicked.connect(self.signals.connect_router.emit)
            self.routerStartStreamButton.clicked.connect(self.signals.start_stream.emit)
            self.routerStopStreamButton.clicked.connect(self.signals.stop_stream.emit)
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, "<_connect_ui_signals>: failed to connect")
    def _on_threshold_changed(self, value):
        self.thresholdValueLabel.setText(str(value))

        if self.defaultThresholdCheckBox.isChecked():
            self.signals.threshold_value.emit(value)

        # if self.logger:
        #     self.logger.success(__file__, "<_on_threshold_changed>: slider event")

    def _on_no_threshold_toggled(self, checked):
        self.thresholdSlider.setEnabled(checked)

        if checked:
            value = self.thresholdSlider.value()
            self.signals.threshold_value.emit(value)
        else:
            self.signals.threshold_value.emit(Settings.THRESHOLD_DISABLED)

        # if self.logger:
        #     self.logger.success(__file__, "<_on_no_threshold_toggled>: checkbox clicked")

    def _on_start_clicked(self):
        if not self.is_running:
            self.signals.start_app.emit()
            self._set_running_state(True)

            # if self.logger:
            #     self.logger.success(__file__, "<_on_start_clicked>: start app")

    def _on_stop_clicked(self):
        if self.is_running:
            self.signals.stop_app.emit()
            self._set_running_state(False)

            # if self.logger:
            #     self.logger.success(__file__, "<_on_stop_clicked>: stop app")

    def _set_running_state(self, running):
        self.is_running = running
        self.startButton.setEnabled(not running)
        self.stopButton.setEnabled(running)

        if not running:
            self._clear_alert()


    @pyqtSlot(str)
    def show_threshold_alert(self, message):
        try:
            self.alertLineEdit.setText(f"MOTION DETECTED: {message}")
            self.alertLineEdit.setStyleSheet("font-weight: bold; color: #d9534f; background-color: #f2dede;")
            self.alert_timer.start(3000)

            # if self.logger:
            #     self.logger.success(__file__, "<show_threshold_alert>: alert")

        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, "<show_threshold_alert> failed to alert")

    def _clear_alert(self):
        self.alertLineEdit.setText("No motion detected")
        self.alertLineEdit.setStyleSheet("font-weight: bold; color: #5cb85c;")

    @pyqtSlot(str)
    def update_console(self, log_message):
        try:
            self.logText.append(log_message)
            cursor = self.logText.textCursor()
            cursor.movePosition(cursor.End)
            self.logText.setTextCursor(cursor)

            if self.logText.document().blockCount() > 1000:
                cursor.movePosition(cursor.Start)
                cursor.movePosition(cursor.Down, cursor.KeepAnchor, 100)
                cursor.removeSelectedText()

        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, "<update_console>: failed to update")

    def update_chart(self, fft_data):
        if self.chart_view:
            self.chart_view.update_chart(fft_data)

    def closeEvent(self, event):
        if self.is_running:
            reply = QMessageBox.question(
                self, 
                'Confirm Exit',
                'Application is still running. Stop and exit ?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.signals.stop_app.emit()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

        # if self.logger:
        #     self.logger.success(__file__, "<closeEvent>: app closed")

    def get_current_threshold(self):
        if not self.defaultThresholdCheckBox.isChecked():
            # if self.logger:
            #     self.logger.success(__file__, "<get_current_threshold>: enabled checked")
            return Settings.THRESHOLD_DISABLED

        # if self.logger:
        #     self.logger.success(__file__, "<get_current_threshold>: current value updated")
        return self.thresholdSlider.value()

    def set_threshold(self, value):
        if value == Settings.THRESHOLD_DISABLED:
            self.defaultThresholdCheckBox.setChecked(False)
        else:
            self.defaultThresholdCheckBox.setChecked(True)
            self.thresholdSlider.setValue(value)

        # if self.logger:
        #     self.logger.success(__file__, "<set_threshold>: value changed")
