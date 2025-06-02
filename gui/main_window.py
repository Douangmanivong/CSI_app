from PyQt5.QtWidgets import QMainWindow
from PyQt5 import uic
from gui.views.chart import CSIChartView
from gui.views.alerts import AlertHandler

class MainWindow(QMainWindow):
    def __init__(self, pipeline, logger):
        super().__init__()
        self.pipeline = pipeline
        self.logger = logger
        
        # Chargement de l'interface UI
        uic.loadUi("gui/ui/main_window.ui", self)
        self.logger.log("UI loaded successfully")
        
        # Initialisation des composants
        self._init_ui()
        self._connect_signals()
        
    def _init_ui(self):
        """Initialise les composants UI"""
        self.chart_view = CSIChartView()
        self.plot_layout.addWidget(self.chart_view)
        self.alert_handler = AlertHandler(self.alertLineEdit)
        self.logger.log("UI components initialized")

    def _connect_signals(self):
        """Connecte les signaux et slots"""
        # Pipeline signals
        self.pipeline.new_data.connect(self._update_chart)
        self.pipeline.motion_detected.connect(self._handle_motion)
        
        # Contrôles UI
        self.startButton.clicked.connect(self._start_processing)
        self.stopButton.clicked.connect(self._stop_processing)
        self.thresholdSlider.valueChanged.connect(self._update_threshold)
        
        self.logger.log("Signal connections established")

    def _update_chart(self, csi_data):
        """Met à jour le graphique avec les nouvelles données"""
        try:
            self.chart_view.update_data(csi_data)
            self.thresholdValueLabel.setText(str(self.thresholdSlider.value()))
        except Exception as e:
            self.logger.log(f"Chart update failed: {str(e)}", level='error')

    def _handle_motion(self, detected):
        """Gère les détections de mouvement"""
        if detected:
            self.alert_handler.trigger_alert("Motion detected!")
            self.logger.log("Motion detected", level='warning')

    def _start_processing(self):
        """Démarre le traitement des données"""
        self.pipeline.start()
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)
        self.logger.log("Processing started")

    def _stop_processing(self):
        """Arrête le traitement des données"""
        self.pipeline.stop()
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.logger.log("Processing stopped")

    def _update_threshold(self, value):
        """Met à jour le seuil de détection"""
        self.pipeline.threshold_detector.set_threshold(value)
        self.logger.log(f"Threshold updated to {value}")