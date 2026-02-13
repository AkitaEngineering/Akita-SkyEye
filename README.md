# Akita SkyEye: DroneBridge32 Reticulum Integration

Akita SkyEye is a project that integrates DroneBridge32 with the Reticulum mesh network, enabling long-range, resilient, and decentralized control and telemetry for drone operations.

## Features

* **Extended Range:** Leverages Reticulum's multi-hop mesh networking for increased operational range.
* **Resilience:** Mesh network architecture provides redundancy and fault tolerance.
* **Decentralized Control:** Enables distributed control and monitoring of drones.
* **Telemetry Aggregation:** Centralized collection and analysis of drone telemetry data.
* **Failsafe Mechanisms:** Includes basic failsafe checks for altitude and battery voltage.
* **Structured Command Set:** Uses a standardized JSON command format.
* **Logging:** Comprehensive logging for debugging and monitoring.
* **Unit Tests:** Includes unit tests to ensure code quality and reliability.



## Getting Started

###   Prerequisites

* Python 3.6+
* Reticulum installed and configured.
* DroneBridge32 hardware and software.
* Raspberry Pi or similar device for drone integration.
* pyserial

###   Installation

1.  Clone the repository:

    ```bash
    git clone [repository_url]
    cd akita_skyeye
    ```

2.  Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

###   Configuration

1.  Modify `config/drone_config.json` to match your DroneBridge32 setup:

    ```json
    {
      "drone_id": "drone001",
      "dronebridge_serial_port": "/dev/ttyAMA0",
      "dronebridge_baudrate": 115200,
      "failsafe_altitude": 10,
      "failsafe_battery": 3.5
    }
    ```

2.  Modify `config/reticulum_config.json` to match your Reticulum network setup:

    ```json
    {
      "interface": "wlan0",
      "identity_file": "akita_skyeye_drone001.id",
      "announce_interval": 2
    }
    ```

3.  Generate a Reticulum identity file for your drone using `reticulum-mkid` and place it in the `config/` directory.

###   Running the Application

1.  **On the Drone:**

    * Copy the `akita_skyeye` directory to your Raspberry Pi.
    * Make the startup script executable: `chmod +x scripts/start_drone.sh`.
    * Run the script: `./scripts/start_drone.sh`.

2.  **On the Control Station:**

    * Copy `scripts/control_station.py` to your control computer.
    * Run the script: `python3 scripts/control_station.py`.

###   Usage

* Use the control station to send JSON commands to the drone (e.g., `{"command": "arm"}`).
* Telemetry data will be displayed on the control station.
* The drone will perform failsafe checks for altitude and battery voltage.

###   Important Notes

* **DroneBridge32 Integration:** Adapt the `drone_interface.py` code to match your specific DroneBridge32 hardware and communication protocols.
* **Testing:** Thoroughly test the system in a safe environment before real-world deployment.
* **Safety:** Prioritize drone safety and follow all applicable regulations.
* **Reticulum Configuration:** Ensure Reticulum is properly installed and configured on all devices.
* **SoftAP:** The drone is designed to create its own softAP for local network access.
* **Telemetry Parsing:** The telemetry parsing is example code. Replace it with your actual telemetry parsing.

###   Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues.
