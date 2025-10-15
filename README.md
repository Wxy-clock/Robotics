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

## Contribution

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/YourFeature`).
3.  Commit your changes (`git commit -m 'Add some feature'`).
4.  Push to the branch (`git push origin feature/YourFeature`).
5.  Open a Pull Request.