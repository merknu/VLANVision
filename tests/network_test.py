# Path: /tests/network_test.py
# This is the test file for the network module.
# It tests the functionality of the network module.
# It uses the unittest module to run the tests.
# It uses the mock module to mock the requests module.
# It uses the pytest module to run the tests.
# It uses the pytest-cov module to generate a coverage report.
import unittest
from src.network import vlan, topology, hardware, utils


class TestNetwork(unittest.TestCase):

    def test_create_vlan_creates_vlan_with_correct_id_and_name(self):
        vlan_id = 10
        name = "Test_VLAN"
        new_vlan = vlan.create_vlan(vlan_id, name)
        self.assertEqual(new_vlan.id, vlan_id)
        self.assertEqual(new_vlan.name, name)

    def test_add_device_to_topology(self):
        device_name = "Switch-01"
        device_type = "switch"
        new_device = topology.add_device(device_name, device_type)
        self.assertEqual(new_device.name, device_name)
        self.assertEqual(new_device.type, device_type)

    def test_add_port_to_device(self):
        device = hardware.Device("Switch-01", "switch")
        port_number = 1
        new_port = hardware.add_port_to_device(device, port_number)
        self.assertEqual(new_port.number, port_number)
        self.assertEqual(new_port.device, device)

    def test_calculate_subnet(self):
        ip_address = "192.168.1.1"
        subnet_mask = "255.255.255.0"
        expected_subnet = "192.168.1.0"
        calculated_subnet = utils.calculate_subnet(ip_address, subnet_mask)
        self.assertEqual(calculated_subnet, expected_subnet)


if __name__ == '__main__':
    unittest.main()
