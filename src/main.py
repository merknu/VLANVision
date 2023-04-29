# Path: /src/main.py
# Description: Main entry point for the application
# Import necessary modules
import sys
import argparse


from src.network import utils as network_utils
from src.security import utils as security_utils
from src.ui.app import run as run_ui
from src.integration import utils as integration_utils


def main(args):
    parser = argparse.ArgumentParser(description="VLANVision - A Network Management Software")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode")

    parsed_args = parser.parse_args(args)

    network_utils.initialize_network()
    network_utils.initialize_hardware_inventory()
    network_utils.initialize_network_topology()
    security_utils.initialize_security()
    integration_utils.initialize_integrations()

    if parsed_args.debug:
        print("Debug mode enabled")

    run_ui()


if __name__ == "__main__":
    main(sys.argv[1:])
