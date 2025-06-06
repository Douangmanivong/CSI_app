# processing/csi_processor.py
# CSI data processor thread
# retrieves CSI packets from circular buffer in batches
# applies threshold detection on magnitudes per subcarrier
# emits fft_data signal for chart visualization
# emits threshold_exceeded signal when thresholds are breached

import numpy as np
import time
from PyQt5.QtCore import QThread
from config.settings import THRESHOLD_VALUE

class CSIProcessor(QThread):
    """CSI data processor for threshold detection and visualization"""
    
    def __init__(self, signals, logger, buffer, mutex, batch_size=10):
        super().__init__()
        self.signals = signals
        self.logger = logger
        self.buffer = buffer
        self.mutex = mutex
        self.batch_size = batch_size
        
        # Processing parameters
        self.threshold_value = THRESHOLD_VALUE
        self.running = False
        
        # Connect to threshold updates from UI
        self.signals.threshold_value.connect(self.update_threshold)
        
        self.logger.success(__file__)  # Processor initialized
    
    def run(self):
        """Main processing loop - runs in separate thread"""
        self.running = True
        self.logger.success(__file__)  # Processing thread started
        
        while self.running:
            try:
                # Retrieve batch from circular buffer
                if not self._retrieve_batch():
                    self.msleep(10)  # Wait if no data available
                    continue
                
            except Exception as e:
                self.logger.failure(__file__)
                print(f"Processing error: {e}")
                self.msleep(100)  # Wait before retry
    
    def _retrieve_batch(self) -> bool:
        """Retrieve and process a batch of CSI data from buffer"""
        try:
            # Access shared buffer with mutex protection
            buffer_size = self.buffer.size(self.mutex)
            if buffer_size < self.batch_size:
                return False  # Not enough data
            
            # Get batch of CSI packets
            data_batch, time_batch = self.buffer.get_batch(self.batch_size, self.mutex)
            
            if not data_batch:
                return False
            
            self.logger.success(__file__)  # Batch retrieved successfully
            
            # Process the batch
            self._process_batch(data_batch, time_batch)
            return True
            
        except Exception as e:
            self.logger.failure(__file__)
            print(f"Buffer access error: {e}")
            return False
    
    def _process_batch(self, data_batch, time_batch):
        """Process a batch of CSI packets"""
        try:
            # Extract magnitude data for processing
            all_magnitudes = []
            latest_timestamp = 0
            
            for csi_packet, timestamp in zip(data_batch, time_batch):
                if isinstance(csi_packet, dict) and 'magnitudes' in csi_packet:
                    all_magnitudes.append(csi_packet['magnitudes'])
                    latest_timestamp = max(latest_timestamp, timestamp)
            
            if not all_magnitudes:
                self.logger.failure(__file__)
                return
            
            # Convert to numpy array for processing
            magnitude_matrix = np.array(all_magnitudes)  # Shape: (batch_size, 64)
            
            self.logger.success(__file__)  # Data extraction successful
            
            # Apply threshold detection
            self._detect_thresholds(magnitude_matrix, latest_timestamp)
            
            # Prepare FFT data for visualization
            self._emit_fft_data(magnitude_matrix, latest_timestamp)
            
        except Exception as e:
            self.logger.failure(__file__)
            print(f"Batch processing error: {e}")
    
    def _detect_thresholds(self, magnitude_matrix, timestamp):
        """Detect threshold exceedances across subcarriers"""
        try:
            # Calculate mean magnitudes across batch for each subcarrier
            mean_magnitudes = np.mean(magnitude_matrix, axis=0)  # Shape: (64,)
            
            # Find subcarriers exceeding threshold
            exceeded_mask = mean_magnitudes > self.threshold_value
            exceeded_indices = np.where(exceeded_mask)[0]
            
            if len(exceeded_indices) > 0:
                # Calculate maximum exceeded value
                max_exceeded_value = np.max(mean_magnitudes[exceeded_mask])
                
                # Emit threshold exceeded signal
                self.signals.threshold_exceeded.emit(
                    float(max_exceeded_value), 
                    float(timestamp)
                )
                
                self.logger.success(__file__)  # Threshold detection completed
                print(f"Threshold exceeded: {max_exceeded_value:.2f} > {self.threshold_value} "
                      f"on {len(exceeded_indices)} subcarriers")
            
        except Exception as e:
            self.logger.failure(__file__)
            print(f"Threshold detection error: {e}")
    
    def _emit_fft_data(self, magnitude_matrix, timestamp):
        """Emit FFT data for chart visualization"""
        try:
            # Calculate mean spectrum across batch
            mean_spectrum = np.mean(magnitude_matrix, axis=0)  # Shape: (64,)
            
            # Emit spectrum data for visualization
            self.signals.fft_data.emit(mean_spectrum, float(timestamp))
            
            self.logger.success(__file__)  # FFT data emission successful
            
        except Exception as e:
            self.logger.failure(__file__)
            print(f"FFT data emission error: {e}")
    
    def update_threshold(self, new_threshold):
        """Update threshold value from UI slider"""
        try:
            self.threshold_value = float(new_threshold)
            self.logger.success(__file__)  # Threshold updated
            print(f"Threshold updated to: {self.threshold_value}")
            
        except Exception as e:
            self.logger.failure(__file__)
            print(f"Threshold update error: {e}")
    
    def stop(self):
        """Stop the processor thread"""
        try:
            self.running = False
            self.quit()
            self.wait()
            self.logger.success(__file__)  # Processor stopped
            
        except Exception as e:
            self.logger.failure(__file__)
            print(f"Stop error: {e}")
    
    def get_current_threshold(self) -> float:
        """Get current threshold value"""
        return self.threshold_value
    
    def set_batch_size(self, new_batch_size: int):
        """Update batch processing size"""
        try:
            if new_batch_size > 0:
                self.batch_size = new_batch_size
                self.logger.success(__file__)  # Batch size updated
            else:
                self.logger.failure(__file__)
                
        except Exception as e:
            self.logger.failure(__file__)
            print(f"Batch size update error: {e}")
    
    def get_processing_stats(self) -> dict:
        """Get processing statistics"""
        try:
            buffer_size = self.buffer.size(self.mutex)
            
            stats = {
                'buffer_size': buffer_size,
                'batch_size': self.batch_size,
                'threshold_value': self.threshold_value,
                'is_running': self.running
            }
            
            self.logger.success(__file__)  # Stats retrieved
            return stats
            
        except Exception as e:
            self.logger.failure(__file__)
            print(f"Stats retrieval error: {e}")
            return {}