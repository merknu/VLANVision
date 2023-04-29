# Path: /src/network/vlan.py
# This is the class for vlan
class VLAN:
    def __init__(self, vlan_id, name, description):
        self.vlan_id = vlan_id
        self.name = name
        self.description = description
        self.devices = []

    def add_device(self, device):
        self.devices.append(device)

    def remove_device(self, device):
        self.devices.remove(device)

    def update_vlan(self, name, description):
        self.name = name
        self.description = description

    def __str__(self):
        return f"VLAN ID: {self.vlan_id}, Name: {self.name}, Description: {self.description}"


class VLANManager:
    def __init__(self):
        self.vlans = {}

    def create_vlan(self, vlan_id, name, description):
        if vlan_id in self.vlans:
            raise ValueError("VLAN ID already exists")
        self.vlans[vlan_id] = VLAN(vlan_id, name, description)

    def delete_vlan(self, vlan_id):
        if vlan_id not in self.vlans:
            raise ValueError("VLAN ID not found")
        del self.vlans[vlan_id]

    def update_vlan(self, vlan_id, name, description):
        if vlan_id not in self.vlans:
            raise ValueError("VLAN ID not found")
        self.vlans[vlan_id].update_vlan(name, description)

    def get_vlan(self, vlan_id):
        if vlan_id not in self.vlans:
            raise ValueError("VLAN ID not found")
        return self.vlans[vlan_id]

    def list_vlans(self):
        return [str(vlan) for vlan in self.vlans.values()]
