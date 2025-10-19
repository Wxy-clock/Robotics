#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Socket diagnostics for robot SDK (non-GUI)

This module helps investigate socket errors like:
  

It performs:
- Raw TCP connectivity test to the realtime state port (20004)
- XML-RPC ping to controller (20003)
- SDK RPC lifecycle test (create RPC, read a few values, clean close)

No changes are made to Robot.py.
"""

import os
import sys
import time
import socket
import platform
import traceback
from datetime import datetime

try:
    # Use robot IP only; database and GUI PNG dependencies removed
    from system_config import ROBOT_IP_ADDRESS
except Exception:
    ROBOT_IP_ADDRESS = os.environ.get("ROBOT_IP_ADDRESS", "192.168.58.2")

# Import SDK without modifying it
import Robot

# Proxy-aware host resolution
try:
    from proxy_connection import resolve_robot_host, is_proxy_enabled, get_proxy_endpoint
except Exception:
    # Fallbacks if module missing
    def resolve_robot_host(default_host: str) -> str:
        return os.environ.get("ROBOT_ENDPOINT", default_host)
    def is_proxy_enabled() -> bool:
        v = os.environ.get("ROBOT_PROXY_ENABLED", "0").strip().lower()
        return v in ("1", "true", "yes", "on")
    def get_proxy_endpoint(default: str = "127.0.0.1") -> str:
        return os.environ.get("ROBOT_PROXY_ENDPOINT", default)

TARGET_HOST = resolve_robot_host(ROBOT_IP_ADDRESS)


def _print_header():
    print("==== Robot Socket Diagnostics ====")
    print(f"Time: {datetime.now().isoformat()}")
    print(f"Python: {sys.version.split()[0]} on {platform.system()} {platform.release()} ({platform.version()})")
    print(f"Process: pid={os.getpid()} cwd={os.getcwd()}")
    print(f"Configured Robot IP: {ROBOT_IP_ADDRESS}")
    print(f"Proxy Enabled: {'YES' if is_proxy_enabled() else 'NO'}")
    if is_proxy_enabled():
        print(f"Proxy Endpoint: {get_proxy_endpoint()}")
    print(f"Effective Target Host: {TARGET_HOST}")
    print("==================================")


def raw_port_test(ip: str, port: int, timeout: float = 2.0) -> bool:
    print(f"[RAW] Connecting to {ip}:{port} ...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((ip, port))
        fileno = s.fileno()
        print(f"[RAW] Connected. fileno={fileno}")
        return True
    except Exception as e:
        print(f"[RAW] Connect failed: {e}")
        return False
    finally:
        try:
            s.close()
            print("[RAW] Socket closed ok")
        except Exception as e:
            print(f"[RAW] Socket close error: {e}")


def xmlrpc_ping(ip: str) -> bool:
    print("[RPC] XML-RPC ping via GetControllerIP ...")
    try:
        # Short-lived proxy, allow default timeout
        proxy = Robot.xmlrpc.client.ServerProxy(f"http://{ip}:20003")
        socket.setdefaulttimeout(1)
        try:
            ret = proxy.GetControllerIP()
            ok = isinstance(ret, list) and len(ret) >= 1
            print(f"[RPC] GetControllerIP returned: {ret if ok else 'unexpected'}")
            return ok
        finally:
            socket.setdefaulttimeout(None)
    except Exception as e:
        print(f"[RPC] XML-RPC ping failed: {e}")
        return False


def sdk_realtime_test(ip: str, hold_seconds: float = 3.0) -> bool:
    print("[SDK] Creating Robot.RPC and waiting for realtime thread ...")
    rpc = None
    try:
        rpc = Robot.RPC(ip)
        # Give realtime thread a moment to start
        time.sleep(0.5)
        # Try reading a few realtime values while the thread runs
        t_end = time.time() + hold_seconds
        ok_reads = 0
        while time.time() < t_end:
            try:
                err_pose, pose = rpc.GetActualTCPPose(1)
                err_j, joints = rpc.GetActualJointPosDegree(1)
                if err_pose == 0 and err_j == 0:
                    ok_reads += 1
                time.sleep(0.2)
            except Exception as e:
                print(f"[SDK] Read error: {e}")
                break
        print(f"[SDK] Ok reads: {ok_reads}")
        return ok_reads > 0
    except Exception as e:
        print(f"[SDK] RPC init or read failed: {e}")
        tb = traceback.format_exc()
        print(tb)
        return False
    finally:
        if rpc is not None:
            print("[SDK] Closing RPC ...")
            try:
                rpc.CloseRPC()
                print("[SDK] RPC closed cleanly")
            except Exception as e:
                print(f"[SDK] RPC close error: {e}")


def run():
    _print_header()

    results = {
        'raw_20004': raw_port_test(TARGET_HOST, 20004),
        'xmlrpc_20003': xmlrpc_ping(TARGET_HOST),
        'sdk_realtime': sdk_realtime_test(TARGET_HOST),
    }

    print("==== Summary ====")
    for k, v in results.items():
        print(f"{k}: {'OK' if v else 'FAIL'}")

    # Return True if at least one succeeded, else False
    return any(results.values())


if __name__ == '__main__':
    ok = run()
    sys.exit(0 if ok else 1)
