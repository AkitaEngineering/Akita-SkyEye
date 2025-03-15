# tests/test_drone_interface.py
import unittest
from unittest.mock import MagicMock
from akita_skyeye.drone_interface import DroneInterface
import logging

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

if __name__ == '__main__':
    unittest.main()
