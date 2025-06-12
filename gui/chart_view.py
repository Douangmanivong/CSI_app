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
        self.x_width = max(x_width, 1.0)
        self.y_values = set()

        self.chart = QChart()
        self.line_series = QLineSeries()
        self.axis_x = QValueAxis()
        self.axis_y = QValueAxis()

        self._setup_chart(title, x_name, y_name)

        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)

        layout = QVBoxLayout(self)
        layout.addWidget(self.chart_view)
        layout.setContentsMargins(0, 0, 0, 0)

        if self.logger:
            self.logger.success(__file__, "<__init__>: chart initialized")

    def _setup_chart(self, title, x_name, y_name):
        self.chart.addSeries(self.line_series)
        self.chart.legend().hide()
        self.chart.setTitle(title)

        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignLeft)

        self.line_series.attachAxis(self.axis_x)
        self.line_series.attachAxis(self.axis_y)

        self.axis_x.setTitleText(x_name)
        self.axis_y.setTitleText(y_name)

        self.axis_x.setRange(0, 1)
        self.axis_y.setRange(200, 2000)

        if self.logger:
            self.logger.success(__file__, "<_setup_chart>: chart setup complete")

    @pyqtSlot(dict)
    def update_chart(self, fft_data):
        try:
            if 'x' in fft_data and 'y' in fft_data:
                x, y = fft_data['x'], fft_data['y']
            elif 'time' in fft_data and 'magnitude' in fft_data:
                x, y = fft_data['time'], fft_data['magnitude']
            else:
                if self.logger:
                    self.logger.failure(__file__, f"<update_chart>: Invalid data format - keys={list(fft_data.keys())}")
                return

            self._append_data_point(x, y)

            if self.logger:
                self.logger.success(__file__, f"<update_chart>: point added")

        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<update_chart>: Exception occurred - {str(e)}")

    def _append_data_point(self, x, y):
        if x < self.axis_x.min():
            self.clear()

        self.line_series.append(x, y)

        x_lower = x - self.x_width
        points = self.line_series.points()
        points_to_remove = 0

        for i, point in enumerate(points):
            if point.x() < x_lower:
                self.y_values.discard(point.y())
                points_to_remove += 1
            else:
                x_lower = point.x()
                break

        if points_to_remove > 0:
            self.line_series.removePoints(0, points_to_remove)

        self.axis_x.setRange(x_lower, x)
        self._update_y_range(y)

        if self.logger:
            self.logger.success(__file__, f"<_append_data_point>: data added")

    def _update_y_range(self, new_y):
        self.y_values.add(new_y)

        if len(self.y_values) > 0:
            y_min = min(self.y_values)
            y_max = max(self.y_values)

            if y_max != y_min:
                y_buffer = (y_max - y_min) * 0.02
            else:
                y_buffer = abs(y_max) * 0.1 if y_max != 0 else 1.0

            self.axis_y.setRange(y_min - y_buffer, y_max + y_buffer)

            if self.logger:
                self.logger.success(__file__, f"<_update_y_range>: updated")

    def clear(self):
        self.line_series.clear()
        self.y_values.clear()
        self.axis_x.setRange(0, 1)
        self.axis_y.setRange(200, 2000)

        if self.logger:
            self.logger.success(__file__, "<clear>: chart cleared")

    def set_x_width(self, width):
        self.x_width = max(width, 1.0)
        if self.logger:
            self.logger.success(__file__, f"<set_x_width>: new width = {self.x_width}")

    def get_point_count(self):
        count = len(self.line_series.points())
        if self.logger:
            self.logger.success(__file__, f"<get_point_count>: count = {count}")
        return count

    def set_title(self, title):
        self.chart.setTitle(title)
        if self.logger:
            self.logger.success(__file__, f"<set_title>: title set to {title}")