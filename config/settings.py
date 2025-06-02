import os
from dataclasses import dataclass

@dataclass
class AppSettings:
    THRESHOLD: float = 50.0
    BUFFER_SIZE: int = 1000
    SAMPLE_RATE: int = 100

# Load settings
settings = AppSettings()