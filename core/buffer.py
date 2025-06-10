# core/buffer.py
# thread-safe circular buffer designed to store parsed CSI data packets 
# synchronization between threads is ensured by using a QMutex lock 
# instantiate buffer once in main for csi_receiver thread usage
# instantiate mutex once in main
    
from collections import deque
from PyQt5.QtCore import QMutex, QMutexLocker
import time

class CircularBuffer:

    def __init__(self, maxsize: int):
        self._buffer = deque(maxlen=maxsize)
        self._timestamps = deque(maxlen=maxsize)

    def put(self, data, mutex: QMutex):
        with QMutexLocker(mutex):
            self._buffer.append(data)
            self._timestamps.append(time.time())

    def get_batch(self, count: int, mutex: QMutex):
        with QMutexLocker(mutex):
            if len(self._buffer) >= count:
                data_batch = [self._buffer.popleft() for _ in range(count)]
                time_batch = [self._timestamps.popleft() for _ in range(count)]
                return data_batch, time_batch
            return [], []

    def size(self, mutex: QMutex) -> int:
        with QMutexLocker(mutex):
            return len(self._buffer)

    def is_full(self, mutex: QMutex) -> bool:
        with QMutexLocker(mutex):
            return len(self._buffer) >= self._buffer.maxlen
