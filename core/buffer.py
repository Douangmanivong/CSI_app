import numpy as np
from collections import deque

class CircularBuffer:
    def __init__(self, size=1000):
        self.buffer = deque(maxlen=size)
        self.size = size
        
    def add(self, data):
        """Ajoute des données CSI au buffer"""
        self.buffer.append(data)
        
    def get_last(self, n=1):
        """Récupère les n derniers échantillons"""
        return list(self.buffer)[-n:]
        
    def clear(self):
        self.buffer.clear()
        
    def is_full(self):
        return len(self.buffer) >= self.size

class CSIBuffer(CircularBuffer):
    def get_amplitudes_matrix(self, n_samples=100):
        """Retourne une matrice numpy des amplitudes pour traitement"""
        samples = self.get_last(n_samples)
        return np.array([s.amplitudes for s in samples])