import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def process_telemetry(telemetry_data):
    if "error" in telemetry_data:
        logging.warning(f"Telemetry error: {telemetry_data}")
    else:
        logging.info(f"Telemetry: {telemetry_data}")
