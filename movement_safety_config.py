#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
movement_safety_config.py

Critical safety boundaries for robot movement.

Fill in the placeholders (the Ellipsis value: `...`) with real numeric limits.
- Joint limits are in degrees per joint (min_deg, max_deg) for a 6-DOF arm
- Cartesian limits use millimeters for XYZ and degrees for RX/RY/RZ
- You may set per-tool limits by adding an integer key matching your tool id
- A "default" entry applies to all tools that do not have explicit entries

Validation helpers raise ValueError when a command is out of bounds or when
placeholders are still present and STRICT_PLACEHOLDER_POLICY is True.

Typical integration points (examples):
- Before calling RobotController.move_to_joint_position(...):
    validate_joint_move(tool, joints)
- Before calling RobotController.move_to_cartesian_position(...)/move_linear(...):
    validate_cartesian_move(tool, pose)

NOTE: This file does not perform any I/O or side effects; it only defines
limits and pure validation helpers you can import where needed.
"""
from __future__ import annotations

from typing import Dict, List, Mapping, MutableMapping, Sequence, Tuple, Union

# Toggle to enable/disable safety validation globally
ENABLED: bool = True

# Toggle to enable/disable ONLY joint-limit checks. Keep False to rely on
# coordinate (Cartesian) checks first and avoid needing precise joint limits.
ENABLE_JOINT_LIMITS: bool = False

# Toggle for runtime coordinate monitoring (5 Hz safety watcher)
ENABLE_RUNTIME_COORD_MONITOR: bool = True

# If True, having any placeholder (`...`) in limits will cause validation to
# raise an error, forcing you to fill in the actual numbers first.
STRICT_PLACEHOLDER_POLICY: bool = True

# Placeholder alias for readability. Replace with real numbers.
P = ...  # Ellipsis object as a sentinel placeholder

# Joint limits per tool id (or "default"). Each list has 6 tuples (min_deg, max_deg).
# Replace `...` with numeric values, e.g., (-180.0, 180.0)
JOINT_LIMITS: Dict[Union[int, str], List[Tuple[float, float]]] = {
    "default": [
        (P, P),  # J1 min_deg, max_deg
        (P, P),  # J2 min_deg, max_deg
        (P, P),  # J3 min_deg, max_deg
        (P, P),  # J4 min_deg, max_deg
        (P, P),  # J5 min_deg, max_deg
        (P, P),  # J6 min_deg, max_deg
    ],
    # Example for a specific tool id (uncomment and fill if needed):
    # 3: [(-180.0, 180.0), (-120.0, 120.0), (-160.0, 160.0), (-360.0, 360.0), (-120.0, 120.0), (-360.0, 360.0)],
}

# Cartesian limits per tool id (or "default"). Values are (min, max) tuples.
# XYZ in millimeters; RX/RY/RZ in degrees.
CARTESIAN_LIMITS: Dict[Union[int, str], Dict[str, Tuple[float, float]]] = {
    "default": {
        "x": (P, P),
        "y": (P, P),
        "z": (P, P),
        "rx": (P, P),
        "ry": (P, P),
        "rz": (P, P),
    },
    # Example for a specific tool id (uncomment and fill if needed):
    # 3: {"x": (100.0, 900.0), "y": (-400.0, 400.0), "z": (50.0, 600.0), "rx": (-180.0, 180.0), "ry": (-180.0, 180.0), "rz": (-180.0, 180.0)},
}


class SafetyConfigError(RuntimeError):
    pass


def _has_placeholder_limits(lims) -> bool:
    if isinstance(lims, tuple):
        return any(v is Ellipsis for v in lims)
    if isinstance(lims, list):
        return any(_has_placeholder_limits(t) for t in lims)
    if isinstance(lims, dict):
        return any(_has_placeholder_limits(v) for v in lims.values())
    return False


def _resolve_joint_limits(tool: int | str) -> List[Tuple[float, float]]:
    lims = JOINT_LIMITS.get(tool) or JOINT_LIMITS.get("default")
    if not lims:
        raise SafetyConfigError(f"No JOINT_LIMITS configured for tool={tool!r} and no default provided.")
    if STRICT_PLACEHOLDER_POLICY and _has_placeholder_limits(lims):
        raise SafetyConfigError("JOINT_LIMITS contains placeholders (...). Fill in real values.")
    if len(lims) != 6:
        raise SafetyConfigError(f"JOINT_LIMITS for tool={tool!r} must have 6 entries, got {len(lims)}")
    return lims  # type: ignore[return-value]


def _resolve_cartesian_limits(tool: int | str) -> Dict[str, Tuple[float, float]]:
    lims = CARTESIAN_LIMITS.get(tool) or CARTESIAN_LIMITS.get("default")
    if not lims:
        raise SafetyConfigError(f"No CARTESIAN_LIMITS configured for tool={tool!r} and no default provided.")
    if STRICT_PLACEHOLDER_POLICY and _has_placeholder_limits(lims):
        raise SafetyConfigError("CARTESIAN_LIMITS contains placeholders (...). Fill in real values.")
    required = ("x", "y", "z", "rx", "ry", "rz")
    missing = [k for k in required if k not in lims]
    if missing:
        raise SafetyConfigError(f"CARTESIAN_LIMITS for tool={tool!r} missing keys: {missing}")
    return lims  # type: ignore[return-value]


def _check_in_range(name: str, value: float, bounds: Tuple[float, float]) -> None:
    lo, hi = bounds
    if lo is Ellipsis or hi is Ellipsis:
        # Should be caught earlier by STRICT_PLACEHOLDER_POLICY, but double-guard here
        raise SafetyConfigError(f"Placeholder limit for {name}; fill in {name} bounds.")
    if value < lo or value > hi:
        raise ValueError(f"{name}={value} out of bounds [{lo}, {hi}]")


def validate_joint_move(tool: int | str, joints: Sequence[float]) -> None:
    """Validate a joint-space move.

    Args:
        tool: Tool id or the string "default"
        joints: Iterable of 6 joint angles in degrees

    Raises:
        SafetyConfigError: If config is missing or contains placeholders (when joint checks enabled)
        ValueError: If any joint angle is out of bounds (when joint checks enabled)
    """
    if not ENABLED or not ENABLE_JOINT_LIMITS:
        # Joint checks are globally disabled or joint limits are temporarily disabled
        return
    if len(joints) != 6:
        raise ValueError(f"Expected 6 joint angles, got {len(joints)}")
    limits = _resolve_joint_limits(tool)
    for i, (val, bounds) in enumerate(zip(joints, limits), start=1):
        _check_in_range(f"J{i}", float(val), bounds)


def validate_cartesian_move(tool: int | str, pose: Sequence[float]) -> None:
    """Validate a Cartesian-space move.

    Args:
        tool: Tool id or the string "default"
        pose: Sequence of 6 values [x, y, z, rx, ry, rz]

    Raises:
        SafetyConfigError: If config is missing or contains placeholders
        ValueError: If any component is out of bounds
    """
    if not ENABLED:
        return
    if len(pose) != 6:
        raise ValueError(f"Expected 6 pose components, got {len(pose)}")
    limits = _resolve_cartesian_limits(tool)
    keys = ("x", "y", "z", "rx", "ry", "rz")
    for name, val in zip(keys, pose):
        _check_in_range(name.upper(), float(val), limits[name])


__all__ = [
    "ENABLED",
    "ENABLE_JOINT_LIMITS",
    "ENABLE_RUNTIME_COORD_MONITOR",
    "STRICT_PLACEHOLDER_POLICY",
    "JOINT_LIMITS",
    "CARTESIAN_LIMITS",
    "validate_joint_move",
    "validate_cartesian_move",
    "SafetyConfigError",
]
