from PyQt5.QtChart import QChart, QChartView, QLineSeries
from PyQt5.QtCore import Qt

class CSIChartView(QChartView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.chart = QChart()
        self.setChart(self.chart)
        self.setRenderHint(QPainter.Antialiasing)
        
        # Setup chart
        self.series = QLineSeries()
        self.chart.addSeries(self.series)
        self.chart.createDefaultAxes()
        
    def update_data(self, csi_data):
        self.series.clear()
        for i, amp in enumerate(csi_data.amplitudes):
            self.series.append(i, amp)
        self.chart.axes(Qt.Horizontal)[0].setRange(0, len(csi_data.amplitudes))