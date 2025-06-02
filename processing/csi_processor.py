from config.settings import THRESHOLD_VALUE

class ThresholdDetector:
    def __init__(self, threshold=None):
        self.threshold = threshold or THRESHOLD_VALUE
        
    def check_threshold(self, csi_data):
        avg_amplitude = sum(csi_data.amplitudes) / len(csi_data.amplitudes)
        return avg_amplitude > self.threshold
        
    def set_threshold(self, value):
        self.threshold = value