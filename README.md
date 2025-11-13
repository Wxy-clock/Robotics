# Robotics – Automated Multimeter Testing System

A Python-based system to automate multimeter testing with a 6‑DOF robot arm, a microcontroller (gripper/pressure), a turntable, and optional machine vision. The repository contains a runnable headless toolset, a proxy for distributed hardware, a GUI skeleton, and safety scaffolding.

## Overview
- **Purpose**: automate probing, switching, reading, and recording measurements on multimeters.
- **Current focus**: headless tools, robot/microcontroller integration, diagnostics, and scaffolding for GUI and vision.
- **GUI**: present but minimal; disabled by default (`GUI_DISABLED=True`).

## Project status
- **Implemented**
  - Robot controller integration via vendor SDK (`Robot.py`) with realtime channel (20004) and XML‑RPC commands (20003).
  - Proxy-aware endpoint resolution (`proxy_connection.py`) and a middleman XML‑RPC bridge for pressure/gripper (`middleman_proxy.py`).
  - Microcontroller comm over serial with auto-discovery and XML‑RPC mode (`MicrocontrollerCommunication`).
  - Headless utilities: realtime data monitor, movement test CLI, socket diagnostics, movement script parser.
  - Safety scaffolding for movement with runtime 5 Hz coordinate monitor (`movement_safety_config.py`).
  - Basic turntable serial driver.
  - Vision modules (YOLO/OpenCV) prepared and decoupled from the core path.
- **Not implemented / known gaps**
  - Database features removed; code paths referring to DB are stubbed or commented.
  - GUI screens are placeholders; business logic is mostly not wired to hardware.
  - Safety limits in `movement_safety_config.py` are placeholders (`...`). Must be filled before enabling motion paths that validate limits.
  - No packaged model artifacts; vision features require user-provided weights and assets.
  - Turntable control is serial-only (no RPC bridge).
  - Many coordinates/fixtures are example defaults; calibration and teach data persistence are not included.

## Quick start
- **Requirements**
  - Python 3.9+ recommended.
  - Install dependencies: `pip install -r requirements.txt` (you may skip heavy ML deps if you won’t use vision).
- **Configure**
  - Set IP/serial and proxy flags in `system_config.py` (preferred) or environment variables (see below).
  - If using a middleman PC for the microcontroller, run `middleman_proxy.py` there first.
- **Headless tools**
  - Realtime monitor (CSV optional): `python data_monitor.py`
    - Prints 5 Hz joint/TCP/pressure. Logs to `logs/monitor/` when enabled. See Data monitor section below.
  - Socket diagnostics (connectivity test): `python socket_diagnostics.py`
  - Movement test (issues a single MoveJ): `python movement_test.py 0 -45 30 0 60 0 --tool 3 --velocity 20`
  - Scripted motions and I/O (parser): `python movement_command_parser.py test.txt`
    - By default `MOVEMENT_ENABLED=False` to avoid moving the robot; set to true only after safety limits are configured.
- **GUI (optional)**
  - Toggle GUI by setting `GUI_DISABLED=False` in `system_config.py`, then run: `python multimeter_gui.py`
  - Screens load but most actions are placeholders unless you wire them to your site’s logic.

## Configuration (central)
- `system_config.py`
  - Network: `ROBOT_IP_ADDRESS`, proxy toggles (`ROBOT_PROXY_ENABLED`, `ROBOT_PROXY_ENDPOINT`, `ROBOT_ENDPOINT_OVERRIDE`).
  - Serial defaults: `SERIAL_PORT`, `SERIAL_BAUDRATE`, `SERIAL_TIMEOUT`.
  - Robot/tool defaults and heights.
  - Paths and directories are created on import.
- Proxy resolution helpers
  - `proxy_connection.py` selects the effective host considering proxy flags and overrides.

## Environment variables (optional)
- `ROBOT_SKIP_AUTO_INIT`: set `1` to prevent sockets on import in some modules (tools set this as needed).
- Microcontroller RPC bridge
  - Client: `PRESSURE_VIA_RPC=1`, optional `PRESSURE_RPC_HOST`, `PRESSURE_RPC_PORT` (defaults to proxy host and 20005 if proxy enabled, else 20003).
  - Middleman: edit `ProxyConfig` in `middleman_proxy.py` or adapt to env vars as needed; choose a `listen_port` that does not clash with other forwarders.
- Serial port override: `MICROCONTROLLER_PORT` or `SERIAL_PORT` (e.g., `COM3`).

## Data monitor (`data_monitor.py`)
- Reads joint angles, TCP pose, and pressure at `READ_FREQUENCY_HZ` (default 5 Hz). Optionally writes CSV under `logs/monitor/`.
- Filtering and the “discarded” flag
  - `discarded_joints` and `discarded_tcp` print flags indicate this cycle’s raw data was rejected by sanity checks (NaN/type errors, absolute caps, or per-cycle deltas).
  - CSV column `discarded_flag` is the OR of both. When discarded, previous accepted values are reused; pressure is not part of the discard decision.
  - Thresholds: joints capped by `MAX_JOINT_ABS` and `MAX_JOINT_DELTA`; TCP uses separate position/orientation delta caps.

## Safety (`movement_safety_config.py`)
- Runtime 5 Hz coordinate monitor is enabled by default (`ENABLE_RUNTIME_COORD_MONITOR=True`).
- Joint and Cartesian limits are placeholders (`...`). Motion validators raise `SafetyConfigError` if placeholders remain when validation is enabled.
- Fill concrete ranges per tool before enabling real motion and switch `MOVEMENT_ENABLED=True` in `movement_command_parser.py` if using that tool to execute moves.

## Middleman proxy (`middleman_proxy.py`)
- XML‑RPC bridge that forwards unknown methods to the robot and implements `ReadPressure()` and `Gripper(close)` using a local serial port.
- Default listen port is `20005` to avoid conflicts with existing forwarders on `20003`.
- The client side (`MicrocontrollerCommunication`) auto‑switches to RPC mode when `PRESSURE_VIA_RPC=1`, or as a fallback when proxy is enabled and no local serial is available.

## File index (what each file does)
- **Core control**
  - `robot_controller.py`: High‑level `RobotController`, `ProbeHandler`, `MicrocontrollerCommunication`; integrates robot SDK, microcontroller (serial/RPC), and basic sequences.
  - `Robot.py`: Vendor SDK wrapper (XML‑RPC + realtime 20004). Do not modify unless you know the protocol.
  - `fairino_related/fairino/Robot.py`: Alternate/copy of vendor SDK; kept for reference.
  - `proxy_connection.py`: Resolves the target host considering proxy settings.
  - `system_config.py`: Central configuration and directory bootstrap.
- **Headless tools and diagnostics**
  - `data_monitor.py`: Live read/print/log joint/TCP/pressure with spike filtering.
  - `movement_test.py`: One‑shot MoveJ CLI with pressure‑based E‑stop monitor.
  - `movement_command_parser.py`: Executes plain‑text command scripts against `RobotController`, `ProbeHandler`, `MicrocontrollerCommunication`, `PressureMonitor` with validation.
  - `movement_safety_config.py`: Limits and validators for joint/Cartesian moves and a runtime safety monitor.
  - `socket_diagnostics.py`: Tests raw TCP to 20004, XML‑RPC to 20003, and SDK realtime reads.
- **Hardware drivers**
  - `turntable_controller.py`: Serial turntable rotation command (serial‑only path).
  - `standard_source_controller.py`: PyVISA control helpers for external standard source.
- **Middleman bridge**
  - `middleman_proxy.py`: XML‑RPC server that forwards to robot and bridges local serial for pressure/gripper.
- **Vision and processing**
  - `image_processing.py`: YOLO‑based LCD digit and QR recognition scaffold; requires `ultralytics` and user weights.
  - `convert_new.py`: Circle/knob detection utilities for test‑point localization.
  - `export.py`: Upstream YOLOv5 export utility (unchanged, kept for convenience).
- **GUI shell**
  - `multimeter_gui.py`: PySide2 screens; logic mostly stubbed. Controlled by `GUI_DISABLED`.
- **Utilities and docs**
  - `NAMING_CONVENTION.md`: Code naming guidelines.
  - `requirements.txt`: Dependency list (some optional/heavy).
  - `development_phase_report.txt`: Notes and progress (if present).
  - Misc camera headers: `MvCameraControl_class.py`, `CameraParams_const.py`, `CameraParams_header.py`, `PixelType_header.py`, `MvErrorDefine_const.py` (SDK-related).

## Typical workflows
- Headless monitoring while other tools run: start `data_monitor.py` in a separate terminal. Enable CSV to produce timestamped logs under `logs/monitor/`.
- Network bring‑up: run `socket_diagnostics.py` to verify 20003/20004 reachability and realtime reads before attempting motion.
- Distributed microcontroller: deploy `middleman_proxy.py` on the PC with the USB device; set `PRESSURE_VIA_RPC=1` on the client, keep your robot XML‑RPC tunnel aimed at the middleman’s port.
- Cautious motion: configure `movement_safety_config.py`, keep parser’s `MOVEMENT_ENABLED=False` until limits are filled and validated, then enable.

## Troubleshooting
- Realtime reads fail or hang
  - Check that your tunnel/route exposes 20004 in addition to 20003.
  - See `socket_diagnostics.py` summary results.
- Microcontroller not found (serial)
  - Set `MICROCONTROLLER_PORT` explicitly or use the RPC mode (`PRESSURE_VIA_RPC=1`).
- Vision errors
  - Ensure `ultralytics` is installed and provide your model weights under the expected paths.

## License
- See repository license if provided by the project owner. If missing, treat as “all rights reserved” by default.