
from typing import Dict, List  # Added import for Dict and List type hinting


# Class for handling device attributes
# This class is focused on individual device attributes like name and IP address.
class Device:
    def __init__(self, name: str, ip_address: str):
        # Initialize a new Device with a name and IP address.
        self.name = name
        self.ip_address = ip_address

    def update_device(self, name: str = None, ip_address: str = None):
        # Update the device's name or IP address.
        if name:
            self.name = name
        if ip_address:
            self.ip_address = ip_address

    def __str__(self) -> str:
        # String representation of the Device.
        return f"{self.name} ({self.ip_address})"


# New Class for handling topology-related functionalities
# This class manages the topology of the network including creating and saving topologies.
class TopologyManagement:
    def __init__(self):
        # Initialize an empty topology.
        self.topology = {}  # Using Dict for better organization

    def create_topology(self, devices: Dict[str, Device]):
        # Create a new topology with a dictionary of devices.
        self.topology = devices

    def save_topology(self):
        # Save the current topology.
        # Code to save topology
        pass


# Modified NetworkTopology class
# This class is now focused on managing devices in the network.
class NetworkTopology(TopologyManagement):  # Inherits from TopologyManagement
    def __init__(self):
        # Initialize an empty list of devices.
        super().__init__()  # Initialize parent class
        self.devices: Dict[str, Device] = {}  # Explicit type hinting

    def add_device(self, device: Device):
        # Add a new device to the network.
        self.devices[device.name] = device  # Using Dict for better organization

    def remove_device(self, device_name: str):
        # Remove a device from the network by its name.
        if device_name in self.devices:
            del self.devices[device_name]

    def update_device(self, device_name: str, new_device: Device):
        # Update a device in the network.
        self.devices[device_name] = new_device

    def get_device(self, device_name: str) -> Device:
        # Get a device by its name.
        return self.devices.get(device_name, None)

    def list_devices(self) -> List[str]:
        # List all device names in the network.
        return list(self.devices.keys())


# Main function for testing
def main():
    net_topo = NetworkTopology()
    dev1 = Device("Device1", "192.168.1.1")
    dev2 = Device("Device2", "192.168.1.2")

    net_topo.add_device(dev1)
    net_topo.add_device(dev2)

    print(net_topo.list_devices())
    print(net_topo.get_device("Device1"))


if __name__ == "__main__":
    main()
