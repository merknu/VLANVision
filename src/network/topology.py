# Path: /src/network/topology.py
# This is the class for topology
class Device:
    def __init__(self, device_id, device_type, name, ip_address, mac_address):
        self.device_id = device_id
        self.device_type = device_type
        self.name = name
        self.ip_address = ip_address
        self.mac_address = mac_address

    def update_device(self, name, ip_address):
        self.name = name
        self.ip_address = ip_address

    def __str__(self):
        return f"{self.device_type}: {self.name}, IP: {self.ip_address}, MAC: {self.mac_address}"


class NetworkTopology:
    def __init__(self):
        self.devices = {}

    def add_device(self, device_id, device_type, name, ip_address, mac_address):
        if device_id in self.devices:
            raise ValueError("Device ID already exists")
        self.devices[device_id] = Device(device_id, device_type, name, ip_address, mac_address)

    def remove_device(self, device_id):
        if device_id not in self.devices:
            raise ValueError("Device ID not found")
        del self.devices[device_id]

    def update_device(self, device_id, name, ip_address):
        if device_id not in self.devices:
            raise ValueError("Device ID not found")
        self.devices[device_id].update_device(name, ip_address)

    def get_device(self, device_id):
        if device_id not in self.devices:
            raise ValueError("Device ID not found")
        return self.devices[device_id]

    def list_devices(self):
        return [str(device) for device in self.devices.values()]
