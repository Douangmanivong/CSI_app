# Application CSI Parser - README

## Overview
This application receives CSI packets over TCP, parses them, and processes them in real time.
It supports modular processing (e.g., magnitude for now, phase and Doppler in the future) and displays live data using a PyQt5 interface.

## Architecture

```
┌────────────────────┐                           ┌────────────────────┐
│  Raspberry Pi 4    │ ────── ICMP PING ────────►│  OpenWRT Router    │
│ (sends pings)      │                           │ (Nexmon CSI tool)  │
└────────────────────┘                           └────────────────────┘
                                                           │
                                      CSI TCP Packets (raw bytes)
                                                           ▼

┌──────────────────────────────────────────────────────────────────────────────┐
│                            io/csi_receiver.py                                │
│                           class CSIReceiver                                  │
│  - connect_tcp()                                                             │
│  - receive_loop()  ─────────────────────────────────────┐                    │
│       ↓ raw bytes                                       │                    │
│   signals.csi_data.emit(data)  ─────────────────────────┘ (pyqtSignal)       │
└──────────────────────────────────────────────────────────────────────────────┘
                                                                 ▼
                                                       Signal: csi_data
                                                                 ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                   processing/bcm4366c0_parser.py                             │
│                  class BCM4366C0Parser (CSIParser)                           │
│ - on_new_data(data):                                                         │
│     → process_queued_data()                                                  │
│     → extract_csi_data()                                                     │
│     → buffer.put(csi_packet) → CircularBuffer                                │
└──────────────────────────────────────────────────────────────────────────────┘

 ┌──────────────────────────┐         ┌─────────────────────────────┐
 │   CircularBuffer         │◄────────┤      QMutex                 │
 │ (thread-safe FIFO queue) │         │ (mutex for thread sync)     │
 └──────────────────────────┘         └─────────────────────────────┘
                                 ▲
                                 │ mutex.lock()
                                 ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                processing/csi_magnitude_processor.py                          │
│               class CSIMagnitudeProcessor (CSIProcessor)                     │
│  - run(): while not stopped                                                  │
│     → buffer.get_batch() (mutex protected)                                   │
│     → extract_magnitudes(csi_packet)                                         │
│     → detect_thresholds()                                                    │
│     → signals.fft_data.emit(spectrum)                                        │
│     → signals.threshold_exceeded.emit()                                      │
└──────────────────────────────────────────────────────────────────────────────┘
                                │                ▲
                         Signals:                │
                         fft_data, alerts        │
                                ▼                │
┌──────────────────────────────────────────────────────────────────────────────┐
│                           gui/main_window.py                                 │
│                      class MainWindow (QMainWindow)                          │
│ - update_chart(data) → chart_view.append_data(data)                          │
│ - show_threshold_alert()                                                     │
│ - update_console() ←  io/logger.py (signals.logs)                            │
└──────────────────────────────────────────────────────────────────────────────┘
                                 ▲
                                 │
┌──────────────────────────────────────────────────────────────────────────────┐
│                              io/logger.py                                    │
│                           class AppLogger                                    │
│ - success(), failure(), log() → signals.logs.emit(message)                   │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Threads
- CSIReceiver: receives binary packets from network
- CSIParser: parses packets, extracts timestamp and CSI raw data
- CSIProcessor (abstract): interface for CSI processing (e.g., threshold detection)
- CSIMagnitudeProcessor: detects magnitude peaks and sends fft data

### Signals
- csi_data
- fft_data
- logs
- start_app
- stop_app
- threshold_exceeded
- threshold_value

### Methods
- run
- on_new_data
- setup
- reset
- process_queued_data
- parse_time
- is_valid_subcarrier
- is_valid_antenna
- process_batch
- _detect_thresholds
- _emit_fft_data
- update_threshold

## Usage
```bash
python main.py
```

## Dependencies
See `requirements.txt`.

## Note
The CSIProcessor base class is now abstract, extend it for new processing types like Doppler or phase analysis.
CSIParser is generic and emits raw CSI data, leaving interpretation to the processor.
