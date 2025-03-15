import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def parse_command(packet):
    try:
        command_data = json.loads(packet["data"].decode("utf-8"))
        #Validate commands here.
        if "command" not in command_data:
            logging.warning("Invalid command format.")
            return None
        return command_data
    except json.JSONDecodeError:
        logging.warning("Invalid JSON command.")
        return None
