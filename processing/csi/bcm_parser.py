from dataclasses import dataclass
from processing.csi.parser import BaseParser

@dataclass
class CSIData:
    timestamp: float
    amplitudes: list
    phases: list
    mac: str

class BCMParser(BaseParser):
    def parse(self, raw_data):
        # Implémentez votre logique de parsing spécifique BCM ici
        # Adapté de votre code existant
        return CSIData(...)