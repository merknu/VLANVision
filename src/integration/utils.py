# Path: /src/integration/utils.py
# This is the class for utils for integration services
import requests
import json


# src/integration/utils.py
def load_integration_credentials(filename):
    """Load integration credentials from a JSON file."""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"No such file or directory: '{filename}'")
        return None
    except json.JSONDecodeError as jde:
        print(f"Invalid JSON file: {filename}. Error: {jde}")
        return None


def initialize_integrations():
    # Initialize integrations here
    pass


def check_integration_availability(url):
    """Check if the integration service is available by sending a request to the given URL."""
    try:
        response = requests.get(url)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def generate_dashboard_url(grafana_base_url, dashboard_id, variables=None):
    """Generate a Grafana dashboard URL with optional variables."""
    url = f'{grafana_base_url}/d/{dashboard_id}'
    if variables:
        url += '?' + '&'.join([f'var-{k}={v}' for k, v in variables.items()])
    return url
