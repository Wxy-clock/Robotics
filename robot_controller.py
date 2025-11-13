#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robot Controller Module for Multimeter Testing System

This module provides comprehensive robot arm control functionality for
automated multimeter testing operations including:

- Robot arm movement and positioning
- Probe handling and insertion
- Turntable rotation control
- Pressure monitoring and feedback
- Communication with microcontroller

Database dependencies have been removed.

Classes:
    RobotController: Main robot control interface
    ProbeHandler: Probe manipulation operations  
    TurntableController: Turntable rotation management
    PressureMonitor: Pressure sensing and feedback
"""

import time
import copy
import threading
import serial
from datetime import datetime
from typing import List, Tuple, Optional, Union
import os

# Third-party imports
import numpy as np
from serial.tools import list_ports  # added for serial port discovery
import xmlrpc.client  # added for RPC pressure/gripper mode

# Local imports
from system_config import *
import Robot
from proxy_connection import resolve_robot_host, is_proxy_enabled, get_proxy_endpoint

# Global robot and database connections
robot_connection = None
serial_connection = None

# Robot positioning constants
COORDINATE_SYSTEM = [0.0] * 6
EXTERNAL_AXES = [0.0] * 4
POSITION_OFFSET = [0.0] * 6

# Robot positions for fixtures and operations
fixture_positions = {
    'fixture_1_safe': None,
    'fixture_1_check': None, 
    'fixture_1_insert': None,
    'fixture_2_safe': None,
    'fixture_2_check': None,
    'fixture_2_insert': None,
    'fixture_3_safe': None,
    'fixture_3_check': None,
    'fixture_3_insert': None,
    'fixture_4_safe': None,
    'fixture_4_check': None,
    'fixture_4_insert': None,
    'start_position': None,
    'measurement_position': None
}

# Operation control variables
current_operation_state = 0
probe_positions_x = [0, 0, 0, 0]
probe_positions_y = [0, 0, 0, 0]
io_operation_interrupted = 0
multimeter_plane_z = 0.000
turntable_forward_position = 0.000
emergency_stop_requested = 0
initialization_status = 1


class RobotController:
    """
    Main robot controller class for multimeter testing operations.
    
    This class provides high-level robot control functions including
    movement, positioning, and coordination with other system components.
    """
    
    def __init__(self):
        """Initialize robot controller and establish connections."""
        self.robot = None
        self.is_connected = False
        self.current_host = None  # track current endpoint for diagnostics
        self._initialize_robot_connection()
        # DB-dependent position loading removed
    
    def _initialize_robot_connection(self):
        """Initialize connection to robot controller."""
        try:
            host = resolve_robot_host(ROBOT_IP_ADDRESS)
            self.current_host = host
            if is_proxy_enabled():
                print(f"[RobotController] Proxy Enabled = YES, Proxy Endpoint = {get_proxy_endpoint()}")
            else:
                print("[RobotController] Proxy Enabled = NO")
            self.robot = Robot.RPC(host)
            # light handshake to verify connectivity
            try:
                _ = self.robot.GetActualJointPosDegree()[1]
                self.is_connected = True
                print(f"Robot connection established successfully to {host}")
            except Exception as ping_err:
                self.is_connected = False
                print(f"Robot connection handshake failed to {host}: {ping_err}")
        except Exception as e:
            print(f"Failed to connect to robot: {e}")
            self.is_connected = False
    
    def move_to_joint_position(self, tool_number: int, velocity: float, joint_angles: List[float]):
        """
        Move robot to specified joint position.
        
        Args:
            tool_number: Tool coordinate system number
            velocity: Movement velocity percentage
            joint_angles: List of 6 joint angles in degrees
        """
        if not self.is_connected:
            raise RuntimeError("Robot not connected")
        
        # Convert to Cartesian coordinates
        cartesian_position = self.robot.GetForwardKin(joint_angles)[1]
        
        # Execute movement
        self.robot.MoveJ(joint_angles, tool_number, 1, cartesian_position, 
                        velocity, 0.0, 100.0, EXTERNAL_AXES, -1.0, 0, POSITION_OFFSET)
    
    def move_to_cartesian_position(self, tool_number: int, velocity: float, 
                                 cartesian_position: List[float]):
        """
        Move robot to specified Cartesian position.
        
        Args:
            tool_number: Tool coordinate system number
            velocity: Movement velocity percentage
            cartesian_position: [x, y, z, rx, ry, rz] position
        """
        if not self.is_connected:
            raise RuntimeError("Robot not connected")
        
        # Convert to joint angles
        joint_angles = self.robot.GetInverseKin(0, cartesian_position, -1)[1]
        
        # Execute movement
        self.robot.MoveJ(joint_angles, tool_number, 1, cartesian_position, 
                        velocity, 0.0, 100.0, EXTERNAL_AXES, -1.0, 0, POSITION_OFFSET)
    
    def move_linear(self, tool_number: int, velocity: float, 
                   cartesian_position: List[float], blend_radius: float = -1.0):
        """
        Move robot in straight line to specified position.
        
        Args:
            tool_number: Tool coordinate system number
            velocity: Movement velocity percentage
            cartesian_position: Target position [x, y, z, rx, ry, rz]
            blend_radius: Blending radius for smooth movement
        """
        if not self.is_connected:
            raise RuntimeError("Robot not connected")
        
        # Convert to joint angles
        joint_angles = self.robot.GetInverseKin(0, cartesian_position, -1)[1]
        
        # Execute linear movement
        self.robot.MoveL(cartesian_position, tool_number, 1, joint_angles, 
                        velocity, 0.0, 100.0, blend_radius)
    
    def get_current_position(self) -> Tuple[List[float], List[float]]:
        """
        Get current robot position in both joint and Cartesian coordinates.
        
        Returns:
            Tuple of (joint_angles, cartesian_position)
        """
        if not self.is_connected:
            raise RuntimeError("Robot not connected")
        
        cartesian_position = self.robot.GetActualTCPPose(1)[1]
        joint_angles = self.robot.GetActualJointPosDegree()[1]
        
        return joint_angles, cartesian_position
    
    def set_tool_coordinate_system(self, tool_number: int):
        """
        Set active tool coordinate system.
        
        Args:
            tool_number: Tool number to activate
        """
        if not self.is_connected:
            raise RuntimeError("Robot not connected")
        
        self.robot.SetToolCoord(tool_number, COORDINATE_SYSTEM, 0, 0)
    
    def stop_robot_movement(self):
        """Emergency stop robot movement."""
        if self.is_connected:
            self.robot.ProgramStop()
            self.robot.WaitMs(2000)
    
    def move_to_safe_plane(self):
        """Move robot to safe operating height."""
        if not self.is_connected:
            return
        
        try:
            self.set_tool_coordinate_system(3)
            current_joint_angles, current_position = self.get_current_position()
            current_position[2] = SAFE_HEIGHT_Z
            self.move_linear(3, 30.0, current_position)
        except Exception as e:
            print(f"Error moving to safe plane: {e}")


class ProbeHandler:
    """
    Handle probe insertion and removal operations.
    
    This class manages the robotic probes used for multimeter contact
    including insertion, positioning, and feedback monitoring.
    """
    
    def __init__(self, robot_controller: RobotController):
        """
        Initialize probe handler.
        
        Args:
            robot_controller: Robot controller instance
        """
        self.robot_controller = robot_controller
        self.microcontroller_comm = MicrocontrollerCommunication()
    
    def insert_probe(self, probe_number: int, multimeter_type: str, 
                    require_timestamp_check: bool = False) -> Tuple[int, str, str]:
        """
        Insert specified probe into multimeter.
        
        Args:
            probe_number: Probe number (1-4)
            multimeter_type: Type of multimeter
            require_timestamp_check: Whether to verify database timestamp
            
        Returns:
            Tuple of (status_code, error_message, exception_info)
        """
        global probe_positions_x, probe_positions_y, current_operation_state
        
        try:
            # Set tool coordinate system
            self.robot_controller.set_tool_coordinate_system(3)
        except Exception as e:
            current_operation_state = -1
            return -7, "Error: Failed to set tool coordinate system", str(e)
        
        # Without database, use default or previously set positions (zeros)
        # Real implementation should load from config or UI
        probe_coords = [
            [probe_positions_x[0], probe_positions_y[0]],
            [probe_positions_x[1], probe_positions_y[1]],
            [probe_positions_x[2], probe_positions_y[2]],
            [probe_positions_x[3], probe_positions_y[3]],
        ]
        
        probe_positions_x = [coord[0] for coord in probe_coords]
        probe_positions_y = [coord[1] for coord in probe_coords]
        
        # Open gripper
        self.microcontroller_comm.send_gripper_command(False)
        
        # Execute probe insertion sequence
        if probe_number == 1:
            return self._insert_probe_1()
        elif probe_number == 2:
            return self._insert_probe_2()
        elif probe_number == 3:
            return self._insert_probe_3()
        elif probe_number == 4:
            return self._insert_probe_4()
        else:
            return -4, "Error: Invalid probe number", ""
    
    def _insert_probe_1(self) -> Tuple[int, str, str]:
        """Insert probe 1 (shortest probe)."""
        try:
            # Move to fixture 1 and grab probe (using default positions)
            self._move_to_fixture_and_grab(1)
            
            # Insert into multimeter
            result = self._insert_probe_into_multimeter('kong1', 'd_k1', 1, True, 35.000)
            return result
            
        except Exception as e:
            current_operation_state = -1
            return -11, "Error: Probe 1 insertion failed", str(e)
    
    def _insert_probe_2(self) -> Tuple[int, str, str]:
        """Insert probe 2."""
        try:
            self._move_to_fixture_and_grab(2)
            result = self._insert_probe_into_multimeter('kong2', 'd_k2', 2, False, 33.000)
            return result
        except Exception as e:
            current_operation_state = -1
            return -11, "Error: Probe 2 insertion failed", str(e)
    
    def _insert_probe_3(self) -> Tuple[int, str, str]:
        """Insert probe 3."""
        try:
            self._move_to_fixture_and_grab(3)
            result = self._insert_probe_into_multimeter('kong3', 'd_k3', 3, True, 29.000)
            return result
        except Exception as e:
            current_operation_state = -1
            return -11, "Error: Probe 3 insertion failed", str(e)
    
    def _insert_probe_4(self) -> Tuple[int, str, str]:
        """Insert probe 4 (longest probe)."""
        try:
            self._move_to_fixture_and_grab(4)
            result = self._insert_probe_into_multimeter('kong4', 'd_k4', 4, True, 32.000)
            return result
        except Exception as e:
            current_operation_state = -1
            return -11, "Error: Probe 4 insertion failed", str(e)
    
    def _move_to_fixture_and_grab(self, fixture_number: int):
        """Move to fixture and grab probe."""
        # Move to safe position
        safe_pos = fixture_positions.get(f'fixture_{fixture_number}_safe') or [0, 0, SAFE_HEIGHT_Z] + ROBOT_RX_RY_RZ
        self.robot_controller.move_to_cartesian_position(3, 80.0, safe_pos)
        
        # Move to check position
        check_pos = fixture_positions.get(f'fixture_{fixture_number}_check') or [0, 0, -120.000] + ROBOT_RX_RY_RZ
        self.robot_controller.move_linear(3, 50.0, check_pos)
        
        time.sleep(1)
        
        # Move to insert position
        insert_pos = fixture_positions.get(f'fixture_{fixture_number}_insert') or [0, 0, -130.000] + ROBOT_RX_RY_RZ
        self.robot_controller.move_linear(3, 5.0, insert_pos)
        
        time.sleep(1)
        
        # Close gripper
        self.microcontroller_comm.send_gripper_command(True)
        time.sleep(1)
        
        # Return to safe position
        self.robot_controller.move_linear(3, 60.0, safe_pos)
    
    def _insert_probe_into_multimeter(self, probe_field: str, position_field: str, 
                                    probe_index: int, test_plane: bool, 
                                    pressure_threshold: float) -> Tuple[int, str, str]:
        """Insert probe into multimeter hole."""
        global multimeter_plane_z, io_operation_interrupted
        
        # Set probe positions
        probe_x = probe_positions_x[probe_index - 1]
        probe_y = probe_positions_y[probe_index - 1]
        
        safe_position = [probe_x, probe_y, SAFE_HEIGHT_Z] + ROBOT_RX_RY_RZ
        check_position = [probe_x, probe_y, FIXTURE_HEIGHT_COMPENSATIONS[probe_index - 1]] + ROBOT_RX_RY_RZ
        
        # Test multimeter plane if required
        if test_plane:
            self._test_multimeter_plane(probe_x, probe_y)
        
        # Move to probe position
        self.robot_controller.move_to_cartesian_position(3, 30.0, safe_position)
        self.robot_controller.move_linear(3, 30.0, check_position)
        
        # Monitor probe insertion with pressure feedback
        pressure_monitor = PressureMonitor(self.microcontroller_comm)
        insertion_result = pressure_monitor.monitor_probe_insertion(pressure_threshold)
        
        if insertion_result != 1:
            return insertion_result, "Probe insertion failed", ""
        
        return 1, "", ""
    
    def _test_multimeter_plane(self, probe_x: float, probe_y: float):
        """Test multimeter plane height for accurate positioning."""
        global multimeter_plane_z
        
        # Move to test position
        test_position = [probe_x + 8.0, probe_y, SAFE_HEIGHT_Z] + ROBOT_RX_RY_RZ
        self.robot_controller.move_to_cartesian_position(3, 30.0, test_position)
        
        # Lower to test height
        test_position[2] = -125.000
        self.robot_controller.move_linear(3, 30.0, test_position)
        
        # Start pressure monitoring
        pressure_monitor = PressureMonitor(self.microcontroller_comm)
        multimeter_plane_z = pressure_monitor.find_multimeter_plane()
        
        # Return to safe height
        current_joint_angles, current_position = self.robot_controller.get_current_position()
        current_position[2] = SAFE_HEIGHT_Z
        self.robot_controller.move_linear(3, 30.0, current_position)


class MicrocontrollerCommunication:
    """
    Handle communication with microcontroller for gripper and sensors.
    
    This class manages serial communication with the microcontroller
    that controls the gripper, pressure sensors, and turntable.
    """
    
    def __init__(self):
        """Initialize microcontroller communication."""
        self.serial_connection = None
        self.selected_port = None  # track selected COM port
        self._rpc = None
        self._mode = "serial"
        # Toggle RPC mode via environment; default to serial
        if os.environ.get("PRESSURE_VIA_RPC", "0") == "1":
            self._mode = "rpc"
            host = resolve_robot_host(ROBOT_IP_ADDRESS)
            rpc_port = int(os.environ.get("PRESSURE_RPC_PORT", "20003"))
            try:
                self._rpc = xmlrpc.client.ServerProxy(f"http://{host}:{rpc_port}/RPC2", allow_none=True)
                print(f"Microcontroller RPC mode via {host}:{rpc_port}")
            except Exception as e:
                print(f"Failed to initialize microcontroller RPC client: {e}")
                self._rpc = None
                self._mode = "serial"
        if self._mode == "serial":
            self._initialize_serial_connection()
    
    def _resolve_serial_port(self) -> Optional[str]:
        """Resolve the serial port to use with environment override and auto-discovery.
        Returns a port string like 'COM3' or None if not found.
        """
        # env override takes precedence
        env_port = os.environ.get("MICROCONTROLLER_PORT") or os.environ.get("SERIAL_PORT")
        configured = env_port or SERIAL_PORT
        available = list(list_ports.comports())
        available_names = {p.device for p in available}

        # if configured exists and available, use it
        if configured and configured in available_names:
            return configured

        # try simple auto-discovery
        if not available:
            return None

        # If only one port, choose it
        if len(available) == 1:
            return available[0].device

        # Prefer common USB-UART adapters by description
        preferred_keywords = ["USB", "CH340", "CP210", "FTDI", "Arduino", "Silicon Labs", "Prolific"]
        for p in available:
            desc = (p.description or "") + " " + (p.manufacturer or "")
            if any(k in desc for k in preferred_keywords):
                return p.device

        # Fallback: None to force user configuration
        return None

    def _initialize_serial_connection(self):
        """Initialize serial connection to microcontroller."""
        try:
            port = self._resolve_serial_port()
            self.serial_connection = serial.Serial()
            self.serial_connection.baudrate = SERIAL_BAUDRATE
            self.serial_connection.bytesize = 8
            self.serial_connection.parity = 'N'
            self.serial_connection.stopbits = 1
            self.serial_connection.timeout = SERIAL_TIMEOUT
            if port:
                self.serial_connection.port = port
                self.selected_port = port
                print(f"Microcontroller communication initialized on {port}")
            else:
                # keep unassigned, print guidance
                self.selected_port = None
                ports_list = ", ".join(sorted({p.device for p in list_ports.comports()})) or "<none>"
                print(
                    "Microcontroller port unresolved. Set MICROCONTROLLER_PORT env var or update system_config.SERIAL_PORT. "
                    f"Detected ports: {ports_list}"
                )
        except Exception as e:
            print(f"Failed to initialize microcontroller communication: {e}")
    
    def _ensure_open(self) -> bool:
        """Ensure the serial port is assigned and open; return True if ready."""
        try:
            if self.serial_connection is None:
                return False
            if not getattr(self.serial_connection, "port", None):
                # retry resolve in case device plugged in later
                port = self._resolve_serial_port()
                if port:
                    self.serial_connection.port = port
                    self.selected_port = port
                    print(f"Microcontroller port set to {port}")
                else:
                    return False
            if not self.serial_connection.is_open:
                self.serial_connection.open()
            return True
        except Exception as e:
            print(f"Serial open failed: {e}")
            return False
    
    def send_gripper_command(self, close_gripper: bool) -> int:
        """
        Send gripper open/close command.
        
        Args:
            close_gripper: True to close gripper, False to open
            
        Returns:
            Status code (1 for success, negative for error)
        """
        # RPC mode path
        if self._mode == "rpc" and self._rpc is not None:
            try:
                result = self._rpc.Gripper(bool(close_gripper))  # type: ignore[attr-defined]
                return int(result)
            except Exception as e:
                print(f"Gripper RPC failed: {e}")
                return -3
        
        # Serial mode path
        try:
            if not self._ensure_open():
                print("Gripper command failed: serial port unavailable")
                return -3
            self.serial_connection.reset_input_buffer()
            self.serial_connection.reset_output_buffer()
            
            command = CMD_GRIP_CLOSE if close_gripper else CMD_GRIP_OPEN
            timeout_start = time.time()
            
            self.serial_connection.write(bytearray(command))
            
            # Wait for response
            while (time.time() - timeout_start) < 1:
                if self.serial_connection.in_waiting > 0:
                    _ = self.serial_connection.readline()
                    break
            
            self.serial_connection.close()
            return 1
            
        except Exception as e:
            print(f"Gripper command failed: {e}")
            try:
                if self.serial_connection and self.serial_connection.is_open:
                    self.serial_connection.close()
            except Exception:
                pass
            return -3
    
    def read_pressure_value(self) -> float:
        """
        Read current pressure value from sensor.
        
        Returns:
            Pressure value in appropriate units, or -3 for communication error
        """
        # RPC mode path
        if self._mode == "rpc" and self._rpc is not None:
            try:
                val = float(self._rpc.ReadPressure())  # type: ignore[attr-defined]
                # if NaN from middleman, treat as error
                if val != val:
                    return -3
                return round(val, 2)
            except Exception as e:
                print(f"Pressure RPC failed: {e}")
                return -3
        
        # Serial mode path
        try:
            if not self._ensure_open():
                print("Pressure reading failed: serial port unavailable")
                return -3
            self.serial_connection.reset_input_buffer()
            self.serial_connection.reset_output_buffer()
            
            timeout_start = time.time()
            self.serial_connection.write(bytearray(CMD_REQUEST_PRESSURE))
            
            pressure_reading = ''
            while (time.time() - timeout_start) < 1:
                if self.serial_connection.in_waiting > 0:
                    response = self.serial_connection.readline()
                    try:
                        pressure_reading = response.decode(encoding='utf-8').strip()
                    except Exception:
                        pressure_reading = ''
                    break
            
            self.serial_connection.close()
            
            if pressure_reading == "":
                return -3
            
            pressure_value = float(pressure_reading)
            return round(pressure_value, 2)
            
        except Exception as e:
            print(f"Pressure reading failed: {e}")
            try:
                if self.serial_connection and self.serial_connection.is_open:
                    self.serial_connection.close()
            except Exception:
                pass
            return -3
    
    def send_turntable_rotation(self, rotation_steps: int):
        """
        Send turntable rotation command.
        
        Args:
            rotation_steps: Number of steps to rotate (0 for no rotation)
        """
        if rotation_steps == 0:
            time.sleep(2)
            return
        
        # No RPC endpoint for turntable provided; keep serial-only
        try:
            command = CMD_TURNTABLE_ROTATE.copy()
            command[6] = rotation_steps
            
            if not self._ensure_open():
                print("Turntable rotation failed: serial port unavailable")
                return
            self.serial_connection.reset_input_buffer()
            self.serial_connection.reset_output_buff



