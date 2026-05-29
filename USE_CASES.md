# Akita SkyEye Use Cases

This document describes the main ways to use Akita SkyEye based on the current repository implementation. It is intended for operators, integrators, and developers who need to understand how the system fits into drone-side networking, flight control, and telemetry workflows.

## System Context

Akita SkyEye runs on a companion computer attached to a drone-side serial link and publishes telemetry over Reticulum. A control station sends JSON commands back to the drone over the same mesh path. Depending on configuration, the drone-side process can:

- forward commands to a serial-connected DroneBridge-style endpoint
- translate high-level commands into MAVLink actions
- send RC override data through an ExpressLRS serial link
- trigger a landing command when configured safety thresholds are crossed

The main runtime entry points are:

- `python3 -m akita_skyeye.main` for the drone-side service
- `python3 scripts/control_station.py` for the operator-side command prompt

## Actors

- Drone operator: sends commands and watches telemetry from a control station
- Drone-side companion computer: runs Akita SkyEye and brokers traffic between Reticulum and local interfaces
- Flight controller or autopilot: receives serial or MAVLink commands and emits telemetry
- ExpressLRS receiver or transmitter path: accepts RC override frames and reports link statistics when enabled

## Use Cases

### 1. Telemetry Backhaul Over Reticulum

**Goal:** Publish live drone telemetry across a Reticulum mesh when direct local access to the aircraft is limited or unavailable.

**When to use it:**

- the drone is beyond normal point-to-point network range
- you want a mesh-friendly telemetry path for distributed operations
- the control station needs updates without a direct serial connection to the aircraft

**Preconditions:**

- Reticulum is installed on both ends
- `config/reticulum_config.json` points at a valid interface and identity file
- the drone-side process can read telemetry from the configured serial device, MAVLink connection, or ExpressLRS interface

**Typical flow:**

1. Start the drone-side service with `python3 -m akita_skyeye.main`.
2. The service initializes the Reticulum destination for the configured drone ID.
3. The drone interface reads telemetry from the available local interfaces.
4. Akita SkyEye publishes the telemetry payload over Reticulum.
5. A control station or other subscriber receives and displays the data.

**Expected outcome:** The operator can observe altitude, battery, position, signal, flight-mode, or ExpressLRS link-quality data without talking directly to the drone's local interface.

### 2. Remote Command Relay To A Serial Flight Stack

**Goal:** Send simple JSON commands over Reticulum and have them forwarded to a serial-connected local system.

**When to use it:**

- the downstream controller expects newline-delimited text or JSON on a serial port
- you want to preserve an existing serial command path while adding a Reticulum transport layer

**Preconditions:**

- `dronebridge_serial_port` in `config/drone_config.json` points to a reachable serial device
- the downstream serial consumer understands the payload format being forwarded

**Typical flow:**

1. Start `scripts/control_station.py` on the operator machine.
2. Enter a JSON command such as `{"command": "arm"}`.
3. The control station announces that payload over Reticulum.
4. The drone-side handler parses the payload and tries high-level adapters first.
5. If no adapter claims the command, Akita SkyEye writes the command to the configured serial port followed by a newline.

**Expected outcome:** Existing serial-based command consumers can be reached through the mesh without changing the command transport at the operator end.

### 3. High-Level Vehicle Control Through MAVLink

**Goal:** Turn high-level JSON commands into direct MAVLink control actions.

**When to use it:**

- the autopilot exposes a MAVLink endpoint
- operators need arm, disarm, takeoff, land, or mode changes instead of raw serial forwarding

**Preconditions:**

- `mavlink.enabled` is set to `true` in `config/drone_config.json`
- `mavlink.connection` and related connection settings match the local autopilot endpoint
- `pymavlink` is installed in the runtime environment

**Typical commands:**

- `{"command": "arm"}`
- `{"command": "disarm"}`
- `{"command": "takeoff", "altitude": 25}`
- `{"command": "land"}`
- `{"command": "set_mode", "mode": "GUIDED"}`

**Expected outcome:** Akita SkyEye invokes the corresponding MAVLink action locally instead of falling back to the serial command path.

### 4. Waypoint Mission Upload And Control

**Goal:** Upload, start, pause, resume, or clear autonomous missions over the Reticulum command channel.

**When to use it:**

- the aircraft supports MAVLink mission workflows
- mission control needs to happen from a remote control point over mesh networking

**Preconditions:**

- MAVLink support is enabled and operational
- the mission payload contains at least one item with numeric `lat`, `lon`, and `alt` values

**Typical commands:**

- `{"command": "mission_upload", "mission": [{"lat": 40.7128, "lon": -74.0060, "alt": 25}]}`
- `{"command": "mission_start"}`
- `{"command": "mission_pause"}`
- `{"command": "mission_resume"}`
- `{"command": "mission_clear"}`

**Expected outcome:** The drone-side service converts the mission payload into MAVLink mission items, responds to mission requests from the autopilot, and controls mission execution through standard MAVLink commands.

### 5. Manual Override Through ExpressLRS

**Goal:** Inject RC channel values into an ExpressLRS link from the drone-side process.

**When to use it:**

- a remote operator needs low-level stick-like control rather than a higher-level autopilot command
- a test or recovery workflow needs direct channel injection

**Preconditions:**

- `expresslrs.enabled` is set to `true` in `config/drone_config.json`
- the configured ExpressLRS serial device is reachable
- channel values are supplied as a list of 4 to 16 numeric values

**Typical command:**

- `{"command": "rc_override", "channels": [1000, 1000, 1000, 1000]}`

**Expected outcome:** Akita SkyEye packs the channel values into a CRSF RC frame and writes it to the ExpressLRS serial interface.

### 6. Link-Quality Aware Safety Landing

**Goal:** Reduce the chance of losing the aircraft by triggering a landing command when telemetry crosses configured safety thresholds.

**When to use it:**

- field operations need automatic response to degraded conditions
- the deployment depends on ExpressLRS link quality or basic battery and altitude thresholds

**Preconditions:**

- `failsafe_altitude`, `failsafe_battery`, and optionally `failsafe_link_quality` are configured appropriately
- telemetry sources provide the fields needed to evaluate those thresholds

**Typical flow:**

1. The drone-side process reads serial, MAVLink, or ExpressLRS telemetry.
2. Akita SkyEye checks the configured thresholds.
3. If altitude or battery falls below the configured minimum, or ExpressLRS link quality drops below the configured threshold, the service issues `{"command": "land"}`.

**Expected outcome:** A landing command is sent automatically when configured safety conditions are violated.

### 7. Bench Testing And Integration Validation

**Goal:** Validate command parsing and adapter behavior before flight deployment.

**When to use it:**

- changing telemetry parsing or command handling
- adding MAVLink or ExpressLRS integrations
- verifying repo health in CI or on a development workstation

**Preconditions:**

- the repository dependencies are installed

**Typical flow:**

1. Run `pytest` from the repository root.
2. Confirm the command parser, drone interface, Reticulum wrapper, MAVLink adapter, and ExpressLRS adapter tests pass.

**Expected outcome:** Core protocol handling works as expected before connecting to live hardware.

## Operational Considerations

- The control-station script defaults to `drone001`; if you change the drone ID in the config, align the operator workflow to use the same destination name.
- The Reticulum identity path is used exactly as configured. If the identity file lives under `config/`, include that relative path explicitly.
- Serial telemetry parsing supports JSON objects and a simple comma-separated format. If your hardware emits a different schema, update the drone interface accordingly.
- If `reticulum`, `pymavlink`, or hardware serial endpoints are unavailable, tests can still run, but the live integrations described here will not operate until those dependencies are present.

## Recommended Deployment Sequence

1. Configure `config/drone_config.json` and `config/reticulum_config.json` for the target drone.
2. Verify the Reticulum identity file exists at the configured path.
3. Run `pytest` before field deployment.
4. Start the drone-side service.
5. Start the control-station script and send a simple command such as `{"command": "arm"}`.
6. Confirm telemetry is flowing and validate the enabled adapter path before relying on autonomous or safety-critical operations.