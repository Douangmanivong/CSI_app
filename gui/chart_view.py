# gui/chart_view.py
# chartView displays CSI spectrogram data received from processor via fft_data signal
# adapted from C++ version to Python with PyQt5 and QtCharts
# instantiate in main_window and connect fft_data signal to update_chart slot
# uses logger for debugging and maintains sliding window of data points
# automatically adjusts X and Y axis ranges based on incoming data

from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QPainter
import numpy as np


class ChartView(QWidget):
    def __init__(self, parent=None, logger=None, 
                 title="CSI Spectrogram", 
                 x_name="Time (s)", 
                 y_name="Magnitude", 
                 x_width=20.0):
        super().__init__(parent)
        
        self.logger = logger if logger else None
        self.x_width = max(x_width, 1.0)  # Minimum width of 1.0
        self.y_values = set()  # For tracking Y range
        
        # Create chart components
        self.chart = QChart()
        self.line_series = QLineSeries()
        self.axis_x = QValueAxis()
        self.axis_y = QValueAxis()
        
        # Configure chart
        self._setup_chart(title, x_name, y_name)
        
        # Create chart view
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        
        # Set layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.chart_view)
        layout.setContentsMargins(0, 0, 0, 0)
        
        if self.logger:
            self.logger.success(__file__)

    def _setup_chart(self, title, x_name, y_name):
        # Add series to chart
        self.chart.addSeries(self.line_series)
        self.chart.legend().hide()
        self.chart.setTitle(title)
        
        # Configure axes
        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignLeft)
        
        # Attach axes to series
        self.line_series.attachAxis(self.axis_x)
        self.line_series.attachAxis(self.axis_y)
        
        # Set axis labels
        self.axis_x.setTitleText(x_name)
        self.axis_y.setTitleText(y_name)
        
        # Set initial ranges
        self.axis_x.setRange(0, 1)
        self.axis_y.setRange(200, 2000)  # Default CSI amplitude range

    @pyqtSlot(dict)
    def update_chart(self, fft_data):
        # Update chart with new FFT data from processor
        # Expected fft_data format: {'x': float, 'y': float} or {'time': float, 'amplitude': float}
        try:
            # Extract x, y values from different possible formats
            if 'x' in fft_data and 'y' in fft_data:
                x, y = fft_data['x'], fft_data['y']
            elif 'time' in fft_data and 'amplitude' in fft_data:
                x, y = fft_data['time'], fft_data['amplitude']
            else:
                if self.logger:
                    self.logger.failure(__file__)
                return
            
            self._append_data_point(x, y)
            
        except Exception as e:
            if self.logger:
                self.logger.failure(__file__)

    def _append_data_point(self, x, y):
        # Add new data point and manage sliding window
        # If time value doesn't make sense (went backwards), clear graph
        if x < self.axis_x.min():
            self.clear()
        
        # Add new point
        self.line_series.append(x, y)
        
        # Calculate sliding window boundaries
        x_lower = x - self.x_width
        points = self.line_series.points()
        
        # Remove old points outside the window
        points_to_remove = 0
        for i, point in enumerate(points):
            if point.x() < x_lower:
                self.y_values.discard(point.y())  # Remove from Y tracking
                points_to_remove += 1
            else:
                x_lower = point.x()  # Update actual lower bound
                break
        
        # Remove old points if any
        if points_to_remove > 0:
            self.line_series.removePoints(0, points_to_remove)
        
        # Update X axis range
        self.axis_x.setRange(x_lower, x)
        
        # Update Y axis range based on visible data
        self._update_y_range(y)

    def _update_y_range(self, new_y):
        # Update Y axis range based on visible data points
        self.y_values.add(new_y)
        
        if len(self.y_values) > 0:
            y_min = min(self.y_values)
            y_max = max(self.y_values)
            
            # Add 2% buffer so points aren't on the edge
            if y_max != y_min:
                y_buffer = (y_max - y_min) * 0.02
            else:
                y_buffer = abs(y_max) * 0.1 if y_max != 0 else 1.0
            
            self.axis_y.setRange(y_min - y_buffer, y_max + y_buffer)

    def clear(self):
        # Clear all data and reset chart
        self.line_series.clear()
        self.y_values.clear()
        self.axis_x.setRange(0, 1)
        self.axis_y.setRange(200, 2000)
        
        if self.logger:
            self.logger.success(__file__)

    def set_x_width(self, width):
        # Set the sliding window width
        self.x_width = max(width, 1.0)
        
    def get_point_count(self):
        # Get current number of points displayed
        return len(self.line_series.points())

    def set_title(self, title):
        # Update chart title
        self.chart.setTitle(title)