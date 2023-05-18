# Path: /src/network/topology.py
# This is the class for topology
import logging
from src.network.hardware import Device  # Import the updated Device class from hardware.py


class NetworkTopology:
    def __init__(self):
        self.devices = {}
        self.logger = logging.getLogger(__name__)
        self.logger.info("Network topology initialized.")

    def add_device(self, device: Device):
        """Adds a device to the network topology.

        Args:
            device (Device): An instance of the Device class.

        Raises:
            ValueError: If a device with the same ID already exists in the network topology.
        """
        if device.device_id in self.devices:
            self.logger.error("Attempted to add device with duplicate ID: %s", device.device_id)
            raise ValueError("Device ID already exists")

        self.devices[device.device_id] = device
        self.logger.info("Device with ID: %s added.", device.device_id)

    def remove_device(self, device_id: str):
        """Removes a device from the network topology.

        Args:
            device_id (str): The ID of the device to remove.

        Raises:
            ValueError: If a device with the given ID does not exist in the network topology.
        """
        if device_id not in self.devices:
            self.logger.error("Attempted to remove non-existent device with ID: %s", device_id)
            raise ValueError("Device ID not found")

        del self.devices[device_id]
        self.logger.info("Device with ID: %s removed.", device_id)

    def update_device(self, device: Device):
        """Updates the information of a device in the network topology.

        Args:
            device (Device): An instance of the Device class with updated information.

        Raises:
            ValueError: If a device with the same ID does not exist in the network topology.
        """
        if device.device_id not in self.devices:
            self.logger.error("Attempted to update non-existent device with ID: %s", device.device_id)
            raise ValueError("Device ID not found")

        self.devices[device.device_id] = device
        self.logger.info("Device with ID: %s updated.", device.device_id)

    def get_device(self, device_id: str) -> Device:
        """Gets a device from the network topology.

        Args:
            device_id (str): The ID of the device to get.

        Returns:
            Device: An instance of the Device class.

        Raises:
            ValueError: If a device with the given ID does not exist in the network topology.
        """
        if device_id not in self.devices:
            self.logger.error("Attempted to get non-existent device with ID: %s", device_id)
            raise ValueError("Device ID not found")

        self.logger.info("Device with ID: %s fetched.", device_id)
        return self.devices[device_id]

    def list_devices(self) -> list:
        """Lists all devices in the network topology.

        Returns:
            list: A list of string representations of all devices in the network topology.
        """
        self.logger.info("Listing all devices.")
        return [str(device) for device in self.devices.values()]

    def __repr__(self):
        """Provides a detailed representation of the object for debugging.

        Returns:
            str: A string representation of the object.
        """
        return f"NetworkTopology(devices={self.devices})"
