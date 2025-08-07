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
- Database operations for position storage

Classes:
    RobotController: Main robot control interface
    ProbeHandler: Probe manipulation operations  
    TurntableController: Turntable rotation management
    PressureMonitor: Pressure sensing and feedback
    DatabaseManager: Database operations for robot data
"""

import time
import copy
import threading
import serial
import pymysql
from datetime import datetime
from typing import List, Tuple, Optional, Union

# Third-party imports
import numpy as np

# Local imports
from system_config import *
import Robot
from image_processing import capture_image, recognize_qr_and_lcd

# Global robot and database connections
robot_connection = None
database_connection = None
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
        self._initialize_robot_connection()
        self._load_robot_positions()
    
    def _initialize_robot_connection(self):
        """Initialize connection to robot controller."""
        try:
            self.robot = Robot.RPC(ROBOT_IP_ADDRESS)
            self.is_connected = True
            print("Robot connection established successfully")
        except Exception as e:
            print(f"Failed to connect to robot: {e}")
            self.is_connected = False
    
    def _load_robot_positions(self):
        """Load robot positions from database."""
        global fixture_positions
        
        if not database_connection:
            return
        
        try:
            cursor = database_connection.cursor()
            cursor.execute("SELECT d_j1,d_j2,d_j3,d_j4,d_begin,d_mea FROM jiajv_info WHERE id = 1")
            database_connection.commit()
            result = cursor.fetchone()
            
            if result:
                # Parse fixture positions
                fixture_1_coords = list(map(float, result[0].split('&')))
                fixture_2_coords = list(map(float, result[1].split('&')))
                fixture_3_coords = list(map(float, result[2].split('&')))
                fixture_4_coords = list(map(float, result[3].split('&')))
                start_coords = list(map(float, result[4].split('&')))
                measurement_coords = list(map(float, result[5].split('&')))
                
                # Set fixture positions
                fixture_positions['fixture_1_safe'] = fixture_1_coords[:2] + [SAFE_HEIGHT_Z] + ROBOT_RX_RY_RZ
                fixture_positions['fixture_1_check'] = fixture_1_coords[:2] + [-130.000] + ROBOT_RX_RY_RZ
                fixture_positions['fixture_1_insert'] = fixture_1_coords + ROBOT_RX_RY_RZ
                
                fixture_positions['fixture_2_safe'] = fixture_2_coords[:2] + [SAFE_HEIGHT_Z] + ROBOT_RX_RY_RZ
                fixture_positions['fixture_2_check'] = fixture_2_coords[:2] + [-130.000] + ROBOT_RX_RY_RZ
                fixture_positions['fixture_2_insert'] = fixture_2_coords + ROBOT_RX_RY_RZ
                
                fixture_positions['fixture_3_safe'] = fixture_3_coords[:2] + [SAFE_HEIGHT_Z] + ROBOT_RX_RY_RZ
                fixture_positions['fixture_3_check'] = fixture_3_coords[:2] + [-130.000] + ROBOT_RX_RY_RZ
                fixture_positions['fixture_3_insert'] = fixture_3_coords + ROBOT_RX_RY_RZ
                
                fixture_positions['fixture_4_safe'] = fixture_4_coords[:2] + [SAFE_HEIGHT_Z] + ROBOT_RX_RY_RZ
                fixture_positions['fixture_4_check'] = fixture_4_coords[:2] + [-110.000] + ROBOT_RX_RY_RZ
                fixture_positions['fixture_4_insert'] = fixture_4_coords + ROBOT_RX_RY_RZ
                
                fixture_positions['start_position'] = start_coords
                fixture_positions['measurement_position'] = measurement_coords
                
        except Exception as e:
            print(f"Error loading robot positions: {e}")
    
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
        
        # Get probe positions from database
        cursor = database_connection.cursor()
        sql = "SELECT k1_pos,k2_pos,k3_pos,k4_pos FROM wyb_info WHERE type = %s"
        cursor.execute(sql, (multimeter_type,))
        database_connection.commit()
        
        result = cursor.fetchone()
        if not result:
            return -6, "Error: Multimeter type not found in database", ""
        
        # Parse probe positions
        probe_coords = []
        for i in range(4):
            x, y = map(float, result[i].split('&'))
            probe_coords.append([x, y])
        
        probe_positions_x = [coord[0] for coord in probe_coords]
        probe_positions_y = [coord[1] for coord in probe_coords]
        
        # Validate timestamp if required
        if require_timestamp_check:
            # Implementation would check if positions were recently updated
            pass
        
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
            # Move to fixture 1 and grab probe
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
        safe_pos = fixture_positions[f'fixture_{fixture_number}_safe']
        self.robot_controller.move_to_cartesian_position(3, 80.0, safe_pos)
        
        # Move to check position
        check_pos = fixture_positions[f'fixture_{fixture_number}_check']
        self.robot_controller.move_linear(3, 50.0, check_pos)
        
        time.sleep(1)
        
        # Move to insert position
        insert_pos = fixture_positions[f'fixture_{fixture_number}_insert']
        self.robot_controller.move_linear(3, 5.0, insert_pos)
        
        time.sleep(1)
        
        # Close gripper
        self.microcontroller_comm.send_gripper_command(True)
        time.sleep(1)
        
        # Update database
        cursor = database_connection.cursor()
        sql = f"UPDATE jiajv_info SET jia{fixture_number} = 0 WHERE id = 1"
        cursor.execute(sql)
        database_connection.commit()
        
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
        
        # Record successful insertion
        self._record_probe_insertion(probe_field, position_field)
        
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
    
    def _record_probe_insertion(self, probe_field: str, position_field: str):
        """Record probe insertion in database."""
        cursor = database_connection.cursor()
        
        # Update probe status
        sql = f"UPDATE jiajv_info SET {probe_field} = %s WHERE id = %s"
        cursor.execute(sql, (1, 1))
        database_connection.commit()
        
        # Record position
        current_joint_angles, current_position = self.robot_controller.get_current_position()
        position_str = f"{current_position[0]:.3f}&{current_position[1]:.3f}&{current_position[2]:.3f}"
        
        sql = f"UPDATE jiajv_info SET {position_field} = %s WHERE id = %s"
        cursor.execute(sql, (position_str, 1))
        database_connection.commit()
        
        # Move to safe position
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
        self._initialize_serial_connection()
    
    def _initialize_serial_connection(self):
        """Initialize serial connection to microcontroller."""
        try:
            self.serial_connection = serial.Serial()
            self.serial_connection.baudrate = SERIAL_BAUDRATE
            self.serial_connection.bytesize = 8
            self.serial_connection.parity = 'N'
            self.serial_connection.stopbits = 1
            self.serial_connection.timeout = SERIAL_TIMEOUT
            self.serial_connection.port = SERIAL_PORT
            print("Microcontroller communication initialized")
        except Exception as e:
            print(f"Failed to initialize microcontroller communication: {e}")
            initialization_status = -1
    
    def send_gripper_command(self, close_gripper: bool) -> int:
        """
        Send gripper open/close command.
        
        Args:
            close_gripper: True to close gripper, False to open
            
        Returns:
            Status code (1 for success, negative for error)
        """
        try:
            self.serial_connection.open()
            self.serial_connection.flushInput()
            self.serial_connection.flushOutput()
            
            command = CMD_GRIP_CLOSE if close_gripper else CMD_GRIP_OPEN
            timeout_start = time.time()
            
            self.serial_connection.write(command)
            
            # Wait for response
            while (time.time() - timeout_start) < 1:
                if self.serial_connection.in_waiting > 0:
                    response = self.serial_connection.readline()
                    break
            
            self.serial_connection.close()
            return 1
            
        except Exception as e:
            print(f"Gripper command failed: {e}")
            return -3
    
    def read_pressure_value(self) -> float:
        """
        Read current pressure value from sensor.
        
        Returns:
            Pressure value in appropriate units, or -3 for communication error
        """
        try:
            self.serial_connection.open()
            self.serial_connection.flushInput()
            self.serial_connection.flushOutput()
            
            timeout_start = time.time()
            self.serial_connection.write(CMD_REQUEST_PRESSURE)
            
            pressure_reading = ''
            while (time.time() - timeout_start) < 1:
                if self.serial_connection.in_waiting > 0:
                    response = self.serial_connection.readline()
                    pressure_reading = response.decode(encoding='utf-8')
                    break
            
            self.serial_connection.close()
            
            if pressure_reading == "":
                return -3
            
            pressure_value = float(pressure_reading)
            return round(pressure_value, 2)
            
        except Exception as e:
            print(f"Pressure reading failed: {e}")
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
        
        try:
            command = CMD_TURNTABLE_ROTATE.copy()
            command[6] = rotation_steps
            
            self.serial_connection.open()
            self.serial_connection.flushInput()
            self.serial_connection.flushOutput()
            
            self.serial_connection.write(bytearray(command))
            self.serial_connection.readline()
            self.serial_connection.close()
            
        except Exception as e:
            print(f"Turntable rotation failed: {e}")
    
    def send_voice_alert(self):
        """Send voice alert command."""
        try:
            self.serial_connection.open()
            self.serial_connection.flushInput()
            self.serial_connection.flushOutput()
            
            self.serial_connection.write(CMD_VOICE_ALERT)
            self.serial_connection.close()
            
        except Exception as e:
            print(f"Voice alert failed: {e}")


class PressureMonitor:
    """
    Monitor pressure sensors for feedback during operations.
    
    This class provides pressure monitoring capabilities for
    precise probe insertion and multimeter plane detection.
    """
    
    def __init__(self, microcontroller_comm: MicrocontrollerCommunication):
        """
        Initialize pressure monitor.
        
        Args:
            microcontroller_comm: Microcontroller communication interface
        """
        self.microcontroller_comm = microcontroller_comm
    
    def monitor_probe_insertion(self, pressure_threshold: float) -> int:
        """
        Monitor probe insertion using pressure feedback.
        
        Args:
            pressure_threshold: Pressure threshold for insertion detection
            
        Returns:
            Status code (1 for success, negative for error)
        """
        global io_operation_interrupted
        
        # Clear pressure reading
        max_pressure = self.microcontroller_comm.read_pressure_value()
        
        while True:
            max_pressure = self.microcontroller_comm.read_pressure_value()
            
            if max_pressure > pressure_threshold:
                # Probe successfully inserted
                robot_connection.ProgramStop()
                robot_connection.WaitMs(2000)
                max_pressure = self.microcontroller_comm.read_pressure_value()
                break
            elif max_pressure == -3:
                # Communication error
                robot_connection.ProgramStop()
                robot_connection.WaitMs(2000)
                io_operation_interrupted = 1
                break
        
        return 1 if max_pressure > pressure_threshold else -3
    
    def find_multimeter_plane(self) -> float:
        """
        Find multimeter plane height using pressure feedback.
        
        Returns:
            Z-coordinate of multimeter plane
        """
        global io_operation_interrupted
        
        max_pressure = self.microcontroller_comm.read_pressure_value()
        
        while True:
            max_pressure = self.microcontroller_comm.read_pressure_value()
            
            if max_pressure > 0.03:
                current_position = robot_connection.GetActualTCPPose(1)[1]
                plane_z = current_position[2]
                
                robot_connection.ProgramStop()
                robot_connection.WaitMs(2000)
                max_pressure = self.microcontroller_comm.read_pressure_value()
                
                return plane_z
            elif max_pressure == -3:
                robot_connection.ProgramStop()
                robot_connection.WaitMs(2000)
                io_operation_interrupted = 1
                break
        
        return 0.0


def test_communication_connection() -> int:
    """
    Test communication with all system components.
    
    Returns:
        1 for success, -1 for failure
    """
    global initialization_status, robot_connection, database_connection
    
    initialization_status = 1
    
    # Test robot communication
    try:
        robot_connection = Robot.RPC(ROBOT_IP_ADDRESS)
        robot_connection.GetActualTCPPose(1)[1]
        print('Robot communication successful')
    except Exception as e:
        print(f'Robot communication failed: {e}')
        initialization_status = -1
    
    # Test microcontroller communication
    microcontroller_comm = MicrocontrollerCommunication()
    
    # Test database communication
    try:
        database_connection = pymysql.connect(
            host=DATABASE_HOST,
            port=DATABASE_PORT,
            user=DATABASE_USER,
            password=DATABASE_PASSWORD,
            database=DATABASE_NAME
        )
        print('Database communication successful')
    except Exception as e:
        print(f'Database connection failed: {e}')
        initialization_status = -1
    
    # Test camera communication
    try:
        capture_image.capture_photo('test_connect')
        print('Camera communication successful')
    except Exception as e:
        print(f'Camera communication failed: {e}')
        initialization_status = -1
    
    # Test pressure sensor
    try:
        pressure_value = microcontroller_comm.read_pressure_value()
        if pressure_value != 0.01:
            initialization_status = -1
            print('Pressure sensor working status error')
        else:
            print('Pressure sensor working correctly')
    except Exception as e:
        print(f'Pressure sensor communication failed: {e}')
        initialization_status = -1
    
    # Test gripper
    try:
        microcontroller_comm.send_gripper_command(True)
        time.sleep(1)
        microcontroller_comm.send_gripper_command(False)
        print("Gripper communication successful")
    except Exception as e:
        print(f'Gripper communication failed: {e}')
        initialization_status = -1
    
    return initialization_status


# Initialize global connections
def initialize_system():
    """Initialize all system connections."""
    global robot_connection, database_connection
    
    try:
        robot_connection = Robot.RPC(ROBOT_IP_ADDRESS)
        database_connection = pymysql.connect(
            host=DATABASE_HOST,
            port=DATABASE_PORT,
            user=DATABASE_USER,
            password=DATABASE_PASSWORD,
            database=DATABASE_NAME
        )
        print("System initialization completed")
    except Exception as e:
        print(f"System initialization failed: {e}")


# Initialize on module import
initialize_system()