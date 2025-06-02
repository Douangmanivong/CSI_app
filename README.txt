# CSI Real-Time Movement Detection Application

This application is designed to **receive, process, and visualize CSI (Channel State Information) data in real time**. The data is captured using the **Nexmon CSI framework** from a **compatible Asus router** and transmitted via TCP to a **Raspberry Pi 4**, where it is processed and analyzed.

## Features

- **TCP reception** of raw CSI data from a Nexmon-enabled Asus router.
- **Parsing, filtering, and transformation** of raw data into structured **NumPy arrays**.
- **Real-time visualization** of CSI data using spectrogram representations.
- **Amplitude-based motion detection** derived from spectrogram changes in real time.
- Modular architecture designed for future integration of a trained **AI model** for enhanced real-time **motion recognition**.

## Architecture Overview

1. **Data Acquisition**:  
   CSI data is transmitted via a TCP socket from the Asus router running the Nexmon CSI framework.

2. **Preprocessing**:  
   The raw data is parsed, filtered, and converted into numerical format using NumPy for efficient computation.

3. **Visualization**:  
   The processed data is visualized in real time as a spectrogram, enabling dynamic interpretation of the signal.

4. **Motion Detection**:  
   The application performs real-time detection of amplitude variations that correlate with physical movement.

5. **Future Work**:  
   The current amplitude-based detection module is intended to be replaced by a trained AI model capable of classifying and recognizing specific motions in real time.

## Requirements

- Python 3.x
- NumPy
- Matplotlib (or similar for visualization)
- Socket programming (TCP client setup)

See `requirements.txt` for the full list of dependencies.

## Usage

1. Ensure the Nexmon CSI tool is correctly configured on your Asus router.
2. Run the application on a Raspberry Pi 4 connected to the same network.
3. The application will start receiving CSI data and display the real-time spectrogram.
4. Observe amplitude variations for motion detection or integrate an AI model for motion classification.

## Author

Developed as part of an internship project by TP.
