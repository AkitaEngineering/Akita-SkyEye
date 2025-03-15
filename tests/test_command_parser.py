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

if __name__ == '__main__':
    unittest.main()
