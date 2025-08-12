# gui/chart_view.py
# chartView displays CSI spectrogram data received from processor via fft_data signal
# rewritten using pyqtgraph for high-performance rendering
# connects to fft_data signal and plots dynamically decimated data for performance

from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import pyqtSlot
import pyqtgraph as pg


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
        self.t0 = None

        self.data_buffer = []
        self.plot_widget = pg.PlotWidget(title=title)
        self.plot_widget.setBackground('w')
        self.plot_widget.setLabel('bottom', x_name)
        self.plot_widget.setLabel('left', y_name)
        self.plot_widget.setYRange(200, 2000)
        self.plot_widget.enableAutoRange(x=False, y=False)
        self.curve = self.plot_widget.plot([], [], pen=pg.mkPen(color=(0, 0, 100), width=1))  # Dark blue

        layout = QVBoxLayout(self)
        layout.addWidget(self.plot_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.MAX_BUFFER_SIZE = 2000

        # if self.logger:
        #     self.logger.success(__file__, "<__init__>: chart initialized")

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

            if self.t0 is None:
                self.t0 = x

            relative_x = max(0, x - self.t0)

            self.data_buffer.append((relative_x, y))
            self.y_values.add(y)

            if len(self.data_buffer) > self.MAX_BUFFER_SIZE:
                self.data_buffer = self.data_buffer[-self.MAX_BUFFER_SIZE:]

            x_latest = self.data_buffer[-1][0]
            visible_window = [pt for pt in self.data_buffer if x_latest - self.x_width <= pt[0] <= x_latest]

            plot_step = max(1, len(visible_window) // 500)
            filtered = visible_window[::plot_step]

            if filtered:
                x_vals, y_vals = zip(*filtered)
                self.curve.setData(x_vals, y_vals)
                self.plot_widget.setXRange(max(0, x_latest - self.x_width), x_latest)

                if self.y_values:
                    y_min = min(self.y_values)
                    y_max = max(self.y_values)
                    y_buffer = (y_max - y_min) * 0.02 if y_max != y_min else abs(y_max) * 0.1
                    self.plot_widget.setYRange(y_min - y_buffer, y_max + y_buffer)

        except Exception as e:
            if self.logger:
                self.logger.failure(__file__, f"<update_chart>: Exception occurred - {str(e)}")

    def clear(self):
        self.data_buffer.clear()
        self.y_values.clear()
        self.curve.clear()
        self.plot_widget.setXRange(0, 1)
        self.plot_widget.setYRange(200, 2000)
        self.t0 = None

    def set_x_width(self, width):
        self.x_width = max(width, 1.0)
        # if self.logger:
        #     self.logger.success(__file__, f"<set_x_width>: new width = {self.x_width}")

    def get_point_count(self):
        count = len(self.data_buffer)
        # if self.logger:
        #     self.logger.success(__file__, f"<get_point_count>: count = {count}")
        return count

    def set_title(self, title):
        self.plot_widget.setTitle(title)
        # if self.logger:
        #     self.logger.success(__file__, f"<set_title>: title set to {title}")