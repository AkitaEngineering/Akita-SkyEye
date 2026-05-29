from akita_skyeye import (
    DroneInterface,
    ReticulumInterface,
    parse_command,
    process_telemetry,
    load_drone_config,
)
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    drone_config = load_drone_config()
    drone_id = drone_config["drone_id"]
    drone_interface = DroneInterface(config=drone_config)
    reticulum_interface = ReticulumInterface(drone_id)

    def command_handler(destination, packet):
        command = parse_command(packet)
        if command:
            drone_interface.send_command(command)

    reticulum_interface.register_command_handler(command_handler)

    try:
        while True:
            telemetry = drone_interface.get_telemetry()
            process_telemetry(telemetry)
            drone_interface.check_failsafe(telemetry)
            reticulum_interface.publish_telemetry(telemetry)
            reticulum_interface.update_network()
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Akita SkyEye stopped by user.")


if __name__ == "__main__":
    main()
