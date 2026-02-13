import json


def load_drone_config(filepath="config/drone_config.json"):
    with open(filepath, "r") as f:
        return json.load(f)


def load_reticulum_config(filepath="config/reticulum_config.json"):
    with open(filepath, "r") as f:
        return json.load(f)
