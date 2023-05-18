# Path: /tests/security_test.py
# This is the test file for the security module.
# It tests the functionality of the security module.
# It uses the unittest module to run the tests.
# It uses the mock module to mock the requests' module.
# It uses the pytest module to run the tests.
# It uses the pytest-cov module to generate a coverage report.
import os
import unittest
from src.security import user, firewall, intrusion, utils


class TestSecurity(unittest.TestCase):

    def setUp(self):
        self.user_manager = user.UserManager("test_user_data.json")

    def tearDown(self):
        # Clean up after tests by deleting the test user data file
        if os.path.exists("test_user_data.json"):
            os.remove("test_user_data.json")

    def test_add_user(self):
        username = "test_user"
        password = "test_password"
        role = "admin"
        self.user_manager.add_user(username, password, role)
        new_user = self.user_manager.users[username]
        self.assertEqual(new_user.username, username)
        self.assertTrue(new_user.verify_password(password))
        self.assertEqual(new_user.role, role)

    def test_add_firewall_rule(self):
        source_ip = "192.168.1.1"
        destination_ip = "192.168.1.2"
        source_port = 80
        destination_port = 443
        protocol = "TCP"
        action = "ALLOW"
        firewall_manager = firewall.FirewallManager("test_firewall_data.json")
        firewall_manager.add_rule(source_ip, destination_ip, source_port, destination_port, protocol, action)
        new_rule = firewall_manager.rules[-1]  # get the last added rule
        self.assertEqual(new_rule.source_ip, source_ip)
        self.assertEqual(new_rule.destination_ip, destination_ip)
        self.assertEqual(new_rule.src_port, source_port)
        self.assertEqual(new_rule.dest_port, destination_port)
        self.assertEqual(new_rule.protocol, protocol)
        self.assertEqual(new_rule.action, action)

    def test_detect_intrusion(self):
        log_entry = "192.168.1.1 attempted unauthorized access"
        intrusion_detected = intrusion.detect_intrusion(log_entry)
        self.assertTrue(intrusion_detected)

    def test_analyze_logs(self):
        logs = ["192.168.1.1 attempted unauthorized access", "192.168.1.2 connected successfully"]
        expected_analysis = {
            "intrusions": 1,
            "successful_connections": 1
        }
        analyzed_logs = utils.analyze_logs(logs)
        self.assertEqual(analyzed_logs, expected_analysis)


if __name__ == '__main__':
    unittest.main()
