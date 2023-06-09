# Path: /src/network/utils.py
# This is the class for utils functions for network
import ipaddress
import json
import os

from hardware import HardwareInventory


def load_configuration(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Configuration file not found: {file_path}")

    with open(file_path, 'r') as config_file:
        config_data = json.load(config_file)

    return config_data


def initialize_network():
    # Load configuration data from a predefined file path
    config_data = load_configuration('network_config.conf')

    # Initialize the network based on the configuration data
    network = {}
    for key, value in config_data['network'].items():
        network[key] = value

    return network


def initialize_hardware_inventory():
    # Load configuration data from a predefined file path
    config_data = load_configuration('network_config.conf')

    # Initialize the hardware inventory based on the configuration data
    hardware_inventory = HardwareInventory()
    for hardware in config_data['hardware_inventory']:
        hardware_inventory.add_hardware(hardware['id'], hardware['model'], hardware['manufacturer'], hardware['serial_number'], hardware['firmware_version'])

    return hardware_inventory


def initialize_network_topology():
    # Load configuration data from a predefined file path
    config_data = load_configuration('network_config.conf')

    # Initialize the network topology based on the configuration data
    network_topology = {}
    for key, value in config_data['network_topology'].items():
        network_topology[key] = value

    return network_topology


def save_configuration(file_path, config_data):
    with open(file_path, 'w') as config_file:
        json.dump(config_data, config_file, indent=2)


def validate_ip_address(ip_address):
    try:
        parts = ip_address.split('.')
        if len(parts) != 4:
            return False

        for part in parts:
            if not 0 <= int(part) <= 255:
                return False
    except ValueError:
        return False

    return True


def calculate_subnet(ip_address, subnet_mask):
    ip_interface = ipaddress.ip_interface(f"{ip_address}/{subnet_mask}")
    return str(ip_interface.network.network_address)


def validate_cidr(cidr):
    try:
        if '/' not in cidr:
            return False

        ip, prefix = cidr.split('/')
        if not validate_ip_address(ip):
            return False

        if not 0 <= int(prefix) <= 32:
            return False
    except (ValueError, AttributeError):
        return False

    return True
