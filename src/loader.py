# Path: /src/loader.py
# This file is responsible for initializing the application

import os
from dotenv import load_dotenv
from src.network import utils as network_utils
from src.security import utils as security_utils
from src.integration import utils as integration_utils


def initialize_application():
    """Initialize all components of the application."""
    # Load environment variables
    load_dotenv()
    
    # Initialize all components of the application
    network_utils.initialize_network()
    network_utils.initialize_hardware_inventory()
    network_utils.initialize_network_topology()
    security_utils.initialize_security()
    integration_utils.initialize_integrations()
