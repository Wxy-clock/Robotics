#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration Constants for Multimeter Testing System

This module contains configuration constants used throughout the
multimeter testing system including file paths, hardware parameters,
and system limits. Database and GUI PNG dependencies have been removed.
"""

import os
from pathlib import Path

# =============================================================================
# APPLICATION INFORMATION
# =============================================================================

APPLICATION_NAME = "Multimeter Testing System"
APPLICATION_VERSION = "1.0.0"
APPLICATION_AUTHOR = "Robotics Lab"

# =============================================================================
# RUNTIME/GUI CONFIGURATION
# =============================================================================

# Centralized toggle to enable/disable GUI usage across the application.
# Set to True to run in headless mode (no GUI), or False to enable the GUI.
GUI_DISABLED = True

# =============================================================================
# FILE PATHS AND DIRECTORIES
# =============================================================================

# Base directories
UI_BASE_DIRECTORY = Path("ui/")
PHOTO_BASE_DIRECTORY = Path("data/photos/")
TEMP_IMAGE_DIRECTORY = Path("data/temp/images/")
PROBLEM_PHOTO_DIRECTORY = Path("data/photos/problem/")
TEST_PHOTO_DIRECTORY = Path("data/test_photos/")
SYSTEM_DATA_DIRECTORY = Path("data/system_data/")

# UI file paths
SYSTEM_UI_FILE = UI_BASE_DIRECTORY / "system.ui"
MULTIMETER_UI_FILE = UI_BASE_DIRECTORY / "multimeter_interface.ui"
EQUIPMENT_UI_FILE = UI_BASE_DIRECTORY / "equipment_manager.ui"
MEASUREMENT_UI_FILE = UI_BASE_DIRECTORY / "measurement_runner.ui"
MANUAL_MEASUREMENT_UI_FILE = UI_BASE_DIRECTORY / "manual_measurement_runner.ui"
TURNTABLE_UI_FILE = UI_BASE_DIRECTORY / "turntable_controller.ui"
NEW_MULTIMETER_UI_FILE = UI_BASE_DIRECTORY / "new_multimeter_registration.ui"
REPORT_UI_FILE = UI_BASE_DIRECTORY / "report_generator.ui"
DATA_MANAGER_UI_FILE = UI_BASE_DIRECTORY / "data_manager.ui"
QUERY_UI_FILE = UI_BASE_DIRECTORY / "data_query.ui"
QUERY_RESULT_UI_FILE = UI_BASE_DIRECTORY / "query_result.ui"

# Non-GUI temp paths retained if used elsewhere
BLACK_IMAGE_PATH = TEMP_IMAGE_DIRECTORY / "black.png"
RECOGNITION_RESULT_PATH = TEMP_IMAGE_DIRECTORY / "recognition_result.png"

# Default data paths
DEFAULT_EXCEL_IMPORT_PATH = SYSTEM_DATA_DIRECTORY / "import"
DEFAULT_EXPORT_PATH = Path("data/export/")

# =============================================================================
# HARDWARE CONFIGURATION
# =============================================================================

# Serial communication
SERIAL_PORT = "COM7"
SERIAL_BAUDRATE = 9600
SERIAL_TIMEOUT = 1

# Robot arm configuration
ROBOT_IP_ADDRESS = "192.168.58.2"
ROBOT_TOOL_COUNT = 4
SAFE_HEIGHT_Z = -40.000
PHOTO_SAFE_HEIGHT = 31.217

# Robot coordinate system
ROBOT_RX_RY_RZ = [179.897, -0.462, -87.159]
TOOL_COORDINATE_X = -98.024
TOOL_COORDINATE_Y = -10.752

# Fixture height compensations (for different probe lengths)
FIXTURE_HEIGHT_COMPENSATIONS = [-125.000, -115.000, -110.000, -105.000]

# Position offsets
POSITION_OFFSET_X = -5
POSITION_OFFSET_Y = 12.7

# =============================================================================
# NETWORK/PROXY CONFIGURATION
# =============================================================================

# Centralized proxy configuration (set here instead of OS environment)
# Enable to route robot communication through a local/remote proxy endpoint
ROBOT_PROXY_ENABLED = True
# Proxy host/IP when proxy is enabled
ROBOT_PROXY_ENDPOINT = "127.0.0.1"
# Optional host/IP override for direct mode when proxy is disabled; set to None to use ROBOT_IP_ADDRESS
ROBOT_ENDPOINT_OVERRIDE = None


def is_proxy_enabled() -> bool:
    """Return True if proxy mode is enabled via configuration."""
    return bool(ROBOT_PROXY_ENABLED)


def get_proxy_endpoint() -> str:
    """Return the configured proxy endpoint host/IP."""
    return str(ROBOT_PROXY_ENDPOINT)


def get_robot_endpoint_override():
    """Return optional direct-mode endpoint override (or None)."""
    return ROBOT_ENDPOINT_OVERRIDE

# =============================================================================
# MEASUREMENT CONFIGURATION
# =============================================================================

# Measurement limits and ranges
MAX_MEASUREMENT_COUNT = 8
MIN_MEASUREMENT_COUNT = 1
DEFAULT_MEASUREMENT_COUNT = 2

# Measurement vector sizes
MEASUREMENT_VECTOR_SIZE = 5

# Pressure thresholds
TURNTABLE_PRESSURE_THRESHOLD = 0.80
PROBE_INSERTION_PRESSURE_THRESHOLD = 0.03
MULTIMETER_PLANE_PRESSURE_THRESHOLD = 0.03

# Timing constants (in seconds)
MEASUREMENT_DELAY = 2
COMMUNICATION_TIMEOUT = 1
ROTATION_DELAY = 5
PROBE_INSERTION_DELAY = 1

# =============================================================================
# MULTIMETER MODELS AND TYPES
# =============================================================================

# Supported multimeter models
MULTIMETER_MODEL_LIST = [
    'FlUKE1', 'VICTORY1', 'KLET1', 'PLAY1', 
    'NEW1', 'TREATR1', 'ZHUYI1'
]

# Multimeter type mappings
MULTIMETER_TYPE_LIST = [
    'FlUKE', 'VICTORY', 'KLET', 'PLAY', 
    'NEW', 'TREATR', 'ZHUYI'
]

# Standard test multimeter models
FLUKE_MODEL = 'FLUKE&17B+'
VICTOR_MODEL = 'VICTOR&VC890C+'

# =============================================================================
# IMAGE PROCESSING CONFIGURATION
# =============================================================================

# Image processing parameters
IMAGE_PROCESSING_TARGET_WIDTH = 640
IMAGE_PROCESSING_TARGET_HEIGHT = 640
IMAGE_STANDARD_WIDTH = 1024

# Crop parameters for LCD detection
LCD_CROP_LEFT = 100
LCD_CROP_RIGHT = 800
LCD_CROP_TOP = 200
LCD_CROP_BOTTOM = 800

# Recognition confidence thresholds
DIGIT_RECOGNITION_CONFIDENCE_THRESHOLD = 0.3
QR_CODE_RECOGNITION_ATTEMPTS = 6

# Rotation angles for image correction
DEFAULT_ROTATION_ANGLE = -9
ROTATION_ANGLE_VARIATIONS = [-15, -16, -18, -19, -17]

# =============================================================================
# SYSTEM LIMITS AND CONSTRAINTS
# =============================================================================

# Equipment limits
MAX_EQUIPMENT_POSITIONS = 8
MIN_EQUIPMENT_POSITIONS = 1

# Measurement accuracy thresholds
PERFECT_ACCURACY_THRESHOLD = 0.5  # ¡À0.5%
ACCEPTABLE_ACCURACY_THRESHOLD = 1.0  # ¡À1.0%
MAXIMUM_ACCURACY_THRESHOLD = 5.0  # ¡À5.0%

# Voltage and current accuracy thresholds
VOLTAGE_ACCURACY_THRESHOLD = 1.0  # ¡À1.0%
RESISTANCE_CURRENT_ACCURACY_THRESHOLD = 0.5  # ¡À0.5%

# File size and count limits
MAX_EXPORTED_FILES = 1000
MAX_LOG_FILE_SIZE_MB = 100

# =============================================================================
# ERROR CODES AND STATUS
# =============================================================================

# System status codes
STATUS_SUCCESS = 1
STATUS_COMMUNICATION_FAILURE = -1
STATUS_PARAMETER_ERROR = -2
STATUS_HARDWARE_ERROR = -3
STATUS_DATA_ERROR = -4
STATUS_TIMEOUT_ERROR = -5

# Error messages
ERROR_MESSAGES = {
    STATUS_COMMUNICATION_FAILURE: "Communication failure with hardware",
    STATUS_PARAMETER_ERROR: "Invalid parameter provided",
    STATUS_HARDWARE_ERROR: "Hardware malfunction detected",
    STATUS_DATA_ERROR: "Data processing error",
    STATUS_TIMEOUT_ERROR: "Operation timeout"
}

# =============================================================================
# VALIDATION RULES
# =============================================================================

# Input validation patterns
SERIAL_NUMBER_PATTERN = r"^[A-Z0-9]{6,20}$"
MODEL_TYPE_PATTERN = r"^[A-Z]+&[A-Z0-9+]+$"

# Measurement value ranges
MIN_VOLTAGE_VALUE = -1000.0
MAX_VOLTAGE_VALUE = 1000.0
MIN_CURRENT_VALUE = -10.0
MAX_CURRENT_VALUE = 10.0
MIN_RESISTANCE_VALUE = 0.0
MAX_RESISTANCE_VALUE = 100000000.0

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

# Log levels
LOG_LEVEL_DEBUG = "DEBUG"
LOG_LEVEL_INFO = "INFO"
LOG_LEVEL_WARNING = "WARNING"
LOG_LEVEL_ERROR = "ERROR"
LOG_LEVEL_CRITICAL = "CRITICAL"

# Default log level
DEFAULT_LOG_LEVEL = LOG_LEVEL_INFO

# Log file paths
LOG_DIRECTORY = Path("logs/")
MAIN_LOG_FILE = LOG_DIRECTORY / "multimeter_system.log"
ERROR_LOG_FILE = LOG_DIRECTORY / "errors.log"
MEASUREMENT_LOG_FILE = LOG_DIRECTORY / "measurements.log"

# =============================================================================
# EXPORT AND REPORT CONFIGURATION
# =============================================================================

# Export file formats
EXCEL_FILE_EXTENSION = ".xlsx"
CSV_FILE_EXTENSION = ".csv"
PDF_FILE_EXTENSION = ".pdf"

# Report template information
REPORT_TEMPLATE_COLUMNS = [
    "Serial Number", "Model Type", "Measurement Time", "Unit", "Measured Value",
    "Test Value 1", "Test Value 2", "Test Value 3", "Average Value",
    "Maximum Value", "Minimum Value", "Error Value", "Relative Error",
    "Repeatability", "Result", "Status"
]

# Date format for reports
REPORT_DATE_FORMAT = "%Y-%m-%d"
TIMESTAMP_FORMAT = "%Y%m%d%H%M%S"

# =============================================================================
# COMMUNICATION PROTOCOL
# =============================================================================

# Serial command definitions (for microcontroller communication)
CMD_REQUEST_PRESSURE = [0x01, 0xAA, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFE, 0xEF]
CMD_GRIP_CLOSE = [0x01, 0x90, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFE, 0xEF]
CMD_GRIP_OPEN = [0x01, 0x91, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFE, 0xEF]
CMD_TURNTABLE_ROTATE = [0x01, 0x21, 0x00, 0x00, 0x00, 0x00, 0x02, 0xFE, 0xEF]
CMD_TURNTABLE_START = [0x01, 0x60, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFE, 0xEF]
CMD_TURNTABLE_STOP = [0x01, 0x61, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFE, 0xEF]
CMD_PROBE_EXTEND = [0x01, 0x50, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFE, 0xEF]
CMD_PROBE_RETRACT = [0x01, 0x51, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFE, 0xEF]
CMD_PROBE_FORWARD = [0x01, 0x52, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFE, 0xEF]
CMD_PROBE_BACKWARD = [0x01, 0x53, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFE, 0xEF]
CMD_VOICE_ALERT = [0x01, 0x83, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFE, 0xEF]

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def ensure_directory_exists(directory_path):
    """
    Ensure that a directory exists, create it if it doesn't.
    
    Args:
        directory_path (Path or str): Path to the directory
    """
    Path(directory_path).mkdir(parents=True, exist_ok=True)


def get_full_path(relative_path):
    """
    Get full path from relative path.
    
    Args:
        relative_path (str): Relative path
        
    Returns:
        Path: Full path object
    """
    return Path(relative_path).resolve()


def validate_file_path(file_path):
    """
    Validate that a file path exists and is accessible.
    
    Args:
        file_path (Path or str): Path to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        return Path(file_path).exists() and Path(file_path).is_file()
    except (OSError, ValueError):
        return False


# Initialize required directories on module import
def _initialize_directories():
    """Initialize all required directories."""
    directories_to_create = [
        PHOTO_BASE_DIRECTORY,
        TEMP_IMAGE_DIRECTORY,
        PROBLEM_PHOTO_DIRECTORY,
        TEST_PHOTO_DIRECTORY,
        LOG_DIRECTORY
    ]
    
    for directory in directories_to_create:
        ensure_directory_exists(directory)


# Run initialization
_initialize_directories()

# =============================================================================
# ENVIRONMENT VALIDATION
# =============================================================================

def validate_environment():
    """
    Validate the system environment and required files.
    
    Returns:
        tuple: (is_valid, error_messages)
    """
    error_messages = []
    
    # Check if UI files exist
    ui_files = [
        SYSTEM_UI_FILE,
        MULTIMETER_UI_FILE,
        EQUIPMENT_UI_FILE,
        MEASUREMENT_UI_FILE
    ]
    
    for ui_file in ui_files:
        if not validate_file_path(ui_file):
            error_messages.append(f"Missing UI file: {ui_file}")
    
    # Removed model file validation to avoid hard dependency
    # if not validate_file_path(DIGIT_RECOGNITION_MODEL_PATH):
    #     error_messages.append(f"Missing model file: {DIGIT_RECOGNITION_MODEL_PATH}")
    
    # Check if directories are writable
    test_directories = [
        PHOTO_BASE_DIRECTORY,
        TEMP_IMAGE_DIRECTORY,
        LOG_DIRECTORY
    ]
    
    for directory in test_directories:
        try:
            test_file = directory / "test_write.tmp"
            test_file.touch()
            test_file.unlink()
        except (OSError, PermissionError):
            error_messages.append(f"Directory not writable: {directory}")
    
    return len(error_messages) == 0, error_messages


if __name__ == "__main__":
    # Validate environment when run directly
    is_valid, errors = validate_environment()
    
    if is_valid:
        print("Environment validation passed!")
    else:
        print("Environment validation failed:")
        for error in errors:
            print(f"  - {error}")