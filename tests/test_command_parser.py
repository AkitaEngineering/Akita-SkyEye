# tests/test_command_parser.py
import unittest
from akita_skyeye.command_parser import parse_command
import json
import logging

logging.disable(logging.CRITICAL)

class TestCommandParser(unittest.TestCase):

    def test_parse_valid_command(self):
        packet = {"data": json.dumps({"command": "arm"}).encode("utf-8")}
        command = parse_command(packet)
        self.assertEqual(command, {"command": "arm"})

    def test_parse_invalid_json(self):
        packet = {"data": b"invalid_json"}
        command = parse_command(packet)
        self.assertIsNone(command)

    def test_parse_missing_command_key(self):
        packet = {"data": json.dumps({"test": "value"}).encode("utf-8")}
        command = parse_command(packet)
        self.assertIsNone(command)

    def test_parse_valid_mission_upload(self):
        packet = {
            "data": json.dumps(
                {
                    "command": "mission_upload",
                    "mission": [{"lat": 40.7128, "lon": -74.0060, "alt": 25}],
                }
            ).encode("utf-8")
        }
        command = parse_command(packet)
        self.assertEqual(command["command"], "mission_upload")
        self.assertEqual(command["mission"][0]["command"], 16)

    def test_parse_invalid_mission_upload(self):
        packet = {
            "data": json.dumps(
                {
                    "command": "mission_upload",
                    "mission": [{"lat": 40.7128, "lon": -74.0060}],
                }
            ).encode("utf-8")
        }
        command = parse_command(packet)
        self.assertIsNone(command)

    def test_parse_valid_rc_override(self):
        packet = {
            "data": json.dumps(
                {
                    "command": "rc_override",
                    "channels": [1000, 1000, 1000, 1000],
                }
            ).encode("utf-8")
        }
        command = parse_command(packet)
        self.assertEqual(command["channels"], [1000, 1000, 1000, 1000])

if __name__ == '__main__':
    unittest.main()
