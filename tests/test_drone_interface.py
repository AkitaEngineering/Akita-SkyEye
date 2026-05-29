# tests/test_drone_interface.py
import unittest
from unittest.mock import MagicMock
from akita_skyeye.drone_interface import DroneInterface
import logging
import serial

logging.disable(logging.CRITICAL) # disable logging during tests.

class TestDroneInterface(unittest.TestCase):

    def setUp(self):
        self.drone_interface = DroneInterface()
        self.drone_interface.ser = MagicMock()

    def test_send_command(self):
        command = "arm"
        self.drone_interface.send_command(command)
        self.drone_interface.ser.write.assert_called_once_with(b'arm\n')

    def test_get_telemetry_valid(self):
        self.drone_interface.ser.readline.return_value = b'10.5,3.8,40.7128N,74.0060W,90'
        telemetry = self.drone_interface.get_telemetry()
        expected_telemetry = {
            "altitude": 10.5,
            "battery": 3.8,
            "gps": "40.7128N,74.0060W",
            "signal": 90.0
        }
        self.assertEqual(telemetry, expected_telemetry)

    def test_get_telemetry_invalid_format(self):
        self.drone_interface.ser.readline.return_value = b'invalid_data'
        telemetry = self.drone_interface.get_telemetry()
        self.assertIn("Parsing error", telemetry["error"])

    def test_get_telemetry_no_data(self):
        self.drone_interface.ser.readline.return_value = b''
        telemetry = self.drone_interface.get_telemetry()
        self.assertEqual(telemetry, {"error": "No telemetry"})

    def test_get_telemetry_serial_error(self):
        self.drone_interface.ser.readline.side_effect = serial.SerialException("Serial error")
        telemetry = self.drone_interface.get_telemetry()
        self.assertEqual(telemetry, {"error": "Serial error"})

    def test_send_command_via_mavlink(self):
        self.drone_interface.mavlink = MagicMock()
        self.drone_interface.mavlink.arm.return_value = True
        result = self.drone_interface.send_command({"command": "arm"})
        self.assertTrue(result)
        self.drone_interface.mavlink.arm.assert_called_once_with()
        self.drone_interface.ser.write.assert_not_called()

    def test_send_command_via_expresslrs(self):
        self.drone_interface.expresslrs = MagicMock()
        self.drone_interface.expresslrs.send_channels.return_value = True
        channels = [1000, 1000, 1000, 1000]
        result = self.drone_interface.send_command({"command": "rc_override", "channels": channels})
        self.assertTrue(result)
        self.drone_interface.expresslrs.send_channels.assert_called_once_with(channels)

    def test_get_telemetry_merges_expresslrs_signal(self):
        self.drone_interface.ser.readline.return_value = b''
        self.drone_interface.expresslrs = MagicMock()
        self.drone_interface.expresslrs.get_link_stats.return_value = {"uplink_link_quality": 88}
        telemetry = self.drone_interface.get_telemetry()
        self.assertEqual(telemetry["signal"], 88.0)
        self.assertEqual(telemetry["expresslrs"]["uplink_link_quality"], 88)

    def test_check_failsafe_link_quality(self):
        self.drone_interface.failsafe_link_quality = 40
        self.drone_interface.send_command = MagicMock()
        self.drone_interface.check_failsafe({"expresslrs": {"uplink_link_quality": 20}})
        self.drone_interface.send_command.assert_called_once_with({"command": "land"})

    def test_fallback_to_serial_when_mavlink_fails(self):
        self.drone_interface.mavlink = MagicMock()
        self.drone_interface.mavlink.arm.return_value = False
        result = self.drone_interface.send_command("arm")
        self.assertTrue(result)
        self.drone_interface.ser.write.assert_called_once_with(b'arm\n')

if __name__ == '__main__':
    unittest.main()
