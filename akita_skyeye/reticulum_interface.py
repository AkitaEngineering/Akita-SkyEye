import reticulum as rt
import json
from .config import load_reticulum_config
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ReticulumInterface:
    def __init__(self, drone_id):
        self.drone_id = drone_id
        self.config = load_reticulum_config()
        self.identity = rt.Identity(filename=self.config["identity_file"])
        self.destination = rt.Destination(self.identity, rt.Destination.TYPE_SERVICE, f"akita.skyeye.{drone_id}")
        rt.Network.interfaces = [self.config["interface"]]
        rt.Network.start()
        logging.info("Reticulum network started.")

    def publish_telemetry(self, telemetry_data):
        telemetry_json = json.dumps(telemetry_data).encode("utf-8")
        rt.Link.announce(self.destination, telemetry_json)
        logging.debug("Telemetry published.")

    def register_command_handler(self, command_handler):
        rt.Link.register_incoming(self.destination, command_handler)
        logging.info("Command handler registered.")
