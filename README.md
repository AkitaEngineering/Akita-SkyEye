# Akita SkyEye

Akita SkyEye bridges a drone-side serial link with the Reticulum mesh network so commands and telemetry can move over a resilient, decentralized transport. The project also includes optional MAVLink and ExpressLRS adapters for higher-level flight control, mission handling, RC override, and link statistics.

## Features

- Reticulum-based command and telemetry transport
- Serial DroneBridge integration for command forwarding and telemetry ingestion
- Optional MAVLink support for arm, disarm, takeoff, land, mode changes, and mission workflows
- Optional ExpressLRS support for CRSF RC override and link statistics
- Failsafe checks for altitude, battery, and ExpressLRS link quality
- Test coverage for the command parser, drone interface, Reticulum wrapper, MAVLink adapter, and ExpressLRS adapter

## Repository Layout

```text
akita_skyeye/   Core package
config/         Drone and Reticulum configuration
scripts/        Convenience launch scripts
tests/          Unit tests
```

## Requirements

- Python 3.6+
- Reticulum installed on the systems that will exchange commands and telemetry
- Access to the drone serial device if you are using the DroneBridge serial path
- Optional MAVLink endpoint if you enable the `mavlink` section in the drone config
- Optional ExpressLRS serial device if you enable the `expresslrs` section in the drone config

## Installation

```bash
git clone https://github.com/AkitaEngineering/Akita-SkyEye.git
cd Akita-SkyEye
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Configuration files are loaded relative to the repository root.

### Drone Configuration

Edit `config/drone_config.json` to match your hardware and enabled integrations:

```json
{
    "drone_id": "drone001",
    "dronebridge_serial_port": "/dev/ttyAMA0",
    "dronebridge_baudrate": 115200,
    "failsafe_altitude": 10,
    "failsafe_battery": 3.5,
    "failsafe_link_quality": 30,
    "mavlink": {
        "enabled": false,
        "connection": "udp:127.0.0.1:14550",
        "baudrate": 115200,
        "wait_heartbeat": false,
        "source_system": 250,
        "source_component": 0,
        "target_system": 1,
        "target_component": 1
    },
    "expresslrs": {
        "enabled": false,
        "serial_port": "/dev/ttyUSB0",
        "baudrate": 420000,
        "timeout": 0.1,
        "address": 238
    }
}
```

Notes:

- Leave `mavlink.enabled` and `expresslrs.enabled` set to `false` unless those links are actually available.
- If no high-level adapter handles a command, the command is written to `dronebridge_serial_port` as a newline-delimited UTF-8 payload.

### Reticulum Configuration

Edit `config/reticulum_config.json` to match your Reticulum setup:

```json
{
    "interface": "wlan0",
    "identity_file": "akita_skyeye_drone001.id",
    "announce_interval": 2
}
```

Important:

- `identity_file` is passed directly to `reticulum.Identity(...)`. Use the exact path you want Reticulum to open.
- If you store the identity under `config/`, set `identity_file` to that full relative path, for example `config/akita_skyeye_drone001.id`.
- Create the identity file before starting the drone-side process.

## Running

Run the project from the repository root unless you package and install it with the same layout. Do not copy only the `akita_skyeye/` package directory; the runtime expects `config/` and `scripts/` to exist alongside it.

### Drone Side

```bash
python3 -m akita_skyeye.main
```

Or use the helper script:

```bash
./scripts/start_drone.sh
```

### Control Station

```bash
python3 scripts/control_station.py
```

The control-station script prompts for JSON command payloads and sends them over Reticulum.

## Command Format

Commands are JSON objects with a `command` field.

```json
{"command": "arm"}
{"command": "disarm"}
{"command": "takeoff", "altitude": 25}
{"command": "land"}
{"command": "set_mode", "mode": "GUIDED"}
{"command": "mission_upload", "mission": [{"lat": 40.7128, "lon": -74.0060, "alt": 25}]}
{"command": "mission_start"}
{"command": "mission_pause"}
{"command": "mission_resume"}
{"command": "mission_clear"}
{"command": "rc_override", "channels": [1000, 1000, 1000, 1000]}
```

Validation rules implemented by the parser:

- `takeoff` requires a numeric `altitude`
- `set_mode` requires a string `mode`
- `mission_upload` requires a non-empty mission list with numeric `lat`, `lon`, and `alt`
- `rc_override` requires 4 to 16 numeric channel values

## Telemetry and Failsafes

- Serial telemetry can be a JSON object or a comma-separated payload
- MAVLink telemetry can add flight mode, position, battery, and signal values
- ExpressLRS telemetry adds an `expresslrs` object and can populate signal from `uplink_link_quality`
- The drone interface triggers a landing command when configured altitude, battery, or ExpressLRS link-quality thresholds are crossed

## Testing

```bash
pytest
```

## Notes

- The Reticulum wrapper includes a shim so imports and tests still work when the `reticulum` module is absent, but live networking still requires a real Reticulum installation.
- `akita_skyeye/drone_interface.py` contains example telemetry parsing for serial data. Adjust it to match your actual DroneBridge payload format.
- Test and validate the system in a safe environment before flight use.
