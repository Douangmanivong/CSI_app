import logging
from logging.handlers import RotatingFileHandler
from PyQt5.QtCore import QObject, pyqtSignal

class QtSignalHandler(logging.Handler):
    def __init__(self, signal):
        super().__init__()
        self.signal = signal
        
    def emit(self, record):
        msg = self.format(record)
        self.signal.emit(msg)

class CSILogger(QObject):
    log_message = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger('CSI')
        self.logger.setLevel(logging.INFO)
        
        # Fichier de log (rotation automatique)
        file_handler = RotatingFileHandler(
            'csi_monitor.log', maxBytes=1e6, backupCount=3
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        
        # Sortie Qt
        qt_handler = QtSignalHandler(self.log_message)
        qt_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(qt_handler)
    
    def log(self, message, level='info'):
        getattr(self.logger, level)(message)