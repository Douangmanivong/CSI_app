"""
gui/views/chart_view.py - Graphique temps réel pour spectrogramme CSI
Adaptation du code C++ ChartView vers Python/PyQt5
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import pyqtSlot, QTimer
import pyqtgraph as pg
import numpy as np
from collections import deque
import time
from config.settings import Settings

class ChartView(QWidget):
    """
    Widget de graphique temps réel pour affichage spectrogramme CSI
    Equivalent Python du ChartView C++
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configuration graphique (équivalent C++)
        self.x_width = Settings.CHART_X_WIDTH  # Largeur fenêtre temporelle (ex: 20 secondes)
        self.max_points = Settings.CHART_MAX_POINTS  # Limite nb points affichés
        
        # Structures de données (équivalent std::multiset C++)
        self.time_data = deque(maxlen=self.max_points)
        self.amplitude_data = deque(maxlen=self.max_points)
        self.y_values_set = []  # Pour tracking min/max efficace
        
        # Configuration PyQtGraph
        self.setup_chart()
        
        # Layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.plot_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Timer pour refresh périodique (si nécessaire)
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_display)
        
    def setup_chart(self):
        """Configuration initiale du graphique (équivalent constructeur C++)"""
        # Création widget PyQtGraph
        self.plot_widget = pg.PlotWidget()
        
        # Configuration générale
        self.plot_widget.setLabel('left', 'Amplitude', units='dB')
        self.plot_widget.setLabel('bottom', 'Time', units='s')
        self.plot_widget.setTitle('CSI Spectrogram - Real Time')
        
        # Configuration grille
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        # Configuration courbe
        self.curve = self.plot_widget.plot(
            pen=pg.mkPen(color='#00ff00', width=2),
            name='CSI Amplitude'
        )
        
        # Configuration axes (équivalent axisX/axisY C++)
        self.plot_widget.setXRange(0, self.x_width)
        self.plot_widget.setYRange(0, 100)  # Valeurs par défaut
        
        # Auto-range désactivé initialement
        self.plot_widget.enableAutoRange(axis='x', enable=False)
        self.plot_widget.enableAutoRange(axis='y', enable=False)
    
    @pyqtSlot(np.ndarray, float)
    def append_data(self, fft_data, timestamp):
        """
        Ajoute nouvelles données FFT au graphique
        Équivalent de appendData() C++
        
        Args:
            fft_data: Résultat FFT (array numpy)
            timestamp: Timestamp des données
        """
        try:
            # Calcul amplitude maximale (équivalent du QPair C++)
            max_amplitude = np.max(np.abs(fft_data))
            
            # Vérification cohérence temporelle (équivalent C++)
            if self.time_data and timestamp < self.time_data[-1]:
                self.clear()
            
            # Ajout nouvelle donnée
            self.time_data.append(timestamp)
            self.amplitude_data.append(max_amplitude)
            self.y_values_set.append(max_amplitude)
            
            # Nettoyage données anciennes (équivalent fenêtre glissante C++)
            self._remove_old_data(timestamp)
            
            # Mise à jour affichage
            self._update_display()
            
        except Exception as e:
            print(f"ChartView append_data error: {e}")
    
    def _remove_old_data(self, current_time):
        """
        Supprime les données trop anciennes (équivalent logique C++)
        Maintient seulement les x_width dernières secondes
        """
        cutoff_time = current_time - self.x_width
        
        # Compteur pour suppression (équivalent count C++)
        remove_count = 0
        
        # Trouve le premier point à conserver
        for i, t in enumerate(self.time_data):
            if t >= cutoff_time:
                break
            remove_count += 1
        
        # Suppression des anciens points
        if remove_count > 0:
            # Supprime des deques
            for _ in range(remove_count):
                if self.time_data:
                    self.time_data.popleft()
                if self.amplitude_data:
                    removed_value = self.amplitude_data.popleft()
                    # Mise à jour du set des valeurs Y
                    if removed_value in self.y_values_set:
                        self.y_values_set.remove(removed_value)
    
    def _update_display(self):
        """
        Met à jour l'affichage du graphique
        Équivalent de la logique de mise à jour des axes C++
        """
        if not self.time_data or not self.amplitude_data:
            return
        
        # Conversion en arrays pour PyQtGraph
        x_array = np.array(self.time_data)
        y_array = np.array(self.amplitude_data)
        
        # Mise à jour courbe
        self.curve.setData(x_array, y_array)
        
        # Mise à jour axe X (équivalent setRange C++)
        if len(x_array) > 1:
            x_min = x_array[0]
            x_max = x_array[-1]
            self.plot_widget.setXRange(x_min, x_max, padding=0)
        
        # Mise à jour axe Y avec buffer (équivalent logique C++)
        if self.y_values_set:
            y_min = min(self.y_values_set)
            y_max = max(self.y_values_set)
            
            # Buffer 2% comme dans le C++
            y_range = y_max - y_min
            y_buffer = y_range * 0.02 if y_range > 0 else 1.0
            
            self.plot_widget.setYRange(
                y_min - y_buffer, 
                y_max + y_buffer, 
                padding=0
            )
    
    @pyqtSlot()
    def clear(self):
        """
        Efface toutes les données (équivalent clear() C++)
        """
        self.time_data.clear()
        self.amplitude_data.clear()
        self.y_values_set.clear()
        
        # Reset graphique
        self.curve.setData([], [])
        self.plot_widget.setXRange(0, self.x_width)
        self.plot_widget.setYRange(0, 100)
    
    def refresh_display(self):
        """
        Refresh périodique si nécessaire
        """
        # Peut être utilisé pour des animations ou mises à jour spécifiques
        pass
    
    def start_refresh_timer(self, interval_ms=50):
        """Démarre le timer de refresh"""
        self.refresh_timer.start(interval_ms)
    
    def stop_refresh_timer(self):
        """Arrête le timer de refresh"""
        self.refresh_timer.stop()
    
    def set_x_width(self, width):
        """Change la largeur de la fenêtre temporelle"""
        self.x_width = width
        # Force une mise à jour si des données existent
        if self.time_data:
            current_time = self.time_data[-1]
            self._remove_old_data(current_time)
            self._update_display()