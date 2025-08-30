"""
Multi-Vendor Network Device Management
Provides unified interface for managing devices from different vendors.
"""

import re
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import paramiko
import telnetlib


class CommandType(Enum):
    """Types of vendor commands."""
    SHOW = "show"
    CONFIG = "config"
    OPERATIONAL = "operational"
    DIAGNOSTIC = "diagnostic"


@dataclass
class VendorCommand:
    """Represents a vendor-specific command."""
    name: str
    command: str
    command_type: CommandType
    requires_enable: bool = False
    output_parser: Optional[Callable] = None
    timeout: int = 10


class VendorAdapter(ABC):
    """Abstract base class for vendor-specific adapters."""
    
    def __init__(self, hostname: str, credentials: Dict[str, str]):
        self.hostname = hostname
        self.credentials = credentials
        self.connection = None
        self.vendor_name = "Generic"
    
    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to device."""
        pass
    
    @abstractmethod
    def disconnect(self):
        """Close connection to device."""
        pass
    
    @abstractmethod
    def execute_command(self, command: str, timeout: int = 10) -> str:
        """Execute a command and return output."""
        pass
    
    @abstractmethod
    def enter_config_mode(self) -> bool:
        """Enter configuration mode."""
        pass
    
    @abstractmethod
    def exit_config_mode(self) -> bool:
        """Exit configuration mode."""
        pass
    
    @abstractmethod
    def save_config(self) -> bool:
        """Save running configuration to startup."""
        pass


class CiscoAdapter(VendorAdapter):
    """Adapter for Cisco devices (IOS/IOS-XE/NX-OS)."""
    
    def __init__(self, hostname: str, credentials: Dict[str, str]):
        super().__init__(hostname, credentials)
        self.vendor_name = "Cisco"
        self.prompt_regex = r'[\w\-]+[>#]'
        
        # Cisco-specific commands
        self.commands = {
            'show_version': VendorCommand(
                name='show_version',
                command='show version',
                command_type=CommandType.SHOW,
                output_parser=self._parse_version
            ),
            'show_interfaces': VendorCommand(
                name='show_interfaces',
                command='show ip interface brief',
                command_type=CommandType.SHOW,
                output_parser=self._parse_interfaces
            ),
            'show_vlans': VendorCommand(
                name='show_vlans',
                command='show vlan brief',
                command_type=CommandType.SHOW,
                output_parser=self._parse_vlans
            ),
            'show_routing': VendorCommand(
                name='show_routing',
                command='show ip route',
                command_type=CommandType.SHOW,
                requires_enable=True
            ),
            'show_cdp': VendorCommand(
                name='show_cdp',
                command='show cdp neighbors detail',
                command_type=CommandType.SHOW,
                output_parser=self._parse_cdp_neighbors
            ),
            'show_spanning_tree': VendorCommand(
                name='show_spanning_tree',
                command='show spanning-tree',
                command_type=CommandType.SHOW
            ),
            'show_mac_table': VendorCommand(
                name='show_mac_table',
                command='show mac address-table',
                command_type=CommandType.SHOW
            )
        }
    
    def connect(self) -> bool:
        """Connect to Cisco device via SSH."""
        try:
            self.connection = paramiko.SSHClient()
            self.connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            self.connection.connect(
                self.hostname,
                username=self.credentials.get('username'),
                password=self.credentials.get('password'),
                timeout=30,
                look_for_keys=False,
                allow_agent=False
            )
            
            # Open interactive shell
            self.shell = self.connection.invoke_shell()
            time.sleep(2)
            
            # Clear buffer
            self.shell.recv(65535)
            
            # Disable pagination
            self.shell.send('terminal length 0\n')
            time.sleep(1)
            self.shell.recv(65535)
            
            # Enter enable mode if credentials provided
            if self.credentials.get('enable_password'):
                self.shell.send('enable\n')
                time.sleep(1)
                output = self.shell.recv(65535).decode('utf-8')
                
                if 'password' in output.lower():
                    self.shell.send(self.credentials.get('enable_password') + '\n')
                    time.sleep(1)
                    self.shell.recv(65535)
            
            return True
            
        except Exception as e:
            print(f"Failed to connect to Cisco device {self.hostname}: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Cisco device."""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def execute_command(self, command: str, timeout: int = 10) -> str:
        """Execute command on Cisco device."""
        if not self.shell:
            raise Exception("Not connected to device")
        
        # Send command
        self.shell.send(command + '\n')
        time.sleep(2)
        
        # Collect output
        output = ""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.shell.recv_ready():
                chunk = self.shell.recv(65535).decode('utf-8', errors='ignore')
                output += chunk
                
                # Check if we've received the prompt
                if re.search(self.prompt_regex, chunk):
                    break
            
            time.sleep(0.5)
        
        return self._clean_output(output, command)
    
    def enter_config_mode(self) -> bool:
        """Enter Cisco configuration mode."""
        try:
            output = self.execute_command('configure terminal')
            return 'config' in output.lower()
        except:
            return False
    
    def exit_config_mode(self) -> bool:
        """Exit Cisco configuration mode."""
        try:
            output = self.execute_command('end')
            return True
        except:
            return False
    
    def save_config(self) -> bool:
        """Save Cisco configuration."""
        try:
            output = self.execute_command('write memory')
            return 'ok' in output.lower() or 'success' in output.lower()
        except:
            return False
    
    def _clean_output(self, output: str, command: str) -> str:
        """Clean command output."""
        lines = output.split('\n')
        cleaned = []
        
        for line in lines:
            # Skip command echo and prompts
            if command in line or re.match(self.prompt_regex, line):
                continue
            cleaned.append(line.rstrip())
        
        return '\n'.join(cleaned)
    
    def _parse_version(self, output: str) -> Dict[str, Any]:
        """Parse show version output."""
        info = {
            'vendor': 'Cisco',
            'model': '',
            'version': '',
            'serial': '',
            'uptime': ''
        }
        
        # Parse model
        model_match = re.search(r'cisco\s+(\S+)', output, re.IGNORECASE)
        if model_match:
            info['model'] = model_match.group(1)
        
        # Parse version
        version_match = re.search(r'Version\s+([^\s,]+)', output)
        if version_match:
            info['version'] = version_match.group(1)
        
        # Parse serial
        serial_match = re.search(r'Processor board ID\s+(\S+)', output)
        if serial_match:
            info['serial'] = serial_match.group(1)
        
        # Parse uptime
        uptime_match = re.search(r'uptime is\s+(.+)', output)
        if uptime_match:
            info['uptime'] = uptime_match.group(1)
        
        return info
    
    def _parse_interfaces(self, output: str) -> List[Dict[str, Any]]:
        """Parse interface status output."""
        interfaces = []
        
        for line in output.split('\n'):
            # Parse interface lines (e.g., "GigabitEthernet0/1  192.168.1.1  YES NVRAM  up  up")
            match = re.match(r'(\S+)\s+(\S+)\s+\S+\s+\S+\s+(\S+)\s+(\S+)', line)
            if match:
                interfaces.append({
                    'name': match.group(1),
                    'ip_address': match.group(2) if match.group(2) != 'unassigned' else None,
                    'status': match.group(3),
                    'protocol': match.group(4)
                })
        
        return interfaces
    
    def _parse_vlans(self, output: str) -> List[Dict[str, Any]]:
        """Parse VLAN output."""
        vlans = []
        
        for line in output.split('\n'):
            # Parse VLAN lines (e.g., "10   VLAN0010  active")
            match = re.match(r'(\d+)\s+(\S+)\s+(\S+)', line)
            if match:
                vlans.append({
                    'id': int(match.group(1)),
                    'name': match.group(2),
                    'status': match.group(3)
                })
        
        return vlans
    
    def _parse_cdp_neighbors(self, output: str) -> List[Dict[str, Any]]:
        """Parse CDP neighbors output."""
        neighbors = []
        current_neighbor = {}
        
        for line in output.split('\n'):
            # Device ID
            if line.startswith('Device ID:'):
                if current_neighbor:
                    neighbors.append(current_neighbor)
                current_neighbor = {'device_id': line.split(':', 1)[1].strip()}
            
            # IP address
            elif 'IP address:' in line:
                current_neighbor['ip_address'] = line.split(':', 1)[1].strip()
            
            # Platform
            elif 'Platform:' in line:
                platform = line.split(':', 1)[1].strip()
                current_neighbor['platform'] = platform.split(',')[0].strip()
            
            # Interface
            elif 'Interface:' in line:
                interfaces = line.split(':', 1)[1].strip()
                parts = interfaces.split(',')
                if len(parts) >= 2:
                    current_neighbor['local_interface'] = parts[0].strip()
                    current_neighbor['remote_interface'] = parts[1].replace('Port ID', '').strip()
        
        if current_neighbor:
            neighbors.append(current_neighbor)
        
        return neighbors


class JuniperAdapter(VendorAdapter):
    """Adapter for Juniper devices (Junos)."""
    
    def __init__(self, hostname: str, credentials: Dict[str, str]):
        super().__init__(hostname, credentials)
        self.vendor_name = "Juniper"
        self.prompt_regex = r'[\w\-]+[@>]'
        
        self.commands = {
            'show_version': VendorCommand(
                name='show_version',
                command='show version',
                command_type=CommandType.SHOW
            ),
            'show_interfaces': VendorCommand(
                name='show_interfaces',
                command='show interfaces terse',
                command_type=CommandType.SHOW
            ),
            'show_vlans': VendorCommand(
                name='show_vlans',
                command='show vlans',
                command_type=CommandType.SHOW
            ),
            'show_routing': VendorCommand(
                name='show_routing',
                command='show route',
                command_type=CommandType.SHOW
            ),
            'show_lldp': VendorCommand(
                name='show_lldp',
                command='show lldp neighbors',
                command_type=CommandType.SHOW
            )
        }
    
    def connect(self) -> bool:
        """Connect to Juniper device."""
        # Similar implementation to Cisco but with Junos-specific handling
        return super().connect()
    
    def disconnect(self):
        """Disconnect from Juniper device."""
        super().disconnect()
    
    def execute_command(self, command: str, timeout: int = 10) -> str:
        """Execute command on Juniper device."""
        # Junos-specific command execution
        return ""
    
    def enter_config_mode(self) -> bool:
        """Enter Junos configuration mode."""
        try:
            output = self.execute_command('configure')
            return True
        except:
            return False
    
    def exit_config_mode(self) -> bool:
        """Exit Junos configuration mode."""
        try:
            self.execute_command('commit')
            self.execute_command('exit')
            return True
        except:
            return False
    
    def save_config(self) -> bool:
        """Save Junos configuration."""
        try:
            output = self.execute_command('commit')
            return 'commit complete' in output.lower()
        except:
            return False


class AristaAdapter(VendorAdapter):
    """Adapter for Arista devices (EOS)."""
    
    def __init__(self, hostname: str, credentials: Dict[str, str]):
        super().__init__(hostname, credentials)
        self.vendor_name = "Arista"
        
        self.commands = {
            'show_version': VendorCommand(
                name='show_version',
                command='show version',
                command_type=CommandType.SHOW
            ),
            'show_interfaces': VendorCommand(
                name='show_interfaces',
                command='show interfaces status',
                command_type=CommandType.SHOW
            ),
            'show_vlans': VendorCommand(
                name='show_vlans',
                command='show vlan',
                command_type=CommandType.SHOW
            )
        }
    
    def connect(self) -> bool:
        """Connect to Arista device."""
        return super().connect()
    
    def disconnect(self):
        """Disconnect from Arista device."""
        super().disconnect()
    
    def execute_command(self, command: str, timeout: int = 10) -> str:
        """Execute command on Arista device."""
        return ""
    
    def enter_config_mode(self) -> bool:
        """Enter Arista configuration mode."""
        return False
    
    def exit_config_mode(self) -> bool:
        """Exit Arista configuration mode."""
        return False
    
    def save_config(self) -> bool:
        """Save Arista configuration."""
        return False


class MultiVendorManager:
    """Manages connections to devices from multiple vendors."""
    
    # Vendor detection patterns
    VENDOR_PATTERNS = {
        'cisco': ['cisco', 'ios', 'catalyst', 'nexus'],
        'juniper': ['juniper', 'junos', 'srx', 'mx', 'ex'],
        'arista': ['arista', 'eos'],
        'hp': ['hp', 'procurve', 'aruba'],
        'mikrotik': ['mikrotik', 'routeros'],
        'fortinet': ['fortinet', 'fortigate'],
        'paloalto': ['palo alto', 'pan-os']
    }
    
    # Adapter mapping
    VENDOR_ADAPTERS = {
        'cisco': CiscoAdapter,
        'juniper': JuniperAdapter,
        'arista': AristaAdapter
    }
    
    def __init__(self):
        self.adapters: Dict[str, VendorAdapter] = {}
    
    def detect_vendor(self, device_info: Dict[str, Any]) -> str:
        """Detect device vendor from device information."""
        # Check manufacturer field
        if 'manufacturer' in device_info:
            manufacturer_lower = device_info['manufacturer'].lower()
            for vendor, patterns in self.VENDOR_PATTERNS.items():
                if any(pattern in manufacturer_lower for pattern in patterns):
                    return vendor
        
        # Check system description
        if 'system_description' in device_info:
            desc_lower = device_info['system_description'].lower()
            for vendor, patterns in self.VENDOR_PATTERNS.items():
                if any(pattern in desc_lower for pattern in patterns):
                    return vendor
        
        # Check hostname patterns
        if 'hostname' in device_info:
            hostname_lower = device_info['hostname'].lower()
            if 'cisco' in hostname_lower or 'sw' in hostname_lower:
                return 'cisco'
            elif 'juniper' in hostname_lower or 'srx' in hostname_lower:
                return 'juniper'
        
        return 'generic'
    
    def get_adapter(self, hostname: str, vendor: str, 
                   credentials: Dict[str, str]) -> Optional[VendorAdapter]:
        """Get or create vendor adapter for device."""
        adapter_key = f"{hostname}_{vendor}"
        
        if adapter_key not in self.adapters:
            # Create new adapter
            adapter_class = self.VENDOR_ADAPTERS.get(vendor)
            if adapter_class:
                adapter = adapter_class(hostname, credentials)
                if adapter.connect():
                    self.adapters[adapter_key] = adapter
                else:
                    return None
            else:
                print(f"No adapter available for vendor: {vendor}")
                return None
        
        return self.adapters.get(adapter_key)
    
    def execute_command(self, hostname: str, vendor: str, command: str,
                       credentials: Dict[str, str]) -> Optional[str]:
        """Execute command on device."""
        adapter = self.get_adapter(hostname, vendor, credentials)
        if adapter:
            return adapter.execute_command(command)
        return None
    
    def get_device_info(self, hostname: str, vendor: str,
                       credentials: Dict[str, str]) -> Dict[str, Any]:
        """Get comprehensive device information."""
        adapter = self.get_adapter(hostname, vendor, credentials)
        if not adapter:
            return {}
        
        info = {
            'hostname': hostname,
            'vendor': vendor
        }
        
        # Get version info
        if hasattr(adapter, 'commands') and 'show_version' in adapter.commands:
            version_output = adapter.execute_command(adapter.commands['show_version'].command)
            if version_output and adapter.commands['show_version'].output_parser:
                info['version_info'] = adapter.commands['show_version'].output_parser(version_output)
        
        # Get interfaces
        if hasattr(adapter, 'commands') and 'show_interfaces' in adapter.commands:
            interface_output = adapter.execute_command(adapter.commands['show_interfaces'].command)
            if interface_output and adapter.commands['show_interfaces'].output_parser:
                info['interfaces'] = adapter.commands['show_interfaces'].output_parser(interface_output)
        
        # Get VLANs
        if hasattr(adapter, 'commands') and 'show_vlans' in adapter.commands:
            vlan_output = adapter.execute_command(adapter.commands['show_vlans'].command)
            if vlan_output and adapter.commands['show_vlans'].output_parser:
                info['vlans'] = adapter.commands['show_vlans'].output_parser(vlan_output)
        
        return info
    
    def configure_vlan(self, hostname: str, vendor: str, vlan_id: int,
                      vlan_name: str, credentials: Dict[str, str]) -> bool:
        """Configure VLAN on device."""
        adapter = self.get_adapter(hostname, vendor, credentials)
        if not adapter:
            return False
        
        try:
            # Enter config mode
            if not adapter.enter_config_mode():
                return False
            
            # Configure VLAN based on vendor
            if vendor == 'cisco':
                adapter.execute_command(f'vlan {vlan_id}')
                adapter.execute_command(f'name {vlan_name}')
                adapter.execute_command('exit')
            elif vendor == 'juniper':
                adapter.execute_command(f'set vlans {vlan_name} vlan-id {vlan_id}')
            elif vendor == 'arista':
                adapter.execute_command(f'vlan {vlan_id}')
                adapter.execute_command(f'name {vlan_name}')
            
            # Exit config mode and save
            adapter.exit_config_mode()
            return adapter.save_config()
            
        except Exception as e:
            print(f"Failed to configure VLAN: {e}")
            return False
    
    def close_all_connections(self):
        """Close all open connections."""
        for adapter in self.adapters.values():
            adapter.disconnect()
        self.adapters.clear()


# Global instance
multi_vendor_manager = MultiVendorManager()