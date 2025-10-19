#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Turntable Controller Module for Multimeter Testing System

This module provides turntable rotation control functionality for
automated multimeter positioning operations including:

- Serial communication with turntable controller
- Rotation command protocols
- Position control and feedback

Functions:
    send_turntable_rotation: Send rotation command to turntable
"""

import time
import serial
from typing import Optional

# Use system-wide serial config and command definition
from system_config import SERIAL_PORT, SERIAL_BAUDRATE
from system_config import CMD_TURNTABLE_ROTATE


def send_turntable_rotation(rotation_steps: int) -> Optional[int]:
    """
    Send turntable rotation command via serial communication.
    
    Args:
        rotation_steps: Number of rotation steps (0-255)
        
    Returns:
        Status code (1 for success, None for failure)
        
    Raises:
        serial.SerialException: If serial communication fails
    """
    try:
        # Initialize serial connection
        serial_connection = serial.Serial()
        serial_connection.baudrate = SERIAL_BAUDRATE
        serial_connection.bytesize = 8
        serial_connection.parity = 'N'
        serial_connection.stopbits = 1
        serial_connection.timeout = None
        serial_connection.port = SERIAL_PORT
        
        # Open connection
        serial_connection.open()
        serial_connection.flushInput()
        serial_connection.flushOutput()
        
        # Prepare command based on central definition
        command = CMD_TURNTABLE_ROTATE.copy()
        command[6] = rotation_steps
        
        # Send command
        serial_connection.write(bytearray(command))
        
        # Wait for response
        _ = serial_connection.readline()
        
        # Close connection
        serial_connection.close()
        
        return 1
        
    except Exception as e:
        print(f"Turntable rotation failed: {e}")
        return None


# Example usage (commented out)
# send_turntable_rotation(1)