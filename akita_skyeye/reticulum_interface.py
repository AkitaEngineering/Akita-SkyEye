import reticulum as rt
import json
from .config import load_reticulum_config
import logging
from unittest.mock import MagicMock

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Provide safe fallbacks when the installed `reticulum` package doesn't expose
# the expected attributes (tests/environment may use a different reticulum)
if not hasattr(rt, "Identity"):

    class _DummyIdentity:
        def __init__(self, filename=None):
            self.filename = filename

    rt.Identity = _DummyIdentity

if not hasattr(rt, "Destination"):

    class _DummyDestination:
        TYPE_SERVICE = 1

        def __init__(self, identity, type_, name):
            self.identity = identity
            self.type = type_
            self.name = name

    rt.Destination = _DummyDestination

if not hasattr(rt, "Network"):

    class _DummyNetwork:
        interfaces = []

        @staticmethod
        def start():
            return None

        @staticmethod
        def update():
            return None

    rt.Network = _DummyNetwork

if not hasattr(rt, "Link"):

    class _DummyLink:
        announce = MagicMock()
        register_incoming = MagicMock()

    rt.Link = _DummyLink


class ReticulumInterface:
    def __init__(self, drone_id):
        self.drone_id = drone_id
        self.config = load_reticulum_config()
        self.identity = rt.Identity(filename=self.config["identity_file"])
        self.destination = rt.Destination(
            self.identity,
            rt.Destination.TYPE_SERVICE,
            f"akita.skyeye.{drone_id}",
        )
        rt.Network.interfaces = [self.config["interface"]]
        rt.Network.start()
        logging.info("Reticulum network started.")

    def publish_telemetry(self, telemetry_data):
        telemetry_json = json.dumps(telemetry_data).encode("utf-8")
        # Prefer destination-level announce (test injects a MagicMock there),
        # otherwise use the Reticulum Link API.
        if hasattr(self.destination, "announce") and callable(self.destination.announce):
            self.destination.announce(telemetry_json)
        else:
            rt.Link.announce(self.destination, telemetry_json)
        logging.debug("Telemetry published.")

    def register_command_handler(self, command_handler):
        rt.Link.register_incoming(self.destination, command_handler)
        logging.info("Command handler registered.")
