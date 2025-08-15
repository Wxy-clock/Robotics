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

# Turntable communication constants
SERIAL_PORT = 'COM7'  # Serial port number
UART_BAUDRATE = 9600  # Baud rate
ROTATION_COMMAND = [0x01, 0x20, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFE, 0xEF]


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
    global ROTATION_COMMAND
    
    try:
        # Initialize serial connection
        serial_connection = serial.Serial()
        serial_connection.baudrate = UART_BAUDRATE
        serial_connection.bytesize = 8
        serial_connection.parity = 'N'
        serial_connection.stopbits = 1
        serial_connection.timeout = None
        serial_connection.port = SERIAL_PORT
        
        # Open connection
        serial_connection.open()
        serial_connection.flushInput()
        serial_connection.flushOutput()
        
        # Set rotation value in command
        ROTATION_COMMAND[6] = rotation_steps
        
        # Send command
        serial_connection.write(bytearray(ROTATION_COMMAND))
        
        # Wait for response
        response = serial_connection.readline()
        
        # Close connection
        serial_connection.close()
        
        return 1
        
    except Exception as e:
        print(f"Turntable rotation failed: {e}")
        return None


# Example usage (commented out)
# send_turntable_rotation(1)