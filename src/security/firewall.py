# Path: /src/security/firewall.py
# This is the class for firewall rule and firewall manager class
import json


class FirewallRule:
    def __init__(self, src_ip, dest_ip, src_port, dest_port, protocol, action):
        self.src_ip = src_ip
        self.dest_ip = dest_ip
        self.src_port = src_port
        self.dest_port = dest_port
        self.protocol = protocol
        self.action = action

    def to_dict(self):
        return {
            'src_ip': self.src_ip,
            'dest_ip': self.dest_ip,
            'src_port': self.src_port,
            'dest_port': self.dest_port,
            'protocol': self.protocol,
            'action': self.action
        }

    @staticmethod
    def from_dict(rule_data):
        return FirewallRule(
            rule_data['src_ip'],
            rule_data['dest_ip'],
            rule_data['src_port'],
            rule_data['dest_port'],
            rule_data['protocol'],
            rule_data['action']
        )


class FirewallManager:
    def __init__(self, firewall_data_file):
        self.firewall_data_file = firewall_data_file
        self.rules = self.load_rules()

    def load_rules(self):
        try:
            with open(self.firewall_data_file, 'r') as file:
                firewall_data = json.load(file)
        except FileNotFoundError:
            firewall_data = []

        rules = []
        for rule_dict in firewall_data:
            rule = FirewallRule.from_dict(rule_dict)
            rules.append(rule)

        return rules

    def save_rules(self):
        firewall_data = [rule.to_dict() for rule in self.rules]
        with open(self.firewall_data_file, 'w') as file:
            json.dump(firewall_data, file, indent=2)

    def add_rule(self, src_ip, dest_ip, src_port, dest_port, protocol, action):
        rule = FirewallRule(src_ip, dest_ip, src_port, dest_port, protocol, action)
        self.rules.append(rule)
        self.save_rules()

    def remove_rule(self, index):
        if 0 <= index < len(self.rules):
            del self.rules[index]
            self.save_rules()
        else:
            raise ValueError(f"Invalid rule index. Valid indices are from 0 to {len(self.rules) - 1}.")
