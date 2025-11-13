#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Middleman XML-RPC proxy with serial-bridge for pressure/gripper.

Listens on LISTEN_HOST:LISTEN_PORT (default 0.0.0.0:20005).
Forwards unknown robot methods to upstream robot at ROBOT_UPSTREAM_HOST:20003.
Implements custom methods:
- ReadPressure() -> float
- Gripper(close: bool) -> int

Configuration:
- Configure values in the `ProxyConfig` class below (no environment variables required).

Run:
  python middleman_proxy.py

Notes:
- Keep 20004 for SDK realtime channel; this proxy only handles XML-RPC (default 20005).
- If you already have an existing forwarder on 20003, this default avoids conflicts.
"""

import time
import re
import xmlrpc.client
from xmlrpc.server import SimpleXMLRPCServer
import serial
from serial.tools import list_ports
from dataclasses import dataclass
from typing import Optional

CMD_REQUEST_PRESSURE = [0x01, 0xAA, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFE, 0xEF]
CMD_GRIP_CLOSE       = [0x01, 0x90, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFE, 0xEF]
CMD_GRIP_OPEN        = [0x01, 0x91, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFE, 0xEF]


@dataclass
class ProxyConfig:
    """Static configuration for the middleman proxy."""
    upstream_host: str = "192.168.58.2"  # robot controller IP/hostname
    listen_host: str = "0.0.0.0"
    listen_port: int = 20005             # changed default to 20005 to avoid 20003 conflicts
    serial_port: Optional[str] = None     # e.g. "COM3"; None = auto-pick best available
    serial_baudrate: int = 9600
    serial_timeout: float = 1.0


def _ports_sorted():
    """Return available ports sorted by likelihood (USB adapters first, then non-COM1)."""
    ports = list(list_ports.comports())
    keywords = [
        "USB", "CH340", "CP210", "FTDI", "Arduino", "Silicon Labs", "Prolific", "USB-SERIAL"
    ]

    def score(p):
        desc = f"{p.description or ''} {p.manufacturer or ''}"
        is_usb = 1 if any(k in desc for k in keywords) else 0
        non_com1 = 1 if (p.device.upper() != "COM1") else 0
        return (is_usb, non_com1)

    return sorted(ports, key=score, reverse=True)


def _probe_pressure_on_port(device: str, baud: int, timeout: float) -> Optional[float]:
    """Try to read a single pressure value from a specific serial port.
    Return float on success; otherwise None.
    """
    try:
        ser = serial.Serial(device, baudrate=baud, timeout=timeout)
        try:
            ser.reset_input_buffer(); ser.reset_output_buffer()
            ser.write(bytearray(CMD_REQUEST_PRESSURE))
            t0 = time.time(); data = b""
            # Read until newline or timeout; also accept raw bytes and parse a float
            while time.time() - t0 < timeout:
                if ser.in_waiting:
                    data += ser.read(ser.in_waiting)
                    if b"\n" in data or b"\r" in data:
                        break
            txt = data.decode("utf-8", "ignore")
            m = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", txt)
            if m:
                return float(m.group(0))
            return None
        finally:
            try:
                ser.close()
            except Exception:
                pass
    except Exception:
        return None


def _auto_serial_port(preferred: Optional[str], baud: int, timeout: float) -> Optional[str]:
    """Choose the most likely serial port. If preferred is valid, use it; otherwise
    scan ports and pick one that returns a numeric pressure. Fall back to best-looking port.
    """
    if preferred:
        val = _probe_pressure_on_port(preferred, baud, timeout)
        if val is not None:
            return preferred
    # Try sorted candidates and pick the first port that yields a numeric value
    for p in _ports_sorted():
        val = _probe_pressure_on_port(p.device, baud, timeout)
        if val is not None:
            return p.device
    # No port produced a value; return the most likely device if any
    candidates = [p.device for p in _ports_sorted()]
    return candidates[0] if candidates else None


class RobotProxy:
    def __init__(self, cfg: ProxyConfig):
        self.cfg = cfg
        self.backend = xmlrpc.client.ServerProxy(
            f"http://{cfg.upstream_host}:20003/RPC2", allow_none=True
        )
        self.ser = serial.Serial()
        self.ser.baudrate = cfg.serial_baudrate
        self.ser.timeout = cfg.serial_timeout
        sel = _auto_serial_port(cfg.serial_port, cfg.serial_baudrate, cfg.serial_timeout)
        if sel:
            self.ser.port = sel
        self._serial_enabled = bool(sel)
        print(
            f"[Proxy] Upstream robot: {cfg.upstream_host}:20003, "
            f"serial={sel or '<none>'} baud={cfg.serial_baudrate} timeout={cfg.serial_timeout}"
        )

    def _ensure_serial_ready(self) -> bool:
        """Ensure a usable serial port is assigned; try to auto-pick if missing."""
        if self._serial_enabled and getattr(self.ser, "port", None):
            return True
        sel = _auto_serial_port(self.cfg.serial_port, self.cfg.serial_baudrate, self.cfg.serial_timeout)
        if not sel:
            self._serial_enabled = False
            return False
        try:
            if self.ser.is_open:
                self.ser.close()
        except Exception:
            pass
        self.ser.port = sel
        self._serial_enabled = True
        print(f"[Proxy] Serial port set to {sel}")
        return True

    # Custom methods exposed
    def ReadPressure(self) -> float:
        if not self._ensure_serial_ready():
            return float("nan")
        try:
            if not self.ser.is_open:
                self.ser.open()
            self.ser.reset_input_buffer(); self.ser.reset_output_buffer()
            self.ser.write(bytearray(CMD_REQUEST_PRESSURE))
            t0 = time.time(); data = b""
            while time.time() - t0 < self.cfg.serial_timeout:
                if self.ser.in_waiting:
                    data += self.ser.read(self.ser.in_waiting)
                    if b"\n" in data or b"\r" in data:
                        break
            try:
                if self.ser.is_open:
                    self.ser.close()
            except Exception:
                pass
            if not data:
                return float("nan")
            txt = data.decode("utf-8", "ignore")
            m = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", txt)
            return float(m.group(0)) if m else float("nan")
        except Exception:
            try:
                if self.ser.is_open:
                    self.ser.close()
            except Exception:
                pass
            return float("nan")

    def Gripper(self, close: bool) -> int:
        if not self._ensure_serial_ready():
            return -3
        try:
            if not self.ser.is_open:
                self.ser.open()
            self.ser.reset_input_buffer(); self.ser.reset_output_buffer()
            cmd = CMD_GRIP_CLOSE if close else CMD_GRIP_OPEN
            self.ser.write(bytearray(cmd))
            t0 = time.time()
            while time.time() - t0 < self.cfg.serial_timeout:
                if self.ser.in_waiting:
                    _ = self.ser.readline()
                    break
            try:
                if self.ser.is_open:
                    self.ser.close()
            except Exception:
                pass
            return 1
        except Exception:
            try:
                if self.ser.is_open:
                    self.ser.close()
            except Exception:
                pass
            return -3

    # Forward any other method to downstream robot
    def _dispatch(self, method, params):
        if method == "ReadPressure":
            return self.ReadPressure()
        if method == "Gripper":
            arg = params[0] if params else False
            return self.Gripper(bool(arg))
        func = getattr(self.backend, method)
        return func(*params)


if __name__ == "__main__":
    config = ProxyConfig()
    server = SimpleXMLRPCServer((config.listen_host, config.listen_port), allow_none=True, logRequests=True)
    server.register_instance(RobotProxy(config), allow_dotted_names=True)
    print(f"[Proxy] Listening on {config.listen_host}:{config.listen_port}")
    server.serve_forever()
