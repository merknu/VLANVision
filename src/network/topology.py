# Path: /src/network/topology.py
# This is the class for topology
from src.network.hardware import Device  # Import the updated Device class from hardware.py


class NetworkTopology:
    def __init__(self):
        self.devices = {}

    def add_device(self, device: Device):
        """Adds a device to the network topology.

        Args:
            device (Device): An instance of the Device class.

        Raises:
            ValueError: If a device with the same ID already exists in the network topology.
        """
        if device.device_id in self.devices:
            raise ValueError("Device ID already exists")
        self.devices[device.device_id] = device

    def remove_device(self, device_id: str):
        """Removes a device from the network topology.

        Args:
            device_id (str): The ID of the device to remove.

        Raises:
            ValueError: If a device with the given ID does not exist in the network topology.
        """
        if device_id not in self.devices:
            raise ValueError("Device ID not found")
        del self.devices[device_id]

    def update_device(self, device: Device):
        """Updates the information of a device in the network topology.

        Args:
            device (Device): An instance of the Device class with updated information.

        Raises:
            ValueError: If a device with the same ID does not exist in the network topology.
        """
        if device.device_id not in self.devices:
            raise ValueError("Device ID not found")
        self.devices[device.device_id] = device

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
            raise ValueError("Device ID not found")
        return self.devices[device_id]

    def list_devices(self) -> list:
        """Lists all devices in the network topology.

        Returns:
            list: A list of string representations of all devices in the network topology.
        """
        return [str(device) for device in self.devices.values()]
