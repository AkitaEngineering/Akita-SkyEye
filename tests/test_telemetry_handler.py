# tests/test_telemetry_handler.py
import unittest
from akita_skyeye.telemetry_handler import process_telemetry
from unittest.mock import patch
import logging

logging.disable(logging.CRITICAL)

class TestTelemetryHandler(unittest.TestCase):

    @patch('builtins.print')
    def test_process_valid_telemetry(self, mock_print):
        telemetry_data = {"altitude": 10, "battery": 3.8}
        process_telemetry(telemetry_data)
        mock_print.assert_called_once()

    @patch('builtins.print')
    def test_process_telemetry_error(self, mock_print):
        telemetry_data = {"error": "Serial error"}
        process_telemetry(telemetry_data)
        mock_print.assert_called_once()

if __name__ == '__main__':
    unittest.main()
