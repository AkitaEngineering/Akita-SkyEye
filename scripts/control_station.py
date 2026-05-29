import json
import logging
from akita_skyeye.reticulum_interface import rt

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def handle_telemetry(destination, packet):
    telemetry_data = json.loads(packet["data"].decode("utf-8"))
    logging.info(f"Received telemetry: {telemetry_data}")


def main(drone_id="drone001"):
    identity = rt.Identity()
    destination = rt.Destination(identity, rt.Destination.TYPE_SERVICE, f"akita.skyeye.{drone_id}")
    rt.Link.register_incoming(destination, handle_telemetry)
    rt.Network.start()
    logging.info("Control station started.")

    while True:
        command_input = input("Enter command JSON: ")
        try:
            command_json = json.loads(command_input)
        except json.JSONDecodeError:
            logging.warning("Invalid JSON command.")
            continue

        rt.Link.announce(destination, json.dumps(command_json).encode("utf-8"))
        logging.info(f"Sent command: {command_json}")


if __name__ == "__main__":
    main()
