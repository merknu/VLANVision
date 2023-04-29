# Path: /src/network/utils.py
# This is the class for utils functions for network
import json
import os


def load_configuration(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Configuration file not found: {file_path}")

    with open(file_path, 'r') as config_file:
        config_data = json.load(config_file)

    return config_data


def initialize_network():
    # Initialize network here
    pass


def initialize_hardware_inventory():
    # Initialize hardware inventory here
    pass


def initialize_network_topology():
    # Initialize network topology here
    pass


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
