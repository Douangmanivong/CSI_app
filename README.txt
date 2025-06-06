1st draft of app structure, cpp compilation and execution is faster thus only using signals and slots on QT. For python coding only, multi-threading is necessary to allow real-time reception, processing and display of CSI data spectrum. 

TCP loop, parsing, processing and UI are in separate threads to allow real-time. Buffer is used to store CSI data between parsing and processing. Processing is in a thread to allow the possibility to add AI model for better detection in the future.

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
│   signals.raw_data_received.emit(data)  ────────────────┘ (pyqtSignal)       │
└──────────────────────────────────────────────────────────────────────────────┘
                                                                 ▼
                                                       Signal: raw_data_received
                                                                 ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           processing/parser.py                               │
│                        class CSIParser (QThread)                             │
│ - on_new_data(data):                                                         │
│     → process_pcap(data)                                                     │
│     → parse_to_numpy()                                                       │
│     → buffer.put(data_numpy) → CircularBuffer                                │
└──────────────────────────────────────────────────────────────────────────────┘

 ┌──────────────────────────┐         ┌─────────────────────────────┐
 │   CircularBuffer         │◄────────┤      QMutex                 │
 │ (thread-safe FIFO queue) │         │ (mutex for thread sync)     │
 └──────────────────────────┘         └─────────────────────────────┘

                                 ▲
                                 │ mutex.lock()
                                 ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                      processing/csi_processor.py                             │
│                    class CSIProcessor (QThread)                              │
│  - run(): while True                                                         │
│     → buffer.get_batch() (mutex protected)                                   │
│     → process_fft(batch)                                                     │
│     → detect_thresholds()                                                    │
│     → run_model(batch)  ←  (AI model in the future)                          │
│     → signals.fft_data.emit(spectrogram)                                     │
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

Hardware:
- Raspberry Pi 4 : sends ICMP pings to the router
- Router (OpenWRT + Nexmon CSI): emits CSI via TCP
- Laptop (runs the app): receives, processes and displays CSI data

Shared Tools:
- `CircularBuffer`: connects Parser → Processor
- `QMutex`: ensures safe concurrent access to buffer

Threads:
- CSIReceiver (QThread)
- CSIParser (QThread)
- CSIProcessor (QThread)
- MainWindow (Qt main GUI thread)
