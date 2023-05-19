# Path: /src/main.py
# Description: Main entry point for the application
# Import necessary modules
import sys
import argparse

from src.loader import initialize_application
from src.ui.app import run as run_ui


def main(args):
    parser = argparse.ArgumentParser(description="VLANVision - A Network Management Software")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode")

    parsed_args = parser.parse_args(args)

    initialize_application()

    if parsed_args.debug:
        print("Debug mode enabled")

    run_ui()


if __name__ == "__main__":
    main(sys.argv[1:])
