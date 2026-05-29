import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def _extract_payload(packet):
    if isinstance(packet, dict):
        payload = packet.get("data", packet)
    else:
        payload = packet

    if isinstance(payload, bytes):
        return payload.decode("utf-8")
    if isinstance(payload, str):
        return payload
    return None


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_mission_items(command_data):
    mission = command_data.get("mission") or command_data.get("waypoints")
    if not isinstance(mission, list) or not mission:
        logging.warning("Mission upload requires a non-empty mission list.")
        return None

    normalized_items = []
    for item in mission:
        if not isinstance(item, dict):
            logging.warning("Mission item must be a dictionary.")
            return None

        required_fields = ("lat", "lon", "alt")
        if any(field not in item or not _is_number(item[field]) for field in required_fields):
            logging.warning("Mission item missing numeric lat/lon/alt fields.")
            return None

        normalized_item = dict(item)
        normalized_item.setdefault("command", 16)
        normalized_item.setdefault("frame", 6)
        normalized_item.setdefault("current", 1 if not normalized_items else 0)
        normalized_item.setdefault("autocontinue", 1)
        normalized_items.append(normalized_item)

    normalized_command = dict(command_data)
    normalized_command["mission"] = normalized_items
    normalized_command.pop("waypoints", None)
    return normalized_command


def _validate_command(command_data):
    if not isinstance(command_data, dict):
        logging.warning("Invalid command payload.")
        return None

    command_name = command_data.get("command")
    if not isinstance(command_name, str) or not command_name.strip():
        logging.warning("Invalid command format.")
        return None

    command_name = command_name.strip()
    normalized_command = dict(command_data)
    normalized_command["command"] = command_name

    if command_name == "takeoff" and not _is_number(normalized_command.get("altitude")):
        logging.warning("Takeoff command requires a numeric altitude.")
        return None

    if command_name == "set_mode" and not isinstance(normalized_command.get("mode"), str):
        logging.warning("set_mode command requires a mode string.")
        return None

    if command_name == "mission_upload":
        return _validate_mission_items(normalized_command)

    if command_name == "rc_override":
        channels = normalized_command.get("channels")
        if not isinstance(channels, list) or not 4 <= len(channels) <= 16:
            logging.warning("rc_override requires 4 to 16 channel values.")
            return None
        if any(not _is_number(channel) for channel in channels):
            logging.warning("rc_override channels must be numeric.")
            return None

    return normalized_command


def parse_command(packet):
    payload = _extract_payload(packet)
    if payload is None:
        logging.warning("Unsupported command payload type.")
        return None

    try:
        command_data = json.loads(payload)
    except json.JSONDecodeError:
        logging.warning("Invalid JSON command.")
        return None

    return _validate_command(command_data)
