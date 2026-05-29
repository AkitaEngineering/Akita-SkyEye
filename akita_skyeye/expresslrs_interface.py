import logging

import serial


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class ExpressLRSInterface:
    LINK_STATISTICS_FRAME = 0x14
    RC_CHANNELS_PACKED_FRAME = 0x16
    DEFAULT_ADDRESS = 0xEE
    DEFAULT_CHANNEL_VALUE = 992
    MIN_CHANNEL_VALUE = 172
    MAX_CHANNEL_VALUE = 1811
    CRC_POLYNOMIAL = 0xD5

    def __init__(self, config=None, serial_factory=None):
        self.config = config or {}
        self.ser = None
        self.link_stats = {}

        serial_port = self.config.get("serial_port")
        if not serial_port:
            return

        serial_factory = serial_factory or serial.Serial
        try:
            self.ser = serial_factory(
                serial_port,
                self.config.get("baudrate", 420000),
                timeout=self.config.get("timeout", 0.1),
            )
            logging.info(f"ExpressLRS serial port {serial_port} opened successfully.")
        except serial.SerialException as exc:
            logging.error(f"Error opening ExpressLRS serial port: {exc}")
            self.ser = None

    @classmethod
    def _crc8(cls, payload):
        crc = 0
        for byte in payload:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = ((crc << 1) ^ cls.CRC_POLYNOMIAL) & 0xFF
                else:
                    crc = (crc << 1) & 0xFF
        return crc

    @classmethod
    def _build_frame(cls, address, frame_type, payload):
        frame_payload = bytes([frame_type]) + payload
        length = len(frame_payload) + 1
        crc = cls._crc8(frame_payload)
        return bytes([address, length]) + frame_payload + bytes([crc])

    @classmethod
    def _pack_channels(cls, channels):
        padded_channels = list(channels[:16])
        while len(padded_channels) < 16:
            padded_channels.append(cls.DEFAULT_CHANNEL_VALUE)

        accumulator = 0
        bit_count = 0
        packed = bytearray()

        for channel in padded_channels:
            clamped_channel = max(cls.MIN_CHANNEL_VALUE, min(cls.MAX_CHANNEL_VALUE, int(channel)))
            accumulator |= clamped_channel << bit_count
            bit_count += 11

            while bit_count >= 8:
                packed.append(accumulator & 0xFF)
                accumulator >>= 8
                bit_count -= 8

        if bit_count:
            packed.append(accumulator & 0xFF)

        return bytes(packed[:22])

    @staticmethod
    def _signed_byte(value):
        return value - 256 if value > 127 else value

    @classmethod
    def _parse_link_statistics(cls, payload):
        if len(payload) < 10:
            raise ValueError("Incomplete ExpressLRS link statistics payload")

        return {
            "uplink_rssi_1": payload[0],
            "uplink_rssi_2": payload[1],
            "uplink_link_quality": payload[2],
            "uplink_snr": cls._signed_byte(payload[3]),
            "active_antenna": payload[4],
            "rf_mode": payload[5],
            "uplink_tx_power": payload[6],
            "downlink_rssi": payload[7],
            "downlink_link_quality": payload[8],
            "downlink_snr": cls._signed_byte(payload[9]),
        }

    def send_channels(self, channels):
        if not self.ser:
            return False

        payload = self._pack_channels(channels)
        frame = self._build_frame(
            self.config.get("address", self.DEFAULT_ADDRESS),
            self.RC_CHANNELS_PACKED_FRAME,
            payload,
        )
        self.ser.write(frame)
        return True

    def read_frame(self):
        if not self.ser:
            return None

        header = self.ser.read(2)
        if len(header) < 2:
            return None

        address = header[0]
        length = header[1]
        body = self.ser.read(length)
        if len(body) < length:
            return None

        frame_type = body[0]
        payload = body[1:-1]
        crc = body[-1]
        if self._crc8(bytes([frame_type]) + payload) != crc:
            logging.warning("ExpressLRS frame CRC check failed.")
            return {"error": "CRC error"}

        if frame_type == self.LINK_STATISTICS_FRAME:
            self.link_stats = self._parse_link_statistics(payload)
            return dict(self.link_stats)

        return {
            "address": address,
            "type": frame_type,
            "payload": payload,
        }

    def get_link_stats(self):
        if not self.ser:
            return dict(self.link_stats)

        if (getattr(self.ser, "in_waiting", 0) or 0) >= 2:
            frame = self.read_frame()
            if frame and "error" not in frame and "uplink_link_quality" in frame:
                return frame

        return dict(self.link_stats)