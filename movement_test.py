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

from robot_controller import RobotController
from proxy_connection import resolve_robot_host, is_proxy_enabled, get_proxy_endpoint
from system_config import ROBOT_IP_ADDRESS


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

    rc = RobotController()
    if not getattr(rc, "is_connected", False):
        print("ERROR: Robot not connected.")
        return 2

    try:
        # Execute MoveJ
        rc.move_to_joint_position(args.tool, args.velocity, joint_angles)
        print("MoveJ command issued. Waiting...")
        time.sleep(args.sleep)

        # Read back current pose
        joints, pose = rc.get_current_position()
        print("Current joints (deg):", [round(v, 3) for v in joints])
        print("Current TCP pose:", [round(v, 3) for v in pose])
        print("Done.")
        return 0
    except Exception as e:
        print("ERROR during movement:", e)
        return 1



if __name__ == "__main__":
    rc = movement_main()
    sys.exit(rc)

