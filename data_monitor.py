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
    "pressure"
]


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

    try:
        while True:
            ts = datetime.now().strftime(PRINT_DATETIME_FORMAT)

            joints, cart, connected = _safe_get_robot_state(rc)
            pressure = _safe_get_pressure(mc)

            line = (
                f"[{ts}] robot_connected={connected} "
                f"joints={_fmt_list(joints, 2)} "
                f"tcp={_fmt_list(cart, 3)} "
                f"pressure={(f'{pressure:.2f}' if pressure is not None else 'None')}"
            )

            if SINGLE_LINE_OUTPUT:
                # Overwrite the same line for a live-updating display
                sys.stdout.write("\r" + line + " " * max(0, 120 - len(line)))
                sys.stdout.flush()
            else:
                print(line)

            # CSV row: j1..j6, x, y, z, rx, ry, rz, pressure
            if csv_writer is not None:
                j_vals = ["", "", "", "", "", ""]
                if joints is not None and len(joints) >= 6:
                    try:
                        j_vals = [f"{joints[i]:.2f}" for i in range(6)]
                    except Exception:
                        pass
                coord_vals = ["", "", "", "", "", ""]
                if cart is not None and len(cart) >= 6:
                    try:
                        coord_vals = [f"{cart[i]:.3f}" for i in range(6)]
                    except Exception:
                        pass
                pressure_str = f"{pressure:.2f}" if pressure is not None else ""
                try:
                    csv_writer.writerow([*j_vals, *coord_vals, pressure_str])
                    # Flush to ensure data is written in near-realtime
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
