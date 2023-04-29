# # Path: /src/integration/node_red.py
# # This is the class for node_red
import requests


class NodeRedIntegration:
    def __init__(self, node_red_url, api_key):
        self.node_red_url = node_red_url
        self.api_key = api_key
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def get_flows(self):
        """Get all flows from Node-RED."""
        response = requests.get(
            f'{self.node_red_url}/flows',
            headers=self.headers
        )
        return response.json()

    def deploy_flow(self, flow_data):
        """Deploy a new flow or update an existing flow in Node-RED."""
        response = requests.post(
            f'{self.node_red_url}/flows',
            json=flow_data,
            headers=self.headers
        )
        return response.json()

    def delete_flow(self, flow_id):
        """Delete a flow from Node-RED by flow ID."""
        response = requests.delete(
            f'{self.node_red_url}/flows/{flow_id}',
            headers=self.headers
        )
        return response.json()

    def get_flow(self, flow_id):
        """Get a flow from Node-RED by flow ID."""
        response = requests.get(
            f'{self.node_red_url}/flows/{flow_id}',
            headers=self.headers
        )
        return response.json()
