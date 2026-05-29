# tests/test_reticulum_interface.py
import unittest
from unittest.mock import MagicMock
from akita_skyeye.reticulum_interface import ReticulumInterface
import reticulum as rt
import logging

logging.disable(logging.CRITICAL)

class TestReticulumInterface(unittest.TestCase):

    def setUp(self):
        self.drone_id = "test_drone"
        self.reticulum_interface = ReticulumInterface(self.drone_id)
        self.reticulum_interface.destination = MagicMock()
        self.reticulum_interface.identity = MagicMock()

    def test_publish_telemetry(self):
        telemetry_data = {"test": "data"}
        self.reticulum_interface.publish_telemetry(telemetry_data)
        self.reticulum_interface.destination.announce.assert_called_once()

    def test_register_command_handler(self):
        mock_handler = MagicMock()
        self.reticulum_interface.register_command_handler(mock_handler)
        rt.Link.register_incoming.assert_called_once()

if __name__ == '__main__':
    unittest.main()
