#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proxy connection utilities for robot endpoint resolution.

This module provides a thin wrapper over centralized configuration in
`system_config.py` to determine whether a proxy should be used for
robot communication and which host to target.

Configuration (set in system_config.py):
- ROBOT_PROXY_ENABLED: bool to enable proxy mode
- ROBOT_PROXY_ENDPOINT: Hostname/IP to connect when proxy is enabled (e.g. '127.0.0.1')
- ROBOT_ENDPOINT_OVERRIDE: Optional host/IP to use when proxy is disabled

Usage:
    from proxy_connection import resolve_robot_host, is_proxy_enabled, get_proxy_endpoint
    host = resolve_robot_host(default_host)
    if is_proxy_enabled():
        print(f"Proxy Endpoint: {get_proxy_endpoint()}")

In proxy mode, ports 8080/20003/20004 should already be forwarded by the OS/tooling
from the chosen endpoint to the robot-side middleman.
"""

from typing import Optional

# Use centralized config
import system_config as cfg


def is_proxy_enabled() -> bool:
    """Return True if proxy mode is enabled via configuration (system_config)."""
    try:
        return bool(cfg.is_proxy_enabled())
    except Exception:
        # Fallback to constant if helper not present
        return bool(getattr(cfg, "ROBOT_PROXY_ENABLED", False))


def get_proxy_endpoint(default: str = "127.0.0.1") -> str:
    """Return the proxy endpoint host/IP to use when proxy is enabled."""
    try:
        return str(cfg.get_proxy_endpoint())
    except Exception:
        return str(getattr(cfg, "ROBOT_PROXY_ENDPOINT", default))


def resolve_robot_host(default_host: str) -> str:
    """
    Resolve the robot controller host based on proxy toggle and overrides.

    Args:
        default_host: The robot's configured IP from system configuration.

    Returns:
        Host string to be used when creating Robot.RPC(...)
    """
    # If proxy mode enabled, use proxy endpoint
    if is_proxy_enabled():
        return get_proxy_endpoint()

    # Allow a direct-mode override from configuration
    try:
        override = cfg.get_robot_endpoint_override()
    except Exception:
        override = getattr(cfg, "ROBOT_ENDPOINT_OVERRIDE", None)

    if override:
        return str(override)

    # Default to the provided host
    return default_host


__all__ = [
    "resolve_robot_host",
    "is_proxy_enabled",
    "get_proxy_endpoint",
]
