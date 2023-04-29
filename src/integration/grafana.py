# Path: /src/integration/grafana.py
# This is the class for grafana integration class for creating, updating, deleting and listing dashboards
# in Grafana.
import requests


class GrafanaIntegration:
    def __init__(self, grafana_url, api_key):
        self.grafana_url = grafana_url
        self.api_key = api_key
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def create_dashboard(self, dashboard_data):
        """Create a new dashboard in Grafana."""
        response = requests.post(
            f'{self.grafana_url}/api/dashboards/db',
            json=dashboard_data,
            headers=self.headers
        )
        return response.json()

    def update_dashboard(self, dashboard_data):
        """Update an existing dashboard in Grafana."""
        response = requests.put(
            f'{self.grafana_url}/api/dashboards/db',
            json=dashboard_data,
            headers=self.headers
        )
        return response.json()

    def delete_dashboard(self, dashboard_uid):
        """Delete a dashboard in Grafana by UID."""
        response = requests.delete(
            f'{self.grafana_url}/api/dashboards/uid/{dashboard_uid}',
            headers=self.headers
        )
        return response.json()

    def list_dashboards(self):
        """List all dashboards in Grafana."""
        response = requests.get(
            f'{self.grafana_url}/api/search',
            headers=self.headers
        )
        return response.json()

    def get_dashboard_by_uid(self, dashboard_uid):
        """Get a dashboard in Grafana by UID."""
        response = requests.get(
            f'{self.grafana_url}/api/dashboards/uid/{dashboard_uid}',
            headers=self.headers
        )
        return response.json()
