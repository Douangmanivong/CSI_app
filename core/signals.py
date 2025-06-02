from time import perf_counter
from PyQt5.QtCore import QObject, pyqtSignal

class PerformanceMonitor(QObject):
    update_stats = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.latencies = []
        self.last_time = perf_counter()
        
    def start_measurement(self):
        self.last_time = perf_counter()
        
    def end_measurement(self, label=""):
        delta = (perf_counter() - self.last_time) * 1000  # in ms
        self.latencies.append(delta)
        stats = {
            'last': delta,
            'avg': sum(self.latencies)/len(self.latencies),
            'max': max(self.latencies),
            'label': label
        }
        self.update_stats.emit(stats)
        return delta