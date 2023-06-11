# Path: /src/network/hardware.py
# This is the class for hardware inventory management system
from typing import List


class Hardware:
    def __init__(self, model: str, manufacturer: str, serial_number: str, firmware_version: str):
        self.model = model
        self.manufacturer = manufacturer
        self.serial_number = serial_number
        self.firmware_version = firmware_version

    def update_firmware(self, firmware_version: str):
        self.firmware_version = firmware_version

    def __str__(self):
        return f"{self.manufacturer} {self.model}, Serial: {self.serial_number}, Firmware: {self.firmware_version}"


class HardwareInventory:
    def __init__(self):
        self.hardware_inventory = {}

    def add_hardware(self, hardware_id: str, model: str, manufacturer: str, serial_number: str, firmware_version: str):
        if not all([hardware_id, model, manufacturer, serial_number, firmware_version]):
            raise ValueError("All arguments must be provided and not be None")
        if hardware_id in self.hardware_inventory:
            raise ValueError("Hardware ID already exists")
        self.hardware_inventory[hardware_id] = Hardware(model, manufacturer, serial_number, firmware_version)

    def remove_hardware(self, hardware_id: str):
        if hardware_id not in self.hardware_inventory:
            raise ValueError("Hardware ID not found")
        del self.hardware_inventory[hardware_id]

    def update_hardware_firmware(self, hardware_id: str, firmware_version: str):
        if hardware_id not in self.hardware_inventory:
            raise ValueError("Hardware ID not found")
        self.hardware_inventory[hardware_id].update_firmware(firmware_version)

    def get_hardware(self, hardware_id: str) -> Hardware:
        if hardware_id not in self.hardware_inventory:
            raise ValueError("Hardware ID not found")
        return self.hardware_inventory[hardware_id]

    def list_hardware(self) -> List[str]:
        return [str(hardware) for hardware in self.hardware_inventory.values()]


class Port:
    def __init__(self, number: int, status: str = 'down'):
        self.number = number
        self.status = status


class Device(Hardware):
    def __init__(self, device_id: str, model: str, manufacturer: str, serial_number: str, firmware_version: str,
                 device_type: str, name: str, ip_address: str, mac_address: str):
        super().__init__(model, manufacturer, serial_number, firmware_version)
        self.device_id = device_id
        self.device_type = device_type
        self.name = name
        self.ip_address = ip_address
        self.mac_address = mac_address
        self.ports = []

    def add_port_to_device(self, port_number: int):
        self.ports.append(Port(port_number))

    def update_device(self, name: str, ip_address: str):
        self.name = name
        self.ip_address = ip_address
