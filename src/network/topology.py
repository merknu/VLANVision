# Path: /src/network/topology.py
# This is the class for topology
import sys
from typing import Dict, List, Union
from network.hardware import Device as HardwareDevice


class Device(HardwareDevice):
    def __init__(self, device_id: str, device_type: str, name: str, ip_address: str, mac_address: str):
        super().__init__(device_id, model=None, manufacturer=None, serial_number=None, firmware_version=None,
                         device_type=device_type)
        self.name = name
        self.ip_address = ip_address
        self.mac_address = mac_address

    def update_device(self, name: str, ip_address: str):
        self.name = name
        self.ip_address = ip_address

    def __str__(self):
        return f"{self.device_type}: {self.name}, IP: {self.ip_address}, MAC: {self.mac_address}"


class NetworkTopology:
    def __init__(self):
        self.devices: Dict[str, Device] = {}

    def add_device(self, device_id: str, device_type: str, name: str, ip_address: str, mac_address: str):
        if device_id in self.devices:
            raise ValueError("Device ID already exists")
        self.devices[device_id] = Device(device_id, device_type, name, ip_address, mac_address)

    def remove_device(self, device_id: str):
        if device_id not in self.devices:
            raise ValueError("Device ID not found")
        del self.devices[device_id]

    def update_device(self, device_id: str, name: str, ip_address: str):
        if device_id not in self.devices:
            raise ValueError("Device ID not found")
        self.devices[device_id].update_device(name, ip_address)

    def get_device(self, device_id: str) -> Device:
        if device_id not in self.devices:
            raise ValueError("Device ID not found")
        return self.devices[device_id]

    def list_devices(self) -> List[str]:
        return [str(device) for device in self.devices.values()]


def create_topology(file: str) -> List[str]:
    """Create a topology from a given file."""
    with open(file, 'r') as f:
        lines = f.readlines()

    # Handle the case where the file is empty
    if not lines:
        raise ValueError("The provided file is empty.")

    node_list = []
    for line in lines:
        node_list.append(line.strip())

    return node_list


def save_topology(file: str, topology: List[str]):
    """Save a topology to a given file."""
    try:
        with open(file, 'w') as f:
            for node in topology:
                f.write(node + '\n')
    except IOError:
        print(f"Could not write to file: {file}")


def main():
    """Main function to create and save topology."""
    input_file = sys.argv[1]
    output_file = sys.argv[2]

    # Create topology
    topology = create_topology(input_file)

    # Save topology
    save_topology(output_file, topology)


if __name__ == "__main__":
    main()
