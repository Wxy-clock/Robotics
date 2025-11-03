#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
movement_command_parser.py

Parses a plain-text command script and invokes robot control functions.

Format:
- One command per line
- Lines starting with '#' are comments and ignored
- Each line: "func_name arg1 arg2 ..."
- Arguments are whitespace-separated. Numbers are auto-parsed; "true"/"false" -> bool

Supported functions include module-level functions and methods from:
- RobotController
- ProbeHandler
- MicrocontrollerCommunication
- PressureMonitor

Special handling for functions that require list arguments (positions / joints):
- move_to_joint_position: expects 3 args -> tool(int) velocity(float) joints(6 floats)
- move_to_cartesian_position: expects 3 args -> tool(int) velocity(float) pose(6 floats)
- move_linear: expects 3(+1) -> tool(int) velocity(float) pose(6 floats) [blend_radius(float, optional)]

Example file lines:
  test_communication_connection
  move_to_joint_position 3 20 0 -45 30 0 60 0
  move_to_cartesian_position 3 30 100 200 300 180 0 -90
  move_linear 3 15 120 210 280 180 0 -90 5.0
  set_tool_coordinate_system 3
  get_current_position
  insert_probe 1 FlUKE true
  send_gripper_command true
  send_turntable_rotation 2
  send_voice_alert
  monitor_probe_insertion 0.03
  find_multimeter_plane

Return codes:
  0: all commands executed (success or best-effort)
  >0: number of command failures
"""
from __future__ import annotations

import os
import sys
import time
import threading
from typing import List, Any

# Avoid auto-initialization on import; let this script control connections
os.environ.setdefault('ROBOT_SKIP_AUTO_INIT', '1')

from robot_controller import (
    RobotController,
    ProbeHandler,
    MicrocontrollerCommunication,
    PressureMonitor,
    test_communication_connection,
    initialize_system,
)

# Import safety validation helpers and runtime monitor toggle
from movement_safety_config import (
    validate_joint_move,
    validate_cartesian_move,
    SafetyConfigError,
    ENABLE_RUNTIME_COORD_MONITOR,
)


def _parse_token(tok: str):
    t = tok.strip()
    if t.lower() in ("true", "false"):
        return t.lower() == "true"
    try:
        if t.startswith("0x") or t.startswith("-0x"):
            return int(t, 16)
        i = int(t)
        return i
    except ValueError:
        pass
    try:
        f = float(t)
        return f
    except ValueError:
        pass
    return t


def _bundle_six(values: List[Any]) -> List[float]:
    if len(values) < 6:
        raise ValueError(f"expected 6 numbers, got {len(values)}")
    try:
        return [float(values[i]) for i in range(6)]
    except Exception as e:
        raise ValueError(f"failed to parse 6-number list: {e}")


class _RuntimeCoordMonitor:
    """Background 5 Hz coordinate safety checker.

    Uses validate_cartesian_move. On violation, engages rc.stop_robot_movement()
    and records the violation to be consumed by the main thread.
    """

    def __init__(self, rc_provider, tool_provider, *, hz: float = 5.0):
        self._rc_provider = rc_provider
        self._tool_provider = tool_provider
        self._period = 1.0 / max(0.1, hz)
        self._running = threading.Event()
        self._thread: threading.Thread | None = None
        self._violation = threading.Event()
        self._violation_msg: str | None = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._running.set()
        self._thread = threading.Thread(target=self._run, name="CoordSafetyMonitor", daemon=True)
        self._thread.start()

    def stop(self):
        self._running.clear()
        t = self._thread
        if t and t.is_alive():
            t.join(timeout=1.5)

    def has_violation(self) -> bool:
        return self._violation.is_set()

    def consume_violation(self) -> str | None:
        if not self._violation.is_set():
            return None
        msg = self._violation_msg
        self._violation.clear()
        self._violation_msg = None
        return msg

    def _run(self):
        if not ENABLE_RUNTIME_COORD_MONITOR:
            return
        while self._running.is_set():
            try:
                rc: RobotController | None = self._rc_provider()
                if rc is None or not rc.is_connected:
                    time.sleep(self._period)
                    continue
                # Get current pose
                _, cart = rc.get_current_position()
                tool = self._tool_provider() or "default"
                # Validate against configured limits
                validate_cartesian_move(tool, cart)
            except SafetyConfigError as e:
                # Treat config error as a safety violation: stop and signal
                try:
                    rc = self._rc_provider()
                    if rc and rc.is_connected:
                        print(f"[Safety] Coordinate limits config error: {e}. Engaging remote stop...")
                        rc.stop_robot_movement()
                except Exception:
                    pass
                self._violation_msg = f"Config error: {e}"
                self._violation.set()
            except ValueError as e:
                # Out of bounds -> engage stop and record
                try:
                    rc = self._rc_provider()
                    if rc and rc.is_connected:
                        print(f"[Safety] Coordinate violation detected: {e}. Engaging remote stop...")
                        rc.stop_robot_movement()
                except Exception:
                    pass
                self._violation_msg = str(e)
                self._violation.set()
            except Exception:
                # Any other exception: ignore this tick
                pass
            finally:
                time.sleep(self._period)


def parse_and_execute_commands(file_path: str, *, echo: bool = True) -> int:
    """
    Parse the command file and execute each command sequentially.

    Args:
        file_path: Path to the .txt file containing commands
        echo: Whether to print each command and result

    Returns:
        int: Number of command failures encountered
    """
    failures = 0

    # Singleton controller/aux components
    rc: RobotController | None = None
    micro: MicrocontrollerCommunication | None = None
    probe: ProbeHandler | None = None
    monitor: PressureMonitor | None = None

    # Track the currently active tool for runtime monitor validation
    active_tool: int | str | None = "default"

    def ensure_rc():
        nonlocal rc
        if rc is None:
            rc = RobotController()
        return rc

    def ensure_micro():
        nonlocal micro
        if micro is None:
            micro = MicrocontrollerCommunication()
        return micro

    def ensure_probe():
        nonlocal probe
        if probe is None:
            probe = ProbeHandler(ensure_rc())
        return probe

    def ensure_monitor():
        nonlocal monitor
        if monitor is None:
            monitor = PressureMonitor(ensure_micro())
        return monitor

    def get_active_tool():
        return active_tool

    def log(msg: str):
        if echo:
            print(msg)

    # Start runtime coordinate monitor
    coord_monitor = _RuntimeCoordMonitor(ensure_rc, get_active_tool)
    if ENABLE_RUNTIME_COORD_MONITOR:
        coord_monitor.start()

    # Dispatch table for simple calls
    def call_module(fname: str, args: List[Any]) -> bool:
        if fname == "test_communication_connection":
            _ = test_communication_connection()
            return True
        if fname == "initialize_system":
            initialize_system()
            return True
        return False

    def call_rc(fname: str, args: List[Any]) -> bool:
        nonlocal active_tool
        r = ensure_rc()
        if not hasattr(r, fname):
            return False
        try:
            if fname == "set_tool_coordinate_system":
                # Update active tool before calling
                active_tool = int(args[0]) if args else active_tool
                method = getattr(r, fname)
                method(*args)
                return True
            if fname == "move_to_joint_position":
                tool = int(args[0]); vel = float(args[1]); joints = _bundle_six(args[2:8])
                active_tool = tool
                # Safety validation before executing the movement
                validate_joint_move(tool, joints)
                # Additionally validate the resulting Cartesian pose via forward kinematics
                try:
                    cart = r.robot.GetForwardKin(joints)[1]
                    validate_cartesian_move(tool, cart)
                except Exception:
                    # If FK or validation fails, stop and re-raise below
                    raise
                getattr(r, fname)(tool, vel, joints)
                return True
            if fname == "move_to_cartesian_position":
                tool = int(args[0]); vel = float(args[1]); pose = _bundle_six(args[2:8])
                active_tool = tool
                # Safety validation before executing the movement
                validate_cartesian_move(tool, pose)
                getattr(r, fname)(tool, vel, pose)
                return True
            if fname == "move_linear":
                tool = int(args[0]); vel = float(args[1]); pose = _bundle_six(args[2:8])
                active_tool = tool
                # Safety validation before executing the movement
                validate_cartesian_move(tool, pose)
                br = float(args[8]) if len(args) >= 9 else -1.0
                getattr(r, fname)(tool, vel, pose, br)
                return True
            method = getattr(r, fname)
            result = method(*args)
            if fname == "get_current_position":
                log(f"get_current_position -> {result}")
            return True
        except (SafetyConfigError, ValueError) as e:
            # On illegal commands or validation failures: stop and raise
            try:
                if r and r.is_connected:
                    print(f"[Safety] Movement validation failed: {e}. Engaging remote stop...")
                    r.stop_robot_movement()
            except Exception:
                pass
            raise
        except Exception as e:
            log(f"ERROR calling RobotController.{fname}: {e}")
            return True

    def call_probe(fname: str, args: List[Any]) -> bool:
        p = ensure_probe()
        if not hasattr(p, fname):
            return False
        try:
            result = getattr(p, fname)(*args)
            log(f"ProbeHandler.{fname} -> {result}")
            return True
        except Exception as e:
            log(f"ERROR calling ProbeHandler.{fname}: {e}")
            return True

    def call_micro(fname: str, args: List[Any]) -> bool:
        m = ensure_micro()
        if not hasattr(m, fname):
            return False
        try:
            result = getattr(m, fname)(*args)
            log(f"MicrocontrollerCommunication.{fname} -> {result}")
            return True
        except Exception as e:
            log(f"ERROR calling MicrocontrollerCommunication.{fname}: {e}")
            return True

    def call_monitor(fname: str, args: List[Any]) -> bool:
        mon = ensure_monitor()
        if not hasattr(mon, fname):
            return False
        try:
            result = getattr(mon, fname)(*args)
            log(f"PressureMonitor.{fname} -> {result}")
            return True
        except Exception as e:
            log(f"ERROR calling PressureMonitor.{fname}: {e}")
            return True

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for lineno, raw in enumerate(f, start=1):
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                # allow trailing comments
                if "#" in line:
                    line = line.split("#", 1)[0].strip()
                if not line:
                    continue

                parts = line.split()
                fname, arg_tokens = parts[0], parts[1:]
                args = [_parse_token(t) for t in arg_tokens]
                log(f"[{lineno}] {fname} {arg_tokens}")

                handled = False

                # Try each domain in order
                if call_module(fname, args):
                    handled = True
                elif call_rc(fname, args):
                    handled = True
                elif call_probe(fname, args):
                    handled = True
                elif call_micro(fname, args):
                    handled = True
                elif call_monitor(fname, args):
                    handled = True

                if not handled:
                    log(f"ERROR: Unknown command '{fname}' at line {lineno}")
                    failures += 1
                    continue

                # If runtime monitor engaged a stop due to violation, raise
                vio = coord_monitor.consume_violation()
                if vio:
                    raise RuntimeError(f"Coordinate safety violation: {vio}")

                # Heuristic: consider failure if an error was printed in call handlers
                # We cannot detect perfectly; increment failures if rc is not connected and a motion was requested
                if fname.startswith("move_") and (rc is None or not rc.is_connected):
                    failures += 1
    finally:
        # Ensure monitor is stopped
        coord_monitor.stop()

    return failures


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: movement_command_parser.py <commands.txt>")
        sys.exit(2)
    failures = parse_and_execute_commands(sys.argv[1])
    sys.exit(0 if failures == 0 else 1)
