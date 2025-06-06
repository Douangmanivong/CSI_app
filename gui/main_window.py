"""
gui/main_window.py - Fenêtre principale avec ChartView intégré
"""

from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSlider, QLabel, QPushButton, QTextEdit, QCheckBox, QLineEdit, QGroupBox, QGridLayout, QSplitter
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.uic import loadUi
import os

from gui.views.chart_view import ChartView
from config.settings import Settings

class MainWindow(QMainWindow):
    """
    Fenêtre principale de l'application CSI Monitor
    Intègre le ChartView pour affichage spectrogramme
    """
    
    def __init__(self, signals):
        super().__init__()
        self.signals = signals
        
        # ChartView (remplace la zone spectrogramme dans l'UI)
        self.chart_view = ChartView(self)
        
        # Références aux widgets UI
        self.threshold_slider = None
        self.threshold_value_label = None
        self.default_threshold_checkbox = None
        self.alert_line_edit = None
        self.start_button = None
        self.stop_button = None
        self.log_text = None
        
        # État de l'application
        self.is_running = False
        
        # Setup UI
        self.setup_ui()
        self.connect_signals()
        
        # Timer pour mise à jour périodique UI
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self.periodic_ui_update)
        self.ui_timer.start(Settings.UI_UPDATE_INTERVAL_MS)

        # Création du ChartView
        self.chart_view = ChartView(
        title="CSI Spectrogram",
        x_label="Time (s)", 
        y_label="Magnitude",
        x_width=Settings.CHART_X_WIDTH
        )
    
        # Ajout au layout du plotGroupBox (défini dans votre .ui)
        self.plot_layout.addWidget(self.chart_view)
    
        # IMPORTANT: Connexion du signal fft_data au slot update_chart
        self.signals.fft_data.connect(self.chart_view.update_chart)
    
    def setup_ui(self):
        """Configuration de l'interface utilisateur"""
        # Option 1: Charger depuis .ui file et remplacer la zone plot
        self.load_ui_and_integrate_chart()
        
        # Option 2: Créer programmatiquement (si pas de .ui)
        # self.create_ui_programmatically()
    
    def load_ui_and_integrate_chart(self):
        """
        Charge l'UI depuis le fichier .ui et intègre le ChartView
        """
        # Chargement du fichier UI
        ui_file = os.path.join(os.path.dirname(__file__), "ui", "main_window.ui")
        
        try:
            # Charge l'UI dans un widget temporaire
            temp_widget = QWidget()
            loadUi(ui_file, temp_widget)
            
            # Récupère les références aux widgets
            self.threshold_slider = temp_widget.thresholdSlider
            self.threshold_value_label = temp_widget.thresholdValueLabel
            self.default_threshold_checkbox = temp_widget.defaultThresholdCheckBox
            self.alert_line_edit = temp_widget.alertLineEdit
            self.start_button = temp_widget.startButton
            self.stop_button = temp_widget.stopButton
            self.log_text = temp_widget.logText
            
            # Trouve le layout de la zone plot et y intègre le ChartView
            plot_group_box = temp_widget.plotGroupBox
            plot_layout = plot_group_box.findChild(QVBoxLayout, "plot_layout")
            
            if plot_layout:
                # Ajoute le ChartView à la place de la zone vide
                plot_layout.addWidget(self.chart_view)
            else:
                # Fallback: crée le layout s'il n'existe pas
                plot_layout = QVBoxLayout(plot_group_box)
                plot_layout.addWidget(self.chart_view)
            
            # Définit le widget central
            self.setCentralWidget(temp_widget)
            
            # Configuration initiale des widgets
            self.setup_widget_properties()
            
        except Exception as e:
            print(f"Erreur chargement UI: {e}")
            # Fallback vers création programmatique
            self.create_ui_programmatically()
    
    def create_ui_programmatically(self):
        """
        Crée l'UI programmatiquement si le fichier .ui n'est pas disponible
        """
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        
        # Splitter vertical
        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter)
        
        # === Zone supérieure (graphique + contrôles) ===
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        
        # Groupe spectrogramme
        plot_group = QGroupBox("CSI Spectrogram")
        plot_layout = QVBoxLayout(plot_group)
        plot_layout.addWidget(self.chart_view)
        top_layout.addWidget(plot_group)
        
        # Layout contrôles
        controls_layout = QHBoxLayout()
        
        # Groupe détection
        detection_group = QGroupBox("Detection")
        detection_layout = QGridLayout(detection_group)
        
        # Slider seuil
        detection_layout.addWidget(QLabel("Threshold (0-100):"), 0, 0)
        
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(0, 100)
        self.threshold_slider.setValue(50)
        self.threshold_slider.setTickPosition(QSlider.TicksBelow)
        self.threshold_slider.setTickInterval(10)
        detection_layout.addWidget(self.threshold_slider, 0, 1)
        
        self.threshold_value_label = QLabel("50")
        self.threshold_value_label.setMinimumWidth(30)
        detection_layout.addWidget(self.threshold_value_label, 0, 2)
        
        self.default_threshold_checkbox = QCheckBox("Use Default")
        detection_layout.addWidget(self.default_threshold_checkbox, 0, 3)
        
        # Zone alerte
        self.alert_line_edit = QLineEdit()
        self.alert_line_edit.setReadOnly(True)
        self.alert_line_edit.setPlaceholderText("No motion detected")
        self.alert_line_edit.setStyleSheet("font-weight: bold; color: #d9534f;")
        detection_layout.addWidget(self.alert_line_edit, 1, 0, 1, 4)
        
        controls_layout.addWidget(detection_group)
        
        # Boutons Start/Stop
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start")
        self.start_button.setMinimumSize(80, 0)
        self.start_button.setStyleSheet("background-color: #5cb85c; color: white;")
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.setMinimumSize(80, 0)
        self.stop_button.setStyleSheet("background-color: #d9534f; color: white;")
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        controls_layout.addLayout(button_layout)
        top_layout.addLayout(controls_layout)
        
        splitter.addWidget(top_widget)
        
        # === Zone inférieure (logs) ===
        log_group = QGroupBox("Event Log")
        log_group.setMaximumHeight(150)
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        log_layout.addWidget(self.log_text)
        
        splitter.addWidget(log_group)
        
        # Configuration finale
        self.setWindowTitle("CSI Motion Detection")
        self.resize(1000, 700)
        
        self.setup_widget_properties()
    
    def setup_widget_properties(self):
        """Configuration des propriétés des widgets"""
        # Configuration slider
        if self.threshold_slider:
            self.threshold_slider.valueChanged.connect(self.on_threshold_changed)
        
        # Configuration checkbox
        if self.default_threshold_checkbox:
            self.default_threshold_checkbox.toggled.connect(self.on_default_threshold_toggled)
        
        # Configuration boutons
        if self.start_button:
            self.start_button.clicked.connect(self.on_start_clicked)
        
        if self.stop_button:
            self.stop_button.clicked.connect(self.on_stop_clicked)
    
    def connect_signals(self):
        """Connexion des signaux entre composants"""
        # Données FFT vers ChartView
        self.signals.fft_data.connect(self.chart_view.append_data)
        
        # Alertes seuil
        self.signals.threshold_exceeded.connect(self.on_threshold_alert)
        
        # Status connexion
        self.signals.connection_status.connect(self.update_connection_status)
        
        # Logs
        self.signals.logs.connect(self.update_log)
    
    # === SLOTS ===
    
    @pyqtSlot(int)
    def on_threshold_changed(self, value):
        """Slot pour changement de valeur du slider"""
        if self.threshold_value_label:
            self.threshold_value_label.setText(str(value))
        
        # Émet le signal vers le processor
        threshold_float = float(value)
        self.signals.threshold_value.emit(threshold_float)
    
    @pyqtSlot(bool)
    def on_default_threshold_toggled(self, checked):
        """Slot pour checkbox seuil par défaut"""
        if checked:
            default_value = int(Settings.DEFAULT_THRESHOLD)
            if self.threshold_slider:
                self.threshold_slider.setValue(default_value)
    
    @pyqtSlot()
    def on_start_clicked(self):
        """Démarrage de l'acquisition"""
        self.is_running = True
        
        if self.start_button:
            self.start_button.setEnabled(False)
        if self.stop_button:
            self.stop_button.setEnabled(True)
        
        # Démarre le ChartView
        self.chart_view.start_refresh_timer()
        
        # Log
        self.signals.logs.emit("INFO", "Application started")
    
    @pyqtSlot()
    def on_stop_clicked(self):
        """Arrêt de l'acquisition"""
        self.is_running = False
        
        if self.start_button:
            self.start_button.setEnabled(True)
        if self.stop_button:
            self.stop_button.setEnabled(False)
        
        # Arrête le ChartView
        self.chart_view.stop_refresh_timer()
        
        # Efface le graphique
        self.chart_view.clear()
        
        # Reset alerte
        if self.alert_line_edit:
            self.alert_line_edit.setText("")
            self.alert_line_edit.setPlaceholderText("No motion detected")
        
        # Log
        self.signals.logs.emit("INFO", "Application stopped")
    
    @pyqtSlot(float, float)
    def on_threshold_alert(self, amplitude, timestamp):
        """Affichage alerte dépassement seuil"""
        if self.alert_line_edit:
            alert_text = f"MOTION DETECTED! Amplitude: {amplitude:.2f} at {timestamp:.2f}s"
            self.alert_line_edit.setText(alert_text)
            
            # Animation couleur (optionnel)
            self.alert_line_edit.setStyleSheet(
                "font-weight: bold; color: #ffffff; background-color: #d9534f;"
            )
            
            # Timer pour reset couleur après 2 secondes
            QTimer.singleShot(2000, self.reset_alert_style)
    
    @pyqtSlot(str, bool)
    def update_connection_status(self, message, is_connected):
        """Mise à jour status connexion dans logs"""
        status = "CONNECTED" if is_connected else "DISCONNECTED"
        self.signals.logs.emit("STATUS", f"{status}: {message}")
    
    @pyqtSlot(str, str)
    def update_log(self, level, message):
        """Ajout d'un log dans la console"""
        if self.log_text:
            # Format avec couleur selon le niveau
            color_map = {
                "ERROR": "#d9534f",
                "WARNING": "#f0ad4e", 
                "SUCCESS": "#5cb85c",
                "INFO": "#5bc0de",
                "DEBUG": "#777777",
                "ALERT": "#d9534f"
            }
            
            color = color_map.get(level, "#000000")
            formatted_log = f'<span style="color: {color};">[{level}] {message}</span>'
            
            self.log_text.append(formatted_log)
            
            # Auto-scroll vers le bas
            self.log_text.verticalScrollBar().setValue(
                self.log_text.verticalScrollBar().maximum()
            )
    
    def reset_alert_style(self):
        """Reset du style de l'alerte"""
        if self.alert_line_edit:
            self.alert_line_edit.setStyleSheet("font-weight: bold; color: #d9534f;")
    
    def periodic_ui_update(self):
        """Mise à jour périodique de l'UI"""
        # Peut être utilisé pour des animations ou mises à jour spécifiques
        pass
    
    def closeEvent(self, event):
        """Gestion fermeture application"""
        # Arrêt propre des timers
        self.ui_timer.stop()
        self.chart_view.stop_refresh_timer()
        
        # Émet signal d'arrêt vers les threads
        self.signals.logs.emit("INFO", "Application closing...")
        
        event.accept()