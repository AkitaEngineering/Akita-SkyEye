import unittest
from unittest.mock import MagicMock

from akita_skyeye.mavlink_interface import MAVLinkInterface


class FakeMessage:
    def __init__(self, **data):
        self.data = data

    def to_dict(self):
        return dict(self.data)


class FakeMav:
    def __init__(self):
        self.command_long_send = MagicMock()
        self.mission_clear_all_send = MagicMock()
        self.mission_count_send = MagicMock()
        self.mission_item_int_send = MagicMock()


class FakeMaster:
    def __init__(self, messages=None):
        self.mav = FakeMav()
        self.messages = list(messages or [])
        self.target_system = 7
        self.target_component = 3
        self.arducopter_arm = MagicMock()
        self.arducopter_disarm = MagicMock()
        self.set_mode = MagicMock()

    def recv_match(self, type=None, blocking=False, timeout=None):
        if not self.messages:
            return None
        return self.messages.pop(0)


class FakeMavlinkConstants:
    MAV_CMD_COMPONENT_ARM_DISARM = 400
    MAV_CMD_NAV_TAKEOFF = 22
    MAV_CMD_NAV_LAND = 21
    MAV_CMD_DO_PAUSE_CONTINUE = 193
    MAV_CMD_MISSION_START = 300
    MAV_FRAME_GLOBAL_RELATIVE_ALT_INT = 6
    MAV_CMD_NAV_WAYPOINT = 16
    MAV_MISSION_TYPE_MISSION = 0


class FakeMavutil:
    mavlink = FakeMavlinkConstants

    @staticmethod
    def mode_string_v10(message):
        return "GUIDED"


class TestMAVLinkInterface(unittest.TestCase):
    def setUp(self):
        self.master = FakeMaster()
        self.interface = MAVLinkInterface(
            {"connection": "udp:127.0.0.1:14550"},
            connection_factory=lambda *args, **kwargs: self.master,
            mavutil_module=FakeMavutil,
        )

    def test_get_telemetry_updates_common_fields(self):
        self.master.messages = [
            FakeMessage(mavpackettype="HEARTBEAT"),
            FakeMessage(
                mavpackettype="GLOBAL_POSITION_INT",
                lat=407128000,
                lon=-740060000,
                relative_alt=10500,
            ),
            FakeMessage(mavpackettype="SYS_STATUS", battery_remaining=82, voltage_battery=12000),
            FakeMessage(mavpackettype="RADIO_STATUS", rssi=91),
        ]

        telemetry = self.interface.get_telemetry()

        self.assertEqual(telemetry["flight_mode"], "GUIDED")
        self.assertAlmostEqual(telemetry["altitude"], 10.5)
        self.assertAlmostEqual(telemetry["latitude"], 40.7128)
        self.assertAlmostEqual(telemetry["longitude"], -74.006)
        self.assertEqual(telemetry["battery"], 82.0)
        self.assertEqual(telemetry["signal"], 91.0)

    def test_upload_mission_responds_to_requests(self):
        self.master.messages = [
            FakeMessage(mavpackettype="MISSION_REQUEST_INT", seq=0),
            FakeMessage(mavpackettype="MISSION_ACK"),
        ]

        result = self.interface.upload_mission([
            {"lat": 40.7128, "lon": -74.0060, "alt": 25},
        ])

        self.assertTrue(result)
        self.master.mav.mission_clear_all_send.assert_called_once()
        self.master.mav.mission_count_send.assert_called_once()
        self.master.mav.mission_item_int_send.assert_called_once()