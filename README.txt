CSI STREAMING APP READ ME

PURPOSES :
This application collects, streams, processes and displays CSI in real time.
Offers many possibilities for real time HAR.

FEATURES :
Modularity in sniffing devices. As of now, collection is possible with RPi4 and ASUS AC86U.
Modularity in processing methods. As of now, magnitude extraction, moving average filtering, mean value of subcarriers range.
Centralized control panel. Collection, streaming, saving and rebooting is done through the application.

PREREQUISITES :
Sniffing device must be patched with corresponding nexmon patch from nexmon csi git repo.
For RPi4 : all files in the nexmon_rpi folder must be transfered to the device, a python venv must be installed and boot version must be the same as given in the folder. Never update software otherwise flash the sd card with the provided image. To use CSPI, the RPi4 must be used with default user.
For ASUS AC86U : all files in the nexmon_router folder must be transfered to the device and use "chmod +x /jffs/setup_env /jffs/start_stream /jffs/stop_stream /jffs/save_data".
For AP : 2.4GHz and 5GHz should be separated. When connecting your laptop to AP check channel and bandwidth. Recommanded channel is 44 and bandwidth is 80MHz.
For laptop : install all dependancies, install a python venv, run the app on a Linux system.
For dependancies check requirements.txt file.

HOW TO USE :
Check if AP and sniffing device are configured as mentionned above.
Connect your laptop to AP wifi.
Connect your sniffing device to the laptop with LAN cable. 
Check IP addresses for each device and correct the MACROS in settings.py file.
Change the import in main.py, the sniffer thread declaration depending on used device.
The space between the devices should be at least 50cm, otherwise CSI data is not usable.
Run main.py file, in this order, press "Start", "Connect to sniffer", "Setup sniffer", "Start stream", "Save data", "Stop stream" and "Disconnect".

HOW TO MODIFY THE APP :
To add sniffing devices, a corresponding parser must be implemented with the use of abstract class CSI_PARSER. A corresponding remote control must be implemented with the use of abstract class REMOTE_DEVICE. Slots and signals from buttons should be connected in main_window.py file. MACROS can be added in settings.py. Class importation in main.py can be changed depending on the device, sniffer thread must be changed depending on the sniffing device.
To add processing methods, a corresponding processor must be implemented with the use of abstract class CSI_PROCESSOR. Implementation must respect the logic of other processors with the use of signals, circular buffer and mutex.

TECHNICAL DESCRIPTION :
The CSI STREAMING APP uses PYQT5 tools to implement a multi threaded architecture. The pipeline is the following : A threaded UDP listener waits for data, when received, data is transmitted with a signal to a threaded specific parser to decode data and store it into a mutex protected circular buffer. A threaded processor accesses the buffer, processes the data and emits a signal to the chart and update the UI, extracted and processed data is then displayed on the chart in "real time". Estimated delay is around 1 second. Delay is due to the forwarding of data (UDP is faster than TCP but delay still occurs), each step of the pipeline introduces delay though limited with the use of threads, buffers and queues.

OPTIMIZATION PERSPECTIVES :
UDP forwarding allows great reactivity and speed but introduces packet loss that corrupts the CSI. TCP solves this problem but slows down the pipeline. When enough CSI is collected (high frequency of pings), packet loss becomes negligeable.
Pipeline can be optimized with manual parsing instead of imported library.
For AI model use (Doppler velocity pattern recognition), the window of the chart must be constant, optimal pattern recognition should be in the middle. A proper window length should be implemented for better pattern recognition and keep the "real time" aspect. AI model requires much more CPU capacity and memory. Quantisize the model is one way to help with memory management. Using another process instead of a thread to run the model grants more CPU capacity to the app and the model. Use message queues or queues for communication/synchronization of the processes.

Written by The Phong DOUANGMANIVONG.

