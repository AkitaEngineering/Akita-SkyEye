from akita_skyeye import (
    DroneInterface,
    ReticulumInterface,
    parse_command,
    process_telemetry,
    load_drone_config,
)
import time
import logging
import json
import reticulum as rt

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

drone_config = load_drone_config()
drone_id = drone_config["drone_id"]

drone_interface = DroneInterface()
reticulum_interface = ReticulumInterface(drone_id)


def command_handler(destination, packet):
    command = parse_command(packet)
    if command:
        drone_interface.send_command(json.dumps(command))


reticulum_interface.register_command_handler(command_handler)


while True:
    telemetry = drone_interface.get_telemetry()
    process_telemetry(telemetry)
    drone_interface.check_failsafe(telemetry)
    reticulum_interface.publish_telemetry(telemetry)
    rt.Network.update()
    time.sleep(1)
