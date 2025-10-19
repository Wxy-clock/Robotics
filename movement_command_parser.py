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

    def log(msg: str):
        if echo:
            print(msg)

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
        r = ensure_rc()
        if not hasattr(r, fname):
            return False
        try:
            if fname == "move_to_joint_position":
                tool = int(args[0]); vel = float(args[1]); joints = _bundle_six(args[2:8])
                getattr(r, fname)(tool, vel, joints)
                return True
            if fname == "move_to_cartesian_position":
                tool = int(args[0]); vel = float(args[1]); pose = _bundle_six(args[2:8])
                getattr(r, fname)(tool, vel, pose)
                return True
            if fname == "move_linear":
                tool = int(args[0]); vel = float(args[1]); pose = _bundle_six(args[2:8])
                br = float(args[8]) if len(args) >= 9 else -1.0
                getattr(r, fname)(tool, vel, pose, br)
                return True
            method = getattr(r, fname)
            result = method(*args)
            if fname == "get_current_position":
                log(f"get_current_position -> {result}")
            return True
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

            # Heuristic: consider failure if an error was printed in call handlers
            # We cannot detect perfectly; increment failures if rc is not connected and a motion was requested
            if fname.startswith("move_") and (rc is None or not rc.is_connected):
                failures += 1

    return failures


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: movement_command_parser.py <commands.txt>")
        sys.exit(2)
    failures = parse_and_execute_commands(sys.argv[1])
    sys.exit(0 if failures == 0 else 1)
