import serial
import json
from .config import load_drone_config
from .expresslrs_interface import ExpressLRSInterface
from .mavlink_interface import MAVLinkInterface
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class DroneInterface:
    def __init__(
        self,
        config=None,
        serial_factory=None,
        mavlink_connection_factory=None,
        expresslrs_serial_factory=None,
    ):
        self.config = config or load_drone_config()
        self.serial_port = self.config.get("dronebridge_serial_port")
        self.baudrate = self.config.get("dronebridge_baudrate", 115200)
        self.failsafe_altitude = self.config.get("failsafe_altitude", 0)
        self.failsafe_battery = self.config.get("failsafe_battery", 0)
        self.failsafe_link_quality = self.config.get("failsafe_link_quality")
        self.ser = None
        self.mavlink = None
        self.expresslrs = None

        serial_factory = serial_factory or serial.Serial
        if self.serial_port:
            try:
                self.ser = serial_factory(self.serial_port, self.baudrate, timeout=1)
                logging.info(f"Serial port {self.serial_port} opened successfully.")
            except serial.SerialException as e:
                logging.error(f"Error opening serial port: {e}")
                self.ser = None

        mavlink_config = self.config.get("mavlink", {})
        if mavlink_config.get("enabled"):
            self.mavlink = MAVLinkInterface(
                mavlink_config,
                connection_factory=mavlink_connection_factory,
            )

        expresslrs_config = self.config.get("expresslrs", {})
        if expresslrs_config.get("enabled"):
            self.expresslrs = ExpressLRSInterface(
                expresslrs_config,
                serial_factory=expresslrs_serial_factory,
            )

    def _normalize_command(self, command):
        if isinstance(command, dict):
            return command

        if isinstance(command, bytes):
            try:
                command = command.decode("utf-8")
            except UnicodeDecodeError:
                logging.warning("Command payload is not valid UTF-8.")
                return None

        if isinstance(command, str):
            stripped_command = command.strip()
            if not stripped_command:
                return None
            if stripped_command.startswith("{"):
                try:
                    normalized_command = json.loads(stripped_command)
                except json.JSONDecodeError:
                    logging.warning("Command string is not valid JSON.")
                    return None
                return normalized_command if isinstance(normalized_command, dict) else None
            return {"command": stripped_command}

        return None

    def _dispatch_high_level_command(self, command_data):
        command_name = command_data.get("command")

        if self.mavlink:
            if command_name == "arm":
                return self.mavlink.arm()
            if command_name == "disarm":
                return self.mavlink.disarm()
            if command_name == "takeoff":
                return self.mavlink.takeoff(command_data["altitude"])
            if command_name == "land":
                return self.mavlink.land()
            if command_name == "set_mode":
                return self.mavlink.set_mode(command_data["mode"])
            if command_name == "mission_upload":
                return self.mavlink.upload_mission(command_data["mission"])
            if command_name == "mission_start":
                return self.mavlink.start_mission(
                    first_item=command_data.get("first_item", 0),
                    last_item=command_data.get("last_item", 0),
                )
            if command_name == "mission_pause":
                return self.mavlink.pause_mission()
            if command_name == "mission_resume":
                return self.mavlink.resume_mission()
            if command_name == "mission_clear":
                return self.mavlink.clear_mission()

        if self.expresslrs and command_name == "rc_override":
            return self.expresslrs.send_channels(command_data["channels"])

        return False

    def _serialize_command(self, command, normalized_command):
        if isinstance(command, dict):
            return json.dumps(command)
        if isinstance(command, bytes):
            return command.decode("utf-8")
        if isinstance(command, str):
            return command
        if normalized_command is not None:
            return json.dumps(normalized_command)
        return None

    def _parse_serial_telemetry(self, data):
        if data.startswith("{"):
            parsed_data = json.loads(data)
            if isinstance(parsed_data, dict):
                return parsed_data
            raise ValueError("JSON telemetry must decode to an object")

        parts = data.split(",")
        if len(parts) >= 5:
            gps = f"{parts[2]},{parts[3]}"
            signal_idx = 4
        elif len(parts) == 4:
            gps = parts[2]
            signal_idx = 3
        else:
            raise IndexError("Unexpected telemetry format")

        return {
            "altitude": float(parts[0]),
            "battery": float(parts[1]),
            "gps": gps,
            "signal": float(parts[signal_idx]),
        }

    def send_command(self, command):
        normalized_command = self._normalize_command(command)
        if normalized_command and self._dispatch_high_level_command(normalized_command):
            logging.info(f"Sent command via protocol adapter: {normalized_command['command']}")
            return True

        serialized_command = self._serialize_command(command, normalized_command)
        if not self.ser or serialized_command is None:
            return False

        try:
            encoded_command = serialized_command.encode('utf-8') + b'\n'
            self.ser.write(encoded_command)
            logging.info(f"Sent command: {serialized_command}")
            return True
        except serial.SerialException as e:
            logging.error(f"Error sending command: {e}")
            return False

    def _get_serial_telemetry(self):
        if not self.ser:
            return {"error": "Serial not connected"}

        try:
            data = self.ser.readline().decode('utf-8').strip()
        except serial.SerialException as e:
            logging.error(f"Error reading telemetry: {e}")
            return {"error": "Serial error"}

        if not data:
            return {"error": "No telemetry"}

        try:
            return self._parse_serial_telemetry(data)
        except (ValueError, IndexError, json.JSONDecodeError) as e:
            logging.warning(f"Telemetry parsing error: {e}")
            return {"error": "Parsing error", "raw_data": data}

    def get_telemetry(self):
        serial_telemetry = self._get_serial_telemetry()
        telemetry = {}

        if "error" not in serial_telemetry:
            telemetry.update(serial_telemetry)

        if self.mavlink:
            telemetry.update(self.mavlink.get_telemetry())

        if self.expresslrs:
            link_stats = self.expresslrs.get_link_stats()
            if link_stats:
                telemetry["expresslrs"] = link_stats
                telemetry.setdefault("signal", float(link_stats.get("uplink_link_quality", 0)))

        if telemetry:
            return telemetry

        return serial_telemetry

    def check_failsafe(self, telemetry):
        should_land = False

        if "altitude" in telemetry and telemetry["altitude"] < self.failsafe_altitude:
            logging.warning("Failsafe triggered: Low altitude.")
            should_land = True
        if "battery" in telemetry and telemetry["battery"] < self.failsafe_battery:
            logging.warning("Failsafe triggered: Low battery.")
            should_land = True

        link_quality = telemetry.get("expresslrs", {}).get("uplink_link_quality")
        if (
            self.failsafe_link_quality is not None
            and link_quality is not None
            and link_quality < self.failsafe_link_quality
        ):
            logging.warning("Failsafe triggered: Low ExpressLRS link quality.")
            should_land = True

        if should_land:
            self.send_command({"command": "land"})
