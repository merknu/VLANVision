# Path: /src/network/utils.py
# This is the class for utils functions for network management system
import json
import os
import socket

from src.network.hardware import HardwareInventory


# Helper function to resolve the absolute path of a file
def resolve_file_path(relative_path):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, relative_path)


# Helper function to safely parse JSON data from a file
def safe_json_load(file_path):
    try:
        with open(file_path, 'r') as config_file:
            return json.load(config_file)
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON format in {file_path}")
    except PermissionError:
        raise PermissionError(f"Permission denied when accessing {file_path}")


def load_configuration(file_path: str) -> dict:  # Added type hints
    config_file_path = resolve_file_path(file_path)

    if not os.path.exists(config_file_path):
        raise FileNotFoundError(f"Configuration file not found: {config_file_path}")

    config_data = safe_json_load(config_file_path)

    return config_data


# Helper function to load network configuration with a default 'network' key if missing

# Helper function to load network configuration with a default 'network' key if missing
# and provides specific error handling.
def load_network_config(file_path='network_config.conf'):
    try:
        # Load the configuration data from the specified file path
        config_data = load_configuration(file_path)
    except Exception as e:
        raise ValueError(f"Failed to load network configuration: {e}")

    # Ensure that a 'network' key exists in the configuration data
    if 'network' not in config_data:
        config_data['network'] = {}

    return config_data


def initialize_network():
    try:
        config_data = load_network_config()
    except Exception as e:
        raise ValueError(f"Failed to load network configuration: {e}")

    network = {}
    for key, value in config_data['network'].items():
        network[key] = value

    return network


# Function to initialize the hardware inventory based on the configuration data
# Includes specific error handling and additional comments for clarity.
def initialize_hardware_inventory():
    try:
        # Load the configuration data from a predefined file path
        config_data = load_configuration('network_config.conf')
    except Exception as e:
        raise ValueError(f"Failed to load network configuration: {e}")

    # Initialize an empty hardware inventory
    hardware_inventory = HardwareInventory()

    try:
        # Populate the hardware inventory based on the loaded configuration data
        for hardware in config_data['hardware_inventory']:
            hardware_inventory.add_hardware(hardware['id'], hardware['model'], hardware['manufacturer'],
                                            hardware['serial_number'], hardware['firmware_version'])
    except KeyError:
        # Handle missing keys in the configuration data
        raise ValueError("Missing keys in the configuration data. Failed to initialize the hardware inventory.")

    return hardware_inventory


# Function to initialize the network topology based on the configuration data
# Includes specific error handling and additional comments for clarity.
def initialize_network_topology():
    try:
        # Load the configuration data from a predefined file path
        config_data = load_configuration('network_config.conf')
    except Exception as e:
        raise ValueError(f"Failed to load network configuration: {e}")

    # Initialize an empty network topology
    network_topology = {}

    try:
        # Populate the network topology based on the loaded configuration data
        # The network topology is represented as a dictionary where keys are node names
        # and values are lists of connected nodes.
        for key, value in config_data['network_topology'].items():
            network_topology[key] = value
    except KeyError:
        # Handle missing keys in the configuration data
        raise ValueError("Missing keys in the configuration data. Failed to initialize the network topology.")

    return network_topology


# Function to save configuration data to a specified file path.
# Includes error handling for file IO and JSON serialization.
def save_configuration(file_path, config_data):
    try:
        # Open the file in write mode
        with open(file_path, 'w') as config_file:
            # Dump the configuration data as a JSON object
            json.dump(config_data, config_file, indent=2)
    except (FileNotFoundError, PermissionError):
        raise ValueError("Failed to open the configuration file for writing.")
    except json.JSONDecodeError:
        raise ValueError("Failed to serialize the configuration data.")


# Function to validate an IP address format
# Includes error handling for incorrect formats
def validate_ip_address(ip):
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False


# Function to calculate the network address of a subnet given an IP address and a subnet mask
# Includes error handling for incorrect formats
def calculate_subnet(ip, mask):
    try:
        ip_parts = [int(part) for part in ip.split('.')]
        mask_parts = [int(part) for part in mask.split('.')]
        subnet_parts = [ip & mask for ip, mask in zip(ip_parts, mask_parts)]
        return '.'.join(map(str, subnet_parts))
    except ValueError:
        raise ValueError("Invalid IP address or mask format.")


# Function to validate a CIDR notation
# Includes error handling for incorrect formats
def validate_cidr(cidr):
    try:
        ip, prefix = cidr.split('/')
        return validate_ip_address(ip) and 0 <= int(prefix) <= 32
    except ValueError:
        return False
