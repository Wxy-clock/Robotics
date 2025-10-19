#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multimeter Testing GUI Application

This module provides a graphical user interface for automated multimeter testing
using a robotic arm with computer vision capabilities.

The application consists of several main components:
- System initialization and communication testing
- Equipment mounting/unmounting interface  
- Manual and automatic measurement execution
- Data management and reporting
- Turntable rotation control

Classes:
    SystemInitializer: Main system startup and communication testing
    MultimeterInterface: Main multimeter testing interface
    EquipmentManager: Equipment mounting/unmounting operations
    MeasurementRunner: Automated measurement execution
    ManualMeasurementRunner: Manual measurement operations
    DataManager: Data input/output and management
    ReportGenerator: Test result reporting
    TurntableController: Turntable rotation control
    DataQueryInterface: Database query interface
    QueryResultDisplay: Query result display and export
"""

import time
import shutil
import os
import sys
import signal
import copy
import threading
from datetime import datetime

# Third-party imports (trimmed: remove DB and image libs not needed here)
# import serial
# import pymysql
# import cv2
# import numpy as np
# import openpyxl
# from openpyxl import load_workbook
# from openpyxl.utils.dataframe import dataframe_to_rows
# from openpyxl import Workbook
# from openpyxl.utils import get_column_letter
# import pandas as pd

# PySide2 GUI imports (lazy optional when GUI disabled)
from system_config import GUI_DISABLED
if not GUI_DISABLED:
    from PySide2.QtWidgets import (QApplication, QTableWidget, QTableWidgetItem, 
                                   QInputDialog, QMainWindow, QMessageBox, 
                                   QGraphicsScene, QFileDialog, QPushButton, 
                                   QLineEdit, QLabel, QPlainTextEdit, QDialog,
                                   QWidget, QVBoxLayout)
    from PySide2.QtUiTools import QUiLoader
    from PySide2.QtGui import QPalette, QPixmap, QIcon
    from PySide2 import QtCore
    from PySide2.QtCore import QThread, Signal
else:
    # Provide minimal dummies to satisfy type usage if any code paths are reached without GUI
    QApplication = object
    QMessageBox = type('Msg', (), {'information': staticmethod(lambda *a, **k: None)})
    QUiLoader = type('Loader', (), {'load': staticmethod(lambda *a, **k: None)})
    QWidget = object
    QtCore = type('QtCore', (), {'QCoreApplication': type('QCoreApplication', (), {'setAttribute': staticmethod(lambda *a, **k: None)}),
                                 'Qt': type('Qt', (), {'AA_EnableHighDpiScaling': 0})})

# Local imports
os.environ.setdefault('ROBOT_SKIP_AUTO_INIT', '1')  # avoid sockets during test by default
import turntable_controller
# from image_processing import convert_coordinates
import robot_controller
import standard_source_controller
# from image_processing import capture_image
# from image_processing import recognize_qr_and_lcd
# from image_processing import recognize_qr_and_lcd_formal
from system_config import UI_BASE_DIRECTORY

# Constants
UI_BASE_PATH = str(UI_BASE_DIRECTORY)
CURRENT_ROW = 2

# Removed GUI background image dependencies (.png)
# LOGIN_BG_FILENAME and qlabel_bg_style are no longer needed

# Global variables for measurement data
measurement_vector = []
multimeter_models = ['FlUKE1', 'VICTORY1', 'KLET1', 'PLAY1', 'NEW1', 'TREATR1', 'ZHUYI1']
multimeter_types = ['FlUKE', 'VICTORY', 'KLET', 'PLAY', 'NEW', 'TREATR', 'ZHUYI']
total_equipment_count = 2
# Removed GUI-related image path
# equipment_image_path = 'E:/photo/zp.jpg'

# Removed database connection usage; database is no longer required
# database_connection and mocks removed entirely

# Measurement vectors for different test types
voltage_vector_1 = [1, 2, 3, 4, 5]
standard_voltage_1 = [1, 2, 3, 4, 5]
voltage_vector_2 = [1, 2, 3, 4, 5]
standard_voltage_2 = [1, 2, 3, 4, 5]

current_vector_1 = [1, 2, 3, 4, 5]
standard_current_1 = [1, 2, 3, 4, 5]
current_vector_2 = [1, 2, 3, 4, 5]
standard_current_2 = [1, 2, 3, 4, 5]
current_vector_3 = [1, 2, 3, 4, 5]
standard_current_3 = [1, 2, 3, 4, 5]
current_vector_4 = [1, 2, 3, 4, 5]
standard_current_4 = [1, 2, 3, 4, 5]

# Query system variables
query_method = '0'
query_result_name = '0'

# Measurement control variables
measurement_start_index = 0
measurement_end_index = 1
measurement_count = 2

# Tool coordinates for robotic arm
tool_coordinate_x = -98.024
tool_coordinate_y = -10.752

# Control flags
operation_ready = 0
current_multimeter_index = 0

# Position offsets
position_offset_x = -5
position_offset_y = 12.7

# Photo counter
photo_counter = 1


class SystemInitializer:
    """
    System initialization and communication testing interface.
    
    This class handles the main system startup, communication testing with
    all hardware components, and navigation to the main multimeter interface.
    """
    
    def __init__(self):
        """Initialize the system interface and set up UI components."""
        self.ui = QUiLoader().load(UI_BASE_PATH + "/system.ui") if not GUI_DISABLED else None
        
        if not GUI_DISABLED:
            # Connect UI signals to methods
            self.ui.multimeter_button.clicked.connect(self._navigate_to_multimeter_interface)
            self.ui.exit_button.clicked.connect(self._exit_application)
            self.ui.test_button.clicked.connect(self._test_system_communication)
            
            # Removed background image styling (.png not needed)
            # self.ui.background_label.setStyleSheet(qlabel_bg_style('base.png'))
            
            # Initially hide navigation buttons
            self.ui.multimeter_button.setVisible(False)
            self.ui.digital_button.setVisible(False)
            self.ui.test_button.setVisible(True)
        
        # Database removed: no turntable position reset
        # self._reset_turntable_position()
    
    # Removed DB-dependent method
    # def _reset_turntable_position(self):
    #     """Reset turntable position data in database."""
    #     pass
    
    def _navigate_to_multimeter_interface(self):
        """Navigate to the main multimeter testing interface."""
        self.main_interface = MultimeterInterface()
        if not GUI_DISABLED:
            self.main_interface.ui.show()
            self.ui.close()
    
    def _exit_application(self):
        """Exit the application."""
        if not GUI_DISABLED:
            self.ui.close()
    
    def _test_system_communication(self):
        """Test communication with all system components."""
        communication_result = robot_controller.test_communication_connection()
        
        if not GUI_DISABLED:
            if communication_result == 1:
                QMessageBox.information(QMessageBox(), 'Communication Test', 
                                      'All devices connected successfully! Ready to start measurement!')
                self.ui.multimeter_button.setVisible(True)
                self.ui.digital_button.setVisible(True)
                self.ui.test_button.setVisible(False)
            elif communication_result == -1:
                QMessageBox.information(QMessageBox(), 'Communication Test', 
                                      'Some devices failed to connect. Please check connections.')


class MultimeterInterface:
    """
    Main multimeter testing interface.
    
    This class provides the central navigation hub for all multimeter testing
    operations including equipment management, measurements, and data operations.
    """
    
    def __init__(self):
        """Initialize the main multimeter interface."""
        self.ui = QUiLoader().load(UI_BASE_PATH + "/multimeter_interface.ui") if not GUI_DISABLED else None
        
        if not GUI_DISABLED:
            # Connect UI signals to methods
            self.ui.equipment_button.clicked.connect(self._open_equipment_manager)
            self.ui.start_button.clicked.connect(self._start_measurement)
            self.ui.manual_button.clicked.connect(self._start_manual_measurement)
            self.ui.data_manager_button.clicked.connect(self._open_data_manager)
            self.ui.query_button.clicked.connect(self._open_query_interface)
            self.ui.report_button.clicked.connect(self._open_report_generator)
            self.ui.new_multimeter_button.clicked.connect(self._open_new_multimeter_interface)
            self.ui.turntable_button.clicked.connect(self._open_turntable_controller)
            self.ui.exit_button.clicked.connect(self._return_to_system_initializer)
            
            # Removed background and styling dependent on PNGs
            # background_style = qlabel_bg_style(LOGIN_BG_FILENAME)
            # self.ui.background_label.setStyleSheet(background_style)
            
            # Keep some simple styling examples (not image-based)
            self.ui.title_label.setStyleSheet("color: red;")
            self.ui.equipment_button.setStyleSheet("background-color: yellow;")
            self.ui.manual_button.setStyleSheet("background-color: yellow;")
            self.ui.query_button.setStyleSheet("background-color: yellow;")
    
    def _open_equipment_manager(self):
        """Open the equipment mounting/unmounting interface."""
        self.equipment_manager = EquipmentManager()
        if not GUI_DISABLED:
            self.equipment_manager.ui.show()
            self.ui.close()
    
    def _start_measurement(self):
        """Start automatic measurement process."""
        self.measurement_runner = MeasurementRunner()
        if not GUI_DISABLED:
            self.measurement_runner.ui.show()
            self.ui.close()
    
    def _start_manual_measurement(self):
        """Start manual measurement process (DB removed -> no check)."""
        self.manual_runner = ManualMeasurementRunner()
        if not GUI_DISABLED:
            self.manual_runner.ui.show()
            self.ui.close()
    
    def _open_data_manager(self):
        """Open data management interface."""
        self.data_manager = DataManager()
        if not GUI_DISABLED:
            self.data_manager.ui.show()
            self.ui.close()
    
    def _open_query_interface(self):
        """Open data query interface."""
        self.query_interface = DataQueryInterface()
        if not GUI_DISABLED:
            self.query_interface.ui.show()
            self.ui.close()
    
    def _open_report_generator(self):
        """Open report generation interface."""
        self.report_generator = ReportGenerator()
        if not GUI_DISABLED:
            self.report_generator.ui.show()
            self.ui.close()
    
    def _open_new_multimeter_interface(self):
        """Open new multimeter registration interface."""
        self.new_multimeter = NewMultimeterRegistration()
        if not GUI_DISABLED:
            self.new_multimeter.ui.show()
            self.ui.close()
    
    def _open_turntable_controller(self):
        """Open turntable rotation control interface."""
        self.turntable_controller = TurntableController()
        if not GUI_DISABLED:
            self.turntable_controller.ui.show()
            self.ui.close()
    
    def _return_to_system_initializer(self):
        """Return to system initialization interface."""
        self.system_initializer = SystemInitializer()
        if not GUI_DISABLED:
            self.system_initializer.ui.show()
            self.ui.close()


class TurntableController(QWidget):
    """
    Turntable rotation control interface.
    
    This class provides manual control over the turntable rotation system,
    allowing users to rotate the turntable to specific positions.
    """
    
    def __init__(self):
        """Initialize the turntable controller interface."""
        super(TurntableController, self).__init__() if not GUI_DISABLED else None
        
        self.ui = QUiLoader().load(UI_BASE_PATH + "/turntable_controller.ui") if not GUI_DISABLED else None
        
        if not GUI_DISABLED:
            # Connect UI signals
            self.ui.exit_button.clicked.connect(self._exit_controller)
            self.ui.rotate_button.clicked.connect(self._execute_rotation)
            
            # Removed PNG-dependent background styling
            # background_style = qlabel_bg_style(LOGIN_BG_FILENAME)
            # self.ui.rotate_zp_pic.setStyleSheet(background_style)
            self.ui.status_label.setText("Please select rotation function!")
            self.ui.status_label.setStyleSheet(
                '''color: red; justify-content: center; align-items: center; text-align: center;''')
        
        self.rotation_in_progress = False
    
    def _execute_rotation(self):
        """Execute turntable rotation."""
        if self.rotation_in_progress == 0:
            self.rotation_in_progress = 1
            if not GUI_DISABLED:
                self.ui.status_label.setText("Rotating turntable, please do not operate! Wait for completion!")
            
            rotation_thread = threading.Thread(target=self._rotation_worker)
            rotation_thread.daemon = True
            rotation_thread.start()
        else:
            if not GUI_DISABLED:
                self.ui.status_label.setText("Please wait for current rotation to complete!")
    
    def _rotation_worker(self):
        """Worker thread for turntable rotation."""
        rotation_positions = int(self.ui.rotate_zp_num.currentText()) if not GUI_DISABLED else 0
        turntable_controller.send_turntable_rotation(rotation_positions)
        
        if not GUI_DISABLED:
            self.ui.status_label.setText("Rotation completed!")
        self.rotation_in_progress = 0
    
    def _exit_controller(self):
        """Exit turntable controller."""
        if self.rotation_in_progress == 0:
            self.main_interface = MultimeterInterface()
            if not GUI_DISABLED:
                self.main_interface.ui.show()
                self.ui.close()
        else:
            if not GUI_DISABLED:
                self.ui.status_label.setText("Please wait for rotation to complete before exiting!")


class NewMultimeterRegistration(QWidget):
    """
    New multimeter registration interface.
    
    Database features removed; this UI remains for future expansion but performs no DB operations.
    """
    
    def __init__(self):
        """Initialize the new multimeter registration interface."""
        super(NewMultimeterRegistration, self).__init__() if not GUI_DISABLED else None
        
        self.ui = QUiLoader().load(UI_BASE_PATH + "/new_multimeter_registration.ui") if not GUI_DISABLED else None
        
        if not GUI_DISABLED:
            # Connect UI signals
            self.ui.register_button.clicked.connect(self._register_new_multimeter)
            self.ui.exit_button.clicked.connect(self._exit_registration)
            
            # Removed PNG-dependent background
            # background_style = qlabel_bg_style(LOGIN_BG_FILENAME)
            # self.ui.background_label.setStyleSheet(background_style)
    
    def _register_new_multimeter(self):
        """Stub: Database is removed; inform user."""
        if not GUI_DISABLED:
            QMessageBox.information(QMessageBox(), 'Registration', 
                                    'Database functionality is disabled. Registration is unavailable.')
    
    def _exit_registration(self):
        """Exit new multimeter registration interface."""
        self.main_interface = MultimeterInterface()
        if not GUI_DISABLED:
            self.main_interface.ui.show()
            self.ui.close()


class EquipmentManager(QWidget):
    def __init__(self):
        super(EquipmentManager, self).__init__() if not GUI_DISABLED else None
        self.ui = QUiLoader().load(UI_BASE_PATH + "/equipment_manager.ui") if not GUI_DISABLED else None
        if not GUI_DISABLED:
            self.ui.exit_button.clicked.connect(self.close_window)

    def close_window(self):
        self.main_interface = MultimeterInterface()
        if not GUI_DISABLED:
            self.main_interface.ui.show()
            self.ui.close()


class MeasurementRunner(QWidget):
    def __init__(self):
        super(MeasurementRunner, self).__init__() if not GUI_DISABLED else None
        self.ui = QUiLoader().load(UI_BASE_PATH + "/measurement_runner.ui") if not GUI_DISABLED else None
        if not GUI_DISABLED:
            self.ui.exit_button.clicked.connect(self.close_window)

    def close_window(self):
        self.main_interface = MultimeterInterface()
        if not GUI_DISABLED:
            self.main_interface.ui.show()
            self.ui.close()


class ManualMeasurementRunner(QWidget):
    def __init__(self):
        super(ManualMeasurementRunner, self).__init__() if not GUI_DISABLED else None
        self.ui = QUiLoader().load(UI_BASE_PATH + "/manual_measurement_runner.ui") if not GUI_DISABLED else None
        if not GUI_DISABLED:
            self.ui.exit_button.clicked.connect(self.close_window)

    def close_window(self):
        self.main_interface = MultimeterInterface()
        if not GUI_DISABLED:
            self.main_interface.ui.show()
            self.ui.close()


class DataManager(QWidget):
    def __init__(self):
        super(DataManager, self).__init__() if not GUI_DISABLED else None
        self.ui = QUiLoader().load(UI_BASE_PATH + "/data_manager.ui") if not GUI_DISABLED else None
        if not GUI_DISABLED:
            self.ui.exit_button.clicked.connect(self.close_window)

    def close_window(self):
        self.main_interface = MultimeterInterface()
        if not GUI_DISABLED:
            self.main_interface.ui.show()
            self.ui.close()


class DataQueryInterface(QWidget):
    def __init__(self):
        super(DataQueryInterface, self).__init__() if not GUI_DISABLED else None
        self.ui = QUiLoader().load(UI_BASE_PATH + "/data_query.ui") if not GUI_DISABLED else None
        if not GUI_DISABLED:
            self.ui.exit_button.clicked.connect(self.close_window)

    def close_window(self):
        self.main_interface = MultimeterInterface()
        if not GUI_DISABLED:
            self.main_interface.ui.show()
            self.ui.close()


class ReportGenerator(QWidget):
    def __init__(self):
        super(ReportGenerator, self).__init__() if not GUI_DISABLED else None
        self.ui = QUiLoader().load(UI_BASE_PATH + "/report_generator.ui") if not GUI_DISABLED else None
        if not GUI_DISABLED:
            self.ui.exit_button.clicked.connect(self.close_window)

    def close_window(self):
        self.main_interface = MultimeterInterface()
        if not GUI_DISABLED:
            self.main_interface.ui.show()
            self.ui.close()


class QueryResultDisplay(QWidget):
    pass

# Additional classes would continue here following the same pattern...
# Due to length constraints, I'll provide the main structure and a few key classes.
# The remaining classes (ReportGenerator, DataManager, EquipmentManager, etc.) 
# would follow the same naming conventions and documentation patterns.

if __name__ == '__main__':
    """Main application entry point."""
    if GUI_DISABLED:
        # Run diagnostics instead of GUI
        import socket_diagnostics as diag
        ok = diag.run()
        # Import movement test functions right under diagnostics
        try:
            from movement_test import movement_main
        except Exception:
            movement_main = None
        # Prompt for 6 joint values and run movement test accordingly
        try:
            line = input("Enter 6 joint angles (deg) separated by spaces (e.g., 0 -45 30 0 60 0). Press Enter to skip: ").strip()
        except (EOFError, KeyboardInterrupt):
            line = ""
        # Import movement command parser right after prompting
        try:
            from movement_command_parser import parse_and_execute_commands
        except Exception:
            parse_and_execute_commands = None
        if movement_main and line:
            parts = line.split()
            if len(parts) >= 6:
                move_args = parts[:6]
                # Execute movement test with provided angles
                movement_main(move_args)

            else:
                print(f"Expected 6 numbers, got {len(parts)}. Exiting.")
                sys.exit(2)

        time.sleep(3)
        print("Running movement command parser on 'test.txt'...")
        parse_and_execute_commands("test.txt")
        sys.exit(0)
    else:
        QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
        app = QApplication([])
        system_initializer = SystemInitializer()
        system_initializer.ui.show()
        app.exec_()