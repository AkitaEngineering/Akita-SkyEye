import logging
import time

try:
    from pymavlink import mavutil
except ModuleNotFoundError:
    mavutil = None


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class MAVLinkInterface:
    def __init__(self, config=None, connection_factory=None, mavutil_module=None):
        self.config = config or {}
        self.mavutil = mavutil_module or mavutil
        self.master = None
        self.telemetry = {}
        self.target_system = self.config.get("target_system", 1)
        self.target_component = self.config.get("target_component", 1)

        connection_string = self.config.get("connection")
        if not connection_string:
            return

        if connection_factory is None:
            if self.mavutil is None:
                logging.warning("pymavlink is not installed; MAVLink integration disabled.")
                return
            connection_factory = self.mavutil.mavlink_connection

        try:
            self.master = connection_factory(
                connection_string,
                baud=self.config.get("baudrate", 115200),
                source_system=self.config.get("source_system", 250),
                source_component=self.config.get("source_component", 0),
                autoreconnect=True,
            )
        except TypeError:
            self.master = connection_factory(connection_string, baud=self.config.get("baudrate", 115200))
        except OSError as exc:
            logging.error(f"Failed to open MAVLink connection: {exc}")
            self.master = None
            return

        self.target_system = self.config.get(
            "target_system",
            getattr(self.master, "target_system", self.target_system),
        )
        self.target_component = self.config.get(
            "target_component",
            getattr(self.master, "target_component", self.target_component),
        )

        if self.config.get("wait_heartbeat") and hasattr(self.master, "wait_heartbeat"):
            self.master.wait_heartbeat(timeout=self.config.get("heartbeat_timeout", 5))

    def _constant(self, name, default):
        mavlink = getattr(self.mavutil, "mavlink", None)
        return getattr(mavlink, name, default)

    def _message_to_dict(self, message):
        if message is None:
            return None
        if hasattr(message, "to_dict"):
            return message.to_dict()
        if isinstance(message, dict):
            return dict(message)
        return vars(message)

    def _command_long(self, command_id, *params):
        if not self.master:
            return False
        command_params = list(params[:7])
        while len(command_params) < 7:
            command_params.append(0)
        self.master.mav.command_long_send(
            self.target_system,
            self.target_component,
            command_id,
            0,
            *command_params,
        )
        return True

    def arm(self):
        if not self.master:
            return False
        if hasattr(self.master, "arducopter_arm"):
            self.master.arducopter_arm()
            return True
        return self._command_long(self._constant("MAV_CMD_COMPONENT_ARM_DISARM", 400), 1)

    def disarm(self):
        if not self.master:
            return False
        if hasattr(self.master, "arducopter_disarm"):
            self.master.arducopter_disarm()
            return True
        return self._command_long(self._constant("MAV_CMD_COMPONENT_ARM_DISARM", 400), 0)

    def takeoff(self, altitude):
        return self._command_long(self._constant("MAV_CMD_NAV_TAKEOFF", 22), 0, 0, 0, 0, 0, 0, altitude)

    def land(self):
        return self._command_long(self._constant("MAV_CMD_NAV_LAND", 21))

    def set_mode(self, mode_name):
        if not self.master:
            return False
        if hasattr(self.master, "set_mode"):
            self.master.set_mode(mode_name)
            return True

        if hasattr(self.master, "mode_mapping"):
            mode_mapping = self.master.mode_mapping()
            if mode_name in mode_mapping:
                return self._command_long(self._constant("MAV_CMD_DO_SET_MODE", 176), mode_mapping[mode_name])
        return False

    def _drain_messages(self):
        if not self.master:
            return

        while True:
            message = self.master.recv_match(blocking=False)
            if message is None:
                break
            self._update_telemetry(message)

    def _update_telemetry(self, message):
        message_data = self._message_to_dict(message)
        if not message_data:
            return

        message_type = message_data.get("mavpackettype") or message_data.get("type")

        if message_type == "GLOBAL_POSITION_INT":
            latitude = message_data.get("lat", 0) / 1e7
            longitude = message_data.get("lon", 0) / 1e7
            self.telemetry.update(
                {
                    "altitude": message_data.get("relative_alt", 0) / 1000,
                    "latitude": latitude,
                    "longitude": longitude,
                    "gps": f"{latitude},{longitude}",
                }
            )
        elif message_type == "SYS_STATUS":
            battery_remaining = message_data.get("battery_remaining")
            if battery_remaining not in (None, -1):
                self.telemetry["battery"] = float(battery_remaining)
            voltage_battery = message_data.get("voltage_battery")
            if voltage_battery not in (None, 65535):
                self.telemetry["voltage"] = voltage_battery / 1000
        elif message_type == "BATTERY_STATUS":
            battery_remaining = message_data.get("battery_remaining")
            if battery_remaining not in (None, -1):
                self.telemetry["battery"] = float(battery_remaining)
        elif message_type == "GPS_RAW_INT":
            self.telemetry["satellites"] = message_data.get("satellites_visible")
            self.telemetry["gps_fix_type"] = message_data.get("fix_type")
        elif message_type == "RADIO_STATUS":
            if message_data.get("rssi") is not None:
                self.telemetry["signal"] = float(message_data["rssi"])
        elif message_type == "HEARTBEAT":
            if hasattr(self.mavutil, "mode_string_v10"):
                self.telemetry["flight_mode"] = self.mavutil.mode_string_v10(message)
            elif message_data.get("custom_mode") is not None:
                self.telemetry["flight_mode"] = message_data["custom_mode"]

    def get_telemetry(self):
        self._drain_messages()
        return dict(self.telemetry)

    def _send_mission_count(self, count):
        mission_type = self._constant("MAV_MISSION_TYPE_MISSION", 0)
        try:
            self.master.mav.mission_count_send(
                self.target_system,
                self.target_component,
                count,
                mission_type,
            )
        except TypeError:
            self.master.mav.mission_count_send(
                self.target_system,
                self.target_component,
                count,
            )

    def clear_mission(self):
        if not self.master:
            return False
        mission_type = self._constant("MAV_MISSION_TYPE_MISSION", 0)
        try:
            self.master.mav.mission_clear_all_send(
                self.target_system,
                self.target_component,
                mission_type,
            )
        except TypeError:
            self.master.mav.mission_clear_all_send(
                self.target_system,
                self.target_component,
            )
        return True

    def _send_mission_item(self, item):
        mission_type = self._constant("MAV_MISSION_TYPE_MISSION", 0)
        x_coord = int(item["lat"] * 1e7)
        y_coord = int(item["lon"] * 1e7)
        args = [
            self.target_system,
            self.target_component,
            item["seq"],
            item.get("frame", self._constant("MAV_FRAME_GLOBAL_RELATIVE_ALT_INT", 6)),
            item.get("command", self._constant("MAV_CMD_NAV_WAYPOINT", 16)),
            item.get("current", 0),
            item.get("autocontinue", 1),
            item.get("param1", 0),
            item.get("param2", 0),
            item.get("param3", 0),
            item.get("param4", 0),
            x_coord,
            y_coord,
            item["alt"],
            mission_type,
        ]
        try:
            self.master.mav.mission_item_int_send(*args)
        except TypeError:
            self.master.mav.mission_item_int_send(*args[:-1])

    def upload_mission(self, mission_items, timeout=5):
        if not self.master:
            return False

        indexed_items = []
        for sequence, item in enumerate(mission_items):
            mission_item = dict(item)
            mission_item["seq"] = sequence
            indexed_items.append(mission_item)

        self.clear_mission()
        self._send_mission_count(len(indexed_items))

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            message = self.master.recv_match(
                type=["MISSION_REQUEST_INT", "MISSION_REQUEST", "MISSION_ACK"],
                blocking=True,
                timeout=1,
            )
            message_data = self._message_to_dict(message)
            if not message_data:
                continue

            message_type = message_data.get("mavpackettype") or message_data.get("type")
            if message_type == "MISSION_ACK":
                return True
            if message_type in {"MISSION_REQUEST_INT", "MISSION_REQUEST"}:
                sequence = message_data.get("seq")
                if sequence is None or sequence >= len(indexed_items):
                    continue
                self._send_mission_item(indexed_items[sequence])

        return False

    def start_mission(self, first_item=0, last_item=0):
        return self._command_long(
            self._constant("MAV_CMD_MISSION_START", 300),
            first_item,
            last_item,
        )

    def pause_mission(self):
        return self._command_long(self._constant("MAV_CMD_DO_PAUSE_CONTINUE", 193), 0)

    def resume_mission(self):
        return self._command_long(self._constant("MAV_CMD_DO_PAUSE_CONTINUE", 193), 1)