#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
movement_test.py

Simple CLI to command a joint-space move on the robot using RobotController.

Usage examples:
  python movement_test.py 0  -45  30  0  60  0
  python movement_test.py 10 20 30 40 50 60 --tool 3 --velocity 30

Notes:
- Angles are in degrees.
- --tool is the tool coordinate system number (default: 3).
- --velocity is percentage speed (default: 20.0).
- Requires network access to the robot controller. Proxy settings are
  taken from system_config/proxy_connection if enabled.
"""

import sys
import argparse
import time
import threading
from datetime import datetime

from robot_controller import RobotController, MicrocontrollerCommunication
from proxy_connection import resolve_robot_host, is_proxy_enabled, get_proxy_endpoint
from system_config import ROBOT_IP_ADDRESS

# Pressure-based E-Stop configuration
PRESSURE_ESTOP_THRESHOLD_N: float = 5.0  # Trigger E-stop if pressure exceeds this (N)
PRESSURE_POLL_HZ: float = 20.0           # Polling frequency for pressure monitoring
PRESSURE_POLL_INTERVAL: float = 1.0 / PRESSURE_POLL_HZ


def parse_args(argv):
    p = argparse.ArgumentParser(description="Issue a MoveJ with 6 joint angles (deg)")
    p.add_argument("j1", type=float, help="Joint 1 angle (deg)")
    p.add_argument("j2", type=float, help="Joint 2 angle (deg)")
    p.add_argument("j3", type=float, help="Joint 3 angle (deg)")
    p.add_argument("j4", type=float, help="Joint 4 angle (deg)")
    p.add_argument("j5", type=float, help="Joint 5 angle (deg)")
    p.add_argument("j6", type=float, help="Joint 6 angle (deg)")
    p.add_argument("--tool", "-t", type=int, default=3, help="Tool coordinate system number (default: 3)")
    p.add_argument("--velocity", "-v", type=float, default=20.0, help="Velocity percentage (default: 20.0)")
    p.add_argument("--sleep", type=float, default=0.5, help="Post-move sleep seconds before reading pose")
    return p.parse_args(argv)


def movement_main(argv=None):
    # Allow both parsed argv (list of strings) or direct numeric list
    if argv and len(argv) == 6:
        try:
            floats = [float(x) for x in argv]
            # Convert to parsed args by building an argv list
            argv = [str(v) for v in floats]
        except Exception:
            # fall through to argparse if includes flags
            pass

    args = parse_args(argv or sys.argv[1:])

    host = resolve_robot_host(ROBOT_IP_ADDRESS)
    print("=== Movement Test ===")
    print(f"Target host: {host} (proxy={'ON' if is_proxy_enabled() else 'OFF'}; endpoint={get_proxy_endpoint() if is_proxy_enabled() else 'n/a'})")
    print(f"Tool: {args.tool}, Velocity: {args.velocity}%")
    joint_angles = [args.j1, args.j2, args.j3, args.j4, args.j5, args.j6]
    print(f"Joint angles (deg): {joint_angles}")
    print(f"E-Stop: threshold={PRESSURE_ESTOP_THRESHOLD_N} N, poll={PRESSURE_POLL_HZ} Hz")

    rc = RobotController()
    if not getattr(rc, "is_connected", False):
        print("ERROR: Robot not connected.")
        return 2

    # Initialize microcontroller for pressure sensing
    mc = MicrocontrollerCommunication()

    # Shared state for E-stop
    stop_event = threading.Event()
    estop_info = {"triggered": False, "pressure": None, "timestamp": None}

    def _pressure_monitor_loop():
        # drain first read (optional) to stabilize
        try:
            _ = mc.read_pressure_value()
        except Exception:
            pass
        while not stop_event.is_set():
            try:
                val = mc.read_pressure_value()
            except Exception:
                val = None
            if isinstance(val, (int, float)) and val != -3 and val is not None:
                if val > PRESSURE_ESTOP_THRESHOLD_N:
                    # Trigger robot stop immediately
                    estop_info["triggered"] = True
                    estop_info["pressure"] = float(val)
                    estop_info["timestamp"] = datetime.now().strftime("%H:%M:%S")
                    try:
                        rc.stop_robot_movement()
                    except Exception:
                        pass
                    # remain running a little longer, then exit
                    break
            # Sleep until next poll
            time.sleep(PRESSURE_POLL_INTERVAL)

    monitor_thread = threading.Thread(target=_pressure_monitor_loop, name="pressure-monitor", daemon=True)
    monitor_thread.start()

    try:
        # Execute MoveJ
        rc.move_to_joint_position(args.tool, args.velocity, joint_angles)
        print("MoveJ command issued. Waiting...")
        time.sleep(args.sleep)

        # Read back current pose
        joints, pose = rc.get_current_position()
        print("Current joints (deg):", [round(v, 3) for v in joints])
        print("Current TCP pose:", [round(v, 3) for v in pose])

        if estop_info["triggered"]:
            print(f"E-STOP TRIGGERED at {estop_info['timestamp']} with pressure={estop_info['pressure']:.2f} N")
            return 3
        print("Done.")
        return 0
    except Exception as e:
        if estop_info["triggered"]:
            print(f"E-STOP TRIGGERED during motion with pressure={estop_info['pressure']:.2f} N")
            return 3
        print("ERROR during movement:", e)
        return 1
    finally:
        # Signal monitor to stop and wait briefly
        stop_event.set()
        try:
            monitor_thread.join(timeout=1.0)
        except Exception:
            pass


if __name__ == "__main__":
    rc = movement_main()
    sys.exit(rc)

