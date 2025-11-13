#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Realtime Data Monitor

A lightweight CLI tool that continuously reads and prints live data from the
robotic system, including:
- Joint angles (J1..J6, degrees)
- Cartesian TCP pose (x, y, z, rx, ry, rz)
- Pressure sensor reading (raw units per microcontroller output)

This module is standalone and can be run in a separate terminal window to
monitor the system while other parts of the application are running.

Configuration is intentionally minimal and hardcoded for simplicity.
"""

import os
import sys
import time
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple

# Ensure robot controller auto-initializes when imported (do not skip)
os.environ.setdefault("ROBOT_SKIP_AUTO_INIT", "0")

try:
    # Local imports from project
    from robot_controller import RobotController, MicrocontrollerCommunication
except Exception as e:
    print(f"Failed to import controllers: {e}")
    RobotController = None  # type: ignore
    MicrocontrollerCommunication = None  # type: ignore


# =============================================================================
# Hardcoded Monitor Configuration
# =============================================================================
READ_FREQUENCY_HZ: float = 5.0          # Monitor frequency
READ_INTERVAL_SEC: float = 1.0 / READ_FREQUENCY_HZ
PRINT_DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"

# If True, each update overwrites the same console line; otherwise, prints lines
SINGLE_LINE_OUTPUT: bool = True

# CSV logging toggle and settings
LOG_TO_CSV: bool = True
CSV_OUTPUT_DIR: Path = Path("logs/monitor/")
CSV_FILE_PREFIX: str = "data_monitor_"
# Expanded coordinate into 6 columns: x, y, z, rx, ry, rz
CSV_HEADER = [
    "j1", "j2", "j3", "j4", "j5", "j6",
    "x", "y", "z", "rx", "ry", "rz",
    "pressure", "discarded_flag"
]

# Filtering thresholds
MAX_JOINT_ABS = 1000.0          # absolute sanity cap (deg)
MAX_JOINT_DELTA = 20.0          # max per-cycle change allowed (deg) typical for 5Hz sampling
MAX_CART_ABS = 1e6              # absolute cap for pose values
MAX_CART_DELTA_POS = 50.0       # mm change threshold per cycle (adjust as needed)
MAX_CART_DELTA_ORI = 10.0       # deg/radian orientation change threshold per cycle

# =============================================================================
# Utility Functions
# =============================================================================

def _fmt_list(vals: Optional[List[float]], precision: int = 2) -> str:
    if vals is None:
        return "None"
    try:
        return "[" + ", ".join(f"{v:.{precision}f}" for v in vals) + "]"
    except Exception:
        return str(vals)


def _safe_get_robot_state(rc: RobotController) -> Tuple[Optional[List[float]], Optional[List[float]], bool]:
    """Attempt to get current joint and cartesian states.
    Returns (joints, cartesian, connected_flag)."""
    try:
        joints, cart = rc.get_current_position()
        return joints, cart, True
    except Exception as e:
        sys.stderr.write(f"\nget_current_position failed: {type(e).__name__}: {e}\n")
        # Try reconnection best-effort
        try:
            rc._initialize_robot_connection()  # type: ignore (internal reconnect)
        except Exception as re:
            sys.stderr.write(f"reconnect failed: {type(re).__name__}: {re}\n")
        return None, None, False


def _safe_get_pressure(mc: MicrocontrollerCommunication) -> Optional[float]:
    try:
        val = mc.read_pressure_value()
        if isinstance(val, (int, float)) and val != -3:
            return float(val)
        return None
    except Exception:
        return None


def _prepare_csv_writer() -> Tuple[Optional[csv.writer], Optional[object]]:
    """Create CSV file and writer if logging is enabled. Returns (writer, file_handle)."""
    if not LOG_TO_CSV:
        return None, None

    try:
        CSV_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = CSV_OUTPUT_DIR / f"{CSV_FILE_PREFIX}{ts}.csv"
        f = csv_path.open("w", newline="", encoding="utf-8")
        writer = csv.writer(f)
        # Write header (column name tags) with no row name tag
        writer.writerow(CSV_HEADER)
        f.flush()
        print(f"CSV logging enabled: {csv_path}")
        return writer, f
    except Exception as e:
        print(f"Failed to initialize CSV logging: {e}")
        return None, None


def _filter_sequence(current: Optional[List[float]], prev: Optional[List[float]],
                     max_abs: float, max_delta: float) -> Tuple[Optional[List[float]], bool]:
    """Filter a sequence (joints or orientation) based on absolute and delta thresholds.
    Returns (accepted_sequence_or_prev, discarded_flag)."""
    if current is None:
        return prev, True  # discard -> use previous
    if prev is None:
        # First sample: just validate absolute values
        if any(abs(v) > max_abs or v != v for v in current):
            return None, True
        return current, False
    if len(current) != len(prev):
        return prev, True
    # Validate each value
    for i, v in enumerate(current):
        if not isinstance(v, (int, float)) or v != v or abs(v) > max_abs:
            return prev, True
        if abs(v - prev[i]) > max_delta:
            return prev, True
    return current, False


def _filter_cartesian(current: Optional[List[float]], prev: Optional[List[float]]) -> Tuple[Optional[List[float]], bool]:
    """Filter cartesian pose: first 3 are positions (mm), last 3 orientation (deg/rad)."""
    if current is None:
        return prev, True
    if prev is None:
        # First sample absolute sanity check
        if any(abs(v) > MAX_CART_ABS or v != v for v in current):
            return None, True
        return current, False
    if len(current) != len(prev):
        return prev, True
    # Position and orientation separate thresholds
    for i, v in enumerate(current):
        if not isinstance(v, (int, float)) or v != v or abs(v) > MAX_CART_ABS:
            return prev, True
        delta = abs(v - prev[i])
        if i < 3:
            if delta > MAX_CART_DELTA_POS:
                return prev, True
        else:
            if delta > MAX_CART_DELTA_ORI:
                return prev, True
    return current, False


# =============================================================================
# Main Monitor Loop
# =============================================================================

def main() -> int:
    print("Starting Realtime Data Monitor ...")

    if RobotController is None or MicrocontrollerCommunication is None:
        print("Required modules are unavailable. Exiting.")
        return 2

    # Initialize controllers
    rc = RobotController()
    mc = MicrocontrollerCommunication()

    # Print targets for diagnostics
    try:
        host_info = getattr(rc, "current_host", None)
        print(f"Robot target host: {host_info}, connected={getattr(rc, 'is_connected', False)}")
    except Exception:
        pass
    try:
        serial_port = getattr(getattr(mc, 'serial_connection', None), 'port', None)
        print(f"Microcontroller serial port: {getattr(mc, 'selected_port', serial_port)}")
    except Exception:
        pass

    # Prepare CSV logging if enabled
    csv_writer, csv_file = _prepare_csv_writer()

    print(f"Monitor frequency: {READ_FREQUENCY_HZ:.2f} Hz\nPress Ctrl+C to stop.\n")

    prev_joints: Optional[List[float]] = None
    prev_cart: Optional[List[float]] = None
    last_line_len = 0

    try:
        while True:
            ts = datetime.now().strftime(PRINT_DATETIME_FORMAT)

            joints_raw, cart_raw, connected = _safe_get_robot_state(rc)
            pressure = _safe_get_pressure(mc)

            # Filter sequences for consistency
            joints_filtered, joints_discarded = _filter_sequence(joints_raw, prev_joints, MAX_JOINT_ABS, MAX_JOINT_DELTA)
            cart_filtered, cart_discarded = _filter_cartesian(cart_raw, prev_cart)

            if not joints_discarded:
                prev_joints = joints_filtered
            if not cart_discarded:
                prev_cart = cart_filtered

            line = (
                f"[{ts}] robot_connected={connected} "
                f"joints={_fmt_list(joints_filtered, 2)} "
                f"tcp={_fmt_list(cart_filtered, 3)} "
                f"pressure={(f'{pressure:.2f}' if pressure is not None else 'None')} "
                f"discarded_joints={joints_discarded} discarded_tcp={cart_discarded}"
            )

            if SINGLE_LINE_OUTPUT:
                clear_len = max(last_line_len - len(line), 0)
                sys.stdout.write("\r" + line + " " * clear_len)
                sys.stdout.flush()
                last_line_len = len(line)
            else:
                print(line)

            # CSV row: j1..j6, x, y, z, rx, ry, rz, pressure, discarded_flag(any)
            if csv_writer is not None:
                j_vals = [""] * 6
                if joints_filtered is not None and len(joints_filtered) >= 6:
                    try:
                        j_vals = [f"{joints_filtered[i]:.2f}" if joints_filtered[i] is not None else "" for i in range(6)]
                    except Exception:
                        pass
                coord_vals = [""] * 6
                if cart_filtered is not None and len(cart_filtered) >= 6:
                    try:
                        coord_vals = [f"{cart_filtered[i]:.3f}" if cart_filtered[i] is not None else "" for i in range(6)]
                    except Exception:
                        pass
                pressure_str = f"{pressure:.2f}" if pressure is not None else ""
                discarded_flag = "1" if (joints_discarded or cart_discarded) else "0"
                try:
                    csv_writer.writerow([*j_vals, *coord_vals, pressure_str, discarded_flag])
                    csv_file.flush()  # type: ignore[union-attr]
                except Exception as e:
                    # Non-fatal; continue monitoring
                    sys.stderr.write(f"\nCSV write failed: {e}\n")

            time.sleep(READ_INTERVAL_SEC)
    except KeyboardInterrupt:
        if SINGLE_LINE_OUTPUT:
            sys.stdout.write("\n")
        print("Stopping monitor.")
        return 0
    except Exception as e:
        if SINGLE_LINE_OUTPUT:
            sys.stdout.write("\n")
        print(f"Monitor encountered an error: {e}")
        return 1
    finally:
        # Close CSV file if opened
        if 'csv_file' in locals() and csv_file is not None:
            try:
                csv_file.close()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
