import unittest
from unittest.mock import MagicMock

from akita_skyeye.expresslrs_interface import ExpressLRSInterface


class TestExpressLRSInterface(unittest.TestCase):
    def setUp(self):
        self.serial_port = MagicMock()
        self.interface = ExpressLRSInterface(
            {"serial_port": "/dev/null"},
            serial_factory=lambda *args, **kwargs: self.serial_port,
        )

    def test_send_channels_packs_rc_frame(self):
        result = self.interface.send_channels([1000] * 8)

        self.assertTrue(result)
        frame = self.serial_port.write.call_args[0][0]
        self.assertEqual(frame[2], ExpressLRSInterface.RC_CHANNELS_PACKED_FRAME)

    def test_get_link_stats_parses_valid_frame(self):
        payload = bytes([100, 99, 88, 251, 1, 2, 3, 97, 87, 253])
        frame = ExpressLRSInterface._build_frame(
            ExpressLRSInterface.DEFAULT_ADDRESS,
            ExpressLRSInterface.LINK_STATISTICS_FRAME,
            payload,
        )
        self.serial_port.in_waiting = len(frame)
        self.serial_port.read.side_effect = [frame[:2], frame[2:]]

        stats = self.interface.get_link_stats()

        self.assertEqual(stats["uplink_link_quality"], 88)
        self.assertEqual(stats["uplink_snr"], -5)
        self.assertEqual(stats["downlink_snr"], -3)