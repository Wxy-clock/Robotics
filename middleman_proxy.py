#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Middleman XML-RPC proxy with serial-bridge for pressure/gripper.

Listens on LISTEN_HOST:LISTEN_PORT (default 0.0.0.0:20003).
Forwards unknown robot methods to upstream robot at ROBOT_UPSTREAM_HOST:20003.
Implements custom methods:
- ReadPressure() -> float
- Gripper(close: bool) -> int

Configuration:
- Configure values in the `ProxyConfig` class below (no environment variables required).

Run:
  python middleman_proxy.py

Notes:
- Keep 20004 for SDK realtime channel; this proxy only handles XML-RPC (20003).
- If you already have an existing forwarder on 20003, run this on 20005 and
  adjust your tunnel accordingly, or chain upstream.
"""

import time
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
    listen_port: int = 20003
    serial_port: Optional[str] = None     # e.g. "COM3"; None = auto-pick first available
    serial_baudrate: int = 9600
    serial_timeout: float = 1.0


def _auto_serial_port(preferred: Optional[str]) -> Optional[str]:
    if preferred:
        return preferred
    ports = [p.device for p in list_ports.comports()]
    return ports[0] if ports else None


class RobotProxy:
    def __init__(self, cfg: ProxyConfig):
        self.cfg = cfg
        self.backend = xmlrpc.client.ServerProxy(
            f"http://{cfg.upstream_host}:20003/RPC2", allow_none=True
        )
        self.ser = serial.Serial()
        self.ser.baudrate = cfg.serial_baudrate
        self.ser.timeout = cfg.serial_timeout
        sel = _auto_serial_port(cfg.serial_port)
        if sel:
            self.ser.port = sel
        self._serial_enabled = bool(sel)
        print(
            f"[Proxy] Upstream robot: {cfg.upstream_host}:20003, "
            f"serial={sel or '<none>'} baud={cfg.serial_baudrate} timeout={cfg.serial_timeout}"
        )

    # Custom methods exposed
    def ReadPressure(self) -> float:
        if not self._serial_enabled:
            return float("nan")
        try:
            if not self.ser.is_open:
                self.ser.open()
            self.ser.reset_input_buffer(); self.ser.reset_output_buffer()
            self.ser.write(bytearray(CMD_REQUEST_PRESSURE))
            t0 = time.time(); data = b""
            while time.time() - t0 < 1.0:
                if self.ser.in_waiting:
                    data = self.ser.readline()
                    break
            self.ser.close()
            if not data:
                return float("nan")
            try:
                return float(data.decode("utf-8").strip())
            except Exception:
                return float("nan")
        except Exception:
            try:
                if self.ser.is_open:
                    self.ser.close()
            except Exception:
                pass
            return float("nan")

    def Gripper(self, close: bool) -> int:
        if not self._serial_enabled:
            return -3
        try:
            if not self.ser.is_open:
                self.ser.open()
            self.ser.reset_input_buffer(); self.ser.reset_output_buffer()
            cmd = CMD_GRIP_CLOSE if close else CMD_GRIP_OPEN
            self.ser.write(bytearray(cmd))
            t0 = time.time()
            while time.time() - t0 < 1.0:
                if self.ser.in_waiting:
                    _ = self.ser.readline()
                    break
            self.ser.close()
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
