# Robotics - Automated Multimeter Testing System

This project is an automated testing system for multimeters using a robotic arm, computer vision, and a dedicated graphical user interface. The system is designed to automate the process of testing various functions of multimeters, recording the results, and ensuring accuracy through a combination of hardware control and software logic.

## Software Architecture

The application is built using Python and the PySide2 library for the graphical user interface. It follows a modular architecture:

1.  **GUI (`multimeter_gui.py`)**: The main entry point and user interface, providing controls for all system operations.
2.  **Robot Control (`robot_controller.py`)**: Manages the robotic arm's movements, including positioning and probe handling. It communicates with the robot hardware and a MySQL database for position data.
3.  **Hardware Controllers**:
    *   `turntable_controller.py`: Controls the turntable via serial communication.
    *   `MvCameraControl_class.py` and related modules: Provide the interface for the machine vision camera.
4.  **Configuration (`system_config.py`)**: Stores static configuration data like IP addresses, serial ports, and database credentials.
5.  **Database**: A MySQL database is used to store test results, multimeter calibration data, and system state.

## Installation and Setup

1.  **Prerequisites**:
    *   Python 3
    *   Required Python packages: `pyserial`, `pymysql`, `opencv-python`, `numpy`, `openpyxl`, `pandas`, `PySide2`.
2.  **Hardware**:
    *   A compatible robotic arm.
    *   A machine vision camera.
    *   A turntable mechanism with a serial controller.
    *   A microcontroller for gripper and sensor communication.
    *   A MySQL database server.
3.  **Configuration**:
    *   Update `system_config.py` with the correct IP addresses, serial port details, and database credentials.
    *   Ensure the robot, camera, and controllers are connected and powered on.

## Usage Instructions

1.  **Launch the application**:
    ```bash
    python multimeter_gui.py
    ```
2.  **System Initialization**:
    *   The application starts with a system interface.
    *   Click the "Test Communication" button to verify connections to all hardware components (robot, database, camera, etc.).
    *   Once all tests pass, the button to enter the main multimeter interface will become available.
3.  **Main Interface**:
    *   From the main screen, you can navigate to different modules:
        *   **Equipment Management**: Mount or unmount multimeters.
        *   **Start Measurement**: Begin an automated testing sequence.
        *   **Manual Measurement**: Perform individual test steps manually.
        *   **Data Management**: View and manage test data.
        *   **Turntable Control**: Manually control the turntable.
        *   **New Multimeter**: Register a new multimeter model by importing data from an Excel file.

---

## New: Pressure/Gripper via Middleman Proxy (no local COM port required)

When the microcontroller (pressure sensor / gripper) is physically attached to a middleman PC, you can bypass the local COM port by tunneling over the same XML-RPC channel as the robot.

### What was added
- `middleman_proxy.py`: an XML-RPC proxy to run on the middleman machine. It:
  - Listens on a TCP port (default 20003)
  - Forwards unknown robot methods to the real robot (`ROBOT_UPSTREAM_HOST:20003`)
  - Implements two extra methods: `ReadPressure()` and `Gripper(close)` using the middleman¡¯s serial port
- `MicrocontrollerCommunication` supports an RPC mode. Enable with env `PRESSURE_VIA_RPC=1` on the client side.

### Deploy on the middleman
1. Ensure Python 3 is installed and the microcontroller is physically connected (visible as a COM port in Device Manager).
2. Install required package:
   ```bash
   pip install pyserial
   ```
3. Set environment and run the proxy (Windows PowerShell example):
   ```powershell
   set ROBOT_UPSTREAM_HOST=192.168.58.2
   set MICROCONTROLLER_PORT=COM3   # replace with the actual COM port on the middleman
   # optional:
   # set LISTEN_HOST=0.0.0.0
   # set LISTEN_PORT=20003
   # set SERIAL_BAUDRATE=9600
   # set SERIAL_TIMEOUT=1
   python middleman_proxy.py
   ```
4. Keep port 20004 reserved for the SDK realtime channel; the proxy only serves XML-RPC on 20003.

### Configure the client (this repository)
- Keep your existing robot proxy/tunnel pointing to the middleman¡¯s `20003` (or to the proxy port you choose).
- Enable RPC-based pressure/gripper:
  - Set `PRESSURE_VIA_RPC=1`
  - Optional: `PRESSURE_RPC_PORT=20003` if the proxy listens on a non-default port
- No local COM port is needed on the client when RPC mode is enabled.

### Environment variables summary
- On middleman:
  - `ROBOT_UPSTREAM_HOST` (robot controller IP, default `192.168.58.2`)
  - `MICROCONTROLLER_PORT` (e.g., `COM3`)
  - `LISTEN_HOST` (default `0.0.0.0`)
  - `LISTEN_PORT` (default `20003`)
  - `SERIAL_BAUDRATE` (default `9600`)
  - `SERIAL_TIMEOUT` (default `1`)
- On client:
  - `PRESSURE_VIA_RPC=1`
  - `PRESSURE_RPC_PORT` (default `20003`)
  - Existing robot proxy settings (`ROBOT_PROXY_ENABLED`, etc.) remain unchanged

### Notes
- If the middleman already runs another forwarder on `20003`, you can:
  - Run `middleman_proxy.py` on another port (e.g., `20005` via `LISTEN_PORT`), and point your tunnel to that port, or
  - Chain the proxy accordingly and keep the client `PRESSURE_RPC_PORT` in sync.
- Serial mode is still available as a fallback; `MicrocontrollerCommunication` will auto-discover local COM ports when RPC is disabled.