import serial
from .config import load_drone_config
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class DroneInterface:
    def __init__(self):
        config = load_drone_config()
        self.serial_port = config["dronebridge_serial_port"]
        self.baudrate = config["dronebridge_baudrate"]
        self.failsafe_altitude = config["failsafe_altitude"]
        self.failsafe_battery = config["failsafe_battery"]
        try:
            self.ser = serial.Serial(self.serial_port, self.baudrate, timeout=1)
            logging.info(f"Serial port {self.serial_port} opened successfully.")
        except serial.SerialException as e:
            logging.error(f"Error opening serial port: {e}")
            self.ser = None

    def send_command(self, command):
        if self.ser:
            try:
                encoded_command = command.encode('utf-8') + b'\n'
                self.ser.write(encoded_command)
                logging.info(f"Sent command: {command}")
            except serial.SerialException as e:
                logging.error(f"Error sending command: {e}")

    def get_telemetry(self):
        if self.ser:
            try:
                data = self.ser.readline().decode('utf-8').strip()
                if data:
                    try:
                        # Example parsing. Accepts formats:
                        # "alt,batt,gps_lat,gps_lon,signal" or "alt,batt,gps,signal"
                        parts = data.split(",")
                        if len(parts) >= 5:
                            gps = f"{parts[2]},{parts[3]}"
                            signal_idx = 4
                        elif len(parts) == 4:
                            gps = parts[2]
                            signal_idx = 3
                        else:
                            raise IndexError("Unexpected telemetry format")
                        telemetry = {
                            "altitude": float(parts[0]),
                            "battery": float(parts[1]),
                            "gps": gps,
                            "signal": float(parts[signal_idx])
                        }
                        return telemetry
                    except (ValueError, IndexError) as e:
                        logging.warning(f"Telemetry parsing error: {e}")
                        return {"error": "Parsing error", "raw_data": data}
                else:
                    return {"error": "No telemetry"}
            except serial.SerialException as e:
                logging.error(f"Error reading telemetry: {e}")
                return {"error": "Serial error"}
        else:
            return {"error": "Serial not connected"}

    def check_failsafe(self, telemetry):
        if "altitude" in telemetry and telemetry["altitude"] < self.failsafe_altitude:
            logging.warning("Failsafe triggered: Low altitude.")
            self.send_command('land')
        if "battery" in telemetry and telemetry["battery"] < self.failsafe_battery:
            logging.warning("Failsafe triggered: Low battery.")
            self.send_command('land')
