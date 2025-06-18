# Network discovery module using SNMP and other protocols
import ipaddress
import socket
import threading
import time
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime

from pysnmp.hlapi import *
from scapy.all import ARP, Ether, srp
import paramiko

from src.database import db, Device, VLAN


@dataclass
class DiscoveredDevice:
    """Represents a discovered network device."""
    ip_address: str
    mac_address: Optional[str] = None
    hostname: Optional[str] = None
    device_type: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    system_description: Optional[str] = None
    location: Optional[str] = None
    uptime: Optional[int] = None
    interfaces: List[Dict[str, Any]] = None
    vlans: List[int] = None
    
    def __post_init__(self):
        if self.interfaces is None:
            self.interfaces = []
        if self.vlans is None:
            self.vlans = []


class NetworkDiscovery:
    """Handles network device discovery using multiple protocols."""
    
    # SNMP OIDs
    OID_SYSNAME = '1.3.6.1.2.1.1.5.0'
    OID_SYSDESCR = '1.3.6.1.2.1.1.1.0'
    OID_SYSOBJECTID = '1.3.6.1.2.1.1.2.0'
    OID_SYSLOCATION = '1.3.6.1.2.1.1.6.0'
    OID_SYSUPTIME = '1.3.6.1.2.1.1.3.0'
    OID_INTERFACES = '1.3.6.1.2.1.2.2.1'
    OID_VLAN_TABLE = '1.3.6.1.4.1.9.9.46.1.3.1.1.2'
    
    # Known device patterns
    DEVICE_PATTERNS = {
        'cisco': ['Cisco', 'IOS', 'Catalyst'],
        'juniper': ['Juniper', 'JUNOS'],
        'arista': ['Arista', 'EOS'],
        'hp': ['HP', 'ProCurve', 'Aruba'],
        'dell': ['Dell', 'Force10'],
        'mikrotik': ['MikroTik', 'RouterOS'],
    }
    
    def __init__(self, snmp_community: str = 'public', snmp_port: int = 161):
        self.snmp_community = snmp_community
        self.snmp_port = snmp_port
        self.discovered_devices = []
        
    def discover_network(self, network_range: str, max_workers: int = 50) -> List[DiscoveredDevice]:
        """
        Discover devices on the specified network range.
        
        Args:
            network_range: Network range in CIDR notation (e.g., '192.168.1.0/24')
            max_workers: Maximum number of concurrent discovery threads
            
        Returns:
            List of discovered devices
        """
        print(f"Starting network discovery for {network_range}")
        
        # Parse network range
        try:
            network = ipaddress.ip_network(network_range, strict=False)
        except ValueError as e:
            raise ValueError(f"Invalid network range: {e}")
        
        # First, do ARP scan for quick discovery
        live_hosts = self._arp_scan(str(network))
        print(f"Found {len(live_hosts)} live hosts via ARP scan")
        
        # Then do detailed discovery on live hosts
        discovered = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._discover_device, host['ip'], host.get('mac')): host 
                for host in live_hosts
            }
            
            for future in as_completed(futures):
                try:
                    device = future.result(timeout=10)
                    if device:
                        discovered.append(device)
                        print(f"Discovered: {device.ip_address} - {device.hostname or 'Unknown'}")
                except Exception as e:
                    host = futures[future]
                    print(f"Error discovering {host['ip']}: {e}")
        
        self.discovered_devices = discovered
        return discovered
    
    def _arp_scan(self, network: str) -> List[Dict[str, str]]:
        """Perform ARP scan to find live hosts."""
        live_hosts = []
        
        try:
            # Create ARP request
            arp_request = ARP(pdst=network)
            broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
            arp_request_broadcast = broadcast / arp_request
            
            # Send request and receive response
            answered_list = srp(arp_request_broadcast, timeout=2, verbose=False, retry=1)[0]
            
            for sent, received in answered_list:
                live_hosts.append({
                    'ip': received.psrc,
                    'mac': received.hwsrc
                })
        except Exception as e:
            print(f"ARP scan failed: {e}")
            # Fallback to ping scan
            network_obj = ipaddress.ip_network(network, strict=False)
            for ip in network_obj.hosts():
                if self._is_host_alive(str(ip)):
                    live_hosts.append({'ip': str(ip), 'mac': None})
        
        return live_hosts
    
    def _is_host_alive(self, ip: str) -> bool:
        """Check if host is alive using socket connection."""
        common_ports = [22, 23, 80, 443, 161]
        
        for port in common_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                result = sock.connect_ex((ip, port))
                sock.close()
                if result == 0:
                    return True
            except:
                pass
        
        return False
    
    def _discover_device(self, ip: str, mac: str = None) -> Optional[DiscoveredDevice]:
        """Discover device details using SNMP and other protocols."""
        device = DiscoveredDevice(ip_address=ip, mac_address=mac)
        
        # Try SNMP discovery
        snmp_data = self._snmp_discovery(ip)
        if snmp_data:
            device.hostname = snmp_data.get('hostname')
            device.system_description = snmp_data.get('description')
            device.location = snmp_data.get('location')
            device.uptime = snmp_data.get('uptime')
            device.interfaces = snmp_data.get('interfaces', [])
            device.vlans = snmp_data.get('vlans', [])
            
            # Determine device type and manufacturer
            device.device_type, device.manufacturer = self._identify_device(
                snmp_data.get('description', ''),
                snmp_data.get('object_id', '')
            )
        
        # If SNMP fails, try other methods
        if not device.hostname:
            device.hostname = self._get_hostname_dns(ip)
        
        if not device.device_type:
            device.device_type = self._identify_device_by_services(ip)
        
        return device
    
    def _snmp_discovery(self, ip: str) -> Optional[Dict[str, Any]]:
        """Discover device information using SNMP."""
        try:
            data = {}
            
            # Get basic system information
            for oid, key in [
                (self.OID_SYSNAME, 'hostname'),
                (self.OID_SYSDESCR, 'description'),
                (self.OID_SYSOBJECTID, 'object_id'),
                (self.OID_SYSLOCATION, 'location'),
                (self.OID_SYSUPTIME, 'uptime')
            ]:
                result = self._snmp_get(ip, oid)
                if result:
                    data[key] = result
            
            # Get interfaces
            data['interfaces'] = self._get_interfaces_snmp(ip)
            
            # Get VLANs (Cisco-specific, but try anyway)
            data['vlans'] = self._get_vlans_snmp(ip)
            
            return data
        except Exception as e:
            print(f"SNMP discovery failed for {ip}: {e}")
            return None
    
    def _snmp_get(self, ip: str, oid: str) -> Optional[str]:
        """Perform SNMP GET operation."""
        try:
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(self.snmp_community),
                UdpTransportTarget((ip, self.snmp_port), timeout=2, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(oid))
            )
            
            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            
            if errorIndication or errorStatus:
                return None
            
            for varBind in varBinds:
                return str(varBind[1])
        except:
            return None
    
    def _get_interfaces_snmp(self, ip: str) -> List[Dict[str, Any]]:
        """Get network interfaces via SNMP."""
        interfaces = []
        
        try:
            # Get interface names
            for (errorIndication, errorStatus, errorIndex, varBinds) in nextCmd(
                SnmpEngine(),
                CommunityData(self.snmp_community),
                UdpTransportTarget((ip, self.snmp_port), timeout=2, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(self.OID_INTERFACES + '.2')),  # ifDescr
                lexicographicMode=False
            ):
                if errorIndication or errorStatus:
                    break
                
                for varBind in varBinds:
                    oid_parts = str(varBind[0]).split('.')
                    if_index = oid_parts[-1]
                    if_name = str(varBind[1])
                    
                    interfaces.append({
                        'index': if_index,
                        'name': if_name,
                        'status': 'unknown'
                    })
        except:
            pass
        
        return interfaces
    
    def _get_vlans_snmp(self, ip: str) -> List[int]:
        """Get VLANs via SNMP (Cisco-specific)."""
        vlans = []
        
        try:
            for (errorIndication, errorStatus, errorIndex, varBinds) in nextCmd(
                SnmpEngine(),
                CommunityData(self.snmp_community),
                UdpTransportTarget((ip, self.snmp_port), timeout=2, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(self.OID_VLAN_TABLE)),
                lexicographicMode=False
            ):
                if errorIndication or errorStatus:
                    break
                
                for varBind in varBinds:
                    oid_parts = str(varBind[0]).split('.')
                    if len(oid_parts) > 0:
                        vlan_id = int(oid_parts[-1])
                        if 1 <= vlan_id <= 4094:
                            vlans.append(vlan_id)
        except:
            pass
        
        return list(set(vlans))
    
    def _identify_device(self, description: str, object_id: str) -> tuple[str, str]:
        """Identify device type and manufacturer from SNMP data."""
        description_lower = description.lower()
        
        for manufacturer, patterns in self.DEVICE_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in description_lower:
                    # Determine device type
                    if any(x in description_lower for x in ['switch', 'catalyst']):
                        device_type = 'switch'
                    elif any(x in description_lower for x in ['router', 'ios xr']):
                        device_type = 'router'
                    elif any(x in description_lower for x in ['firewall', 'asa', 'pix']):
                        device_type = 'firewall'
                    elif any(x in description_lower for x in ['access point', 'ap']):
                        device_type = 'access_point'
                    else:
                        device_type = 'network_device'
                    
                    return device_type, manufacturer.title()
        
        return 'unknown', 'unknown'
    
    def _get_hostname_dns(self, ip: str) -> Optional[str]:
        """Get hostname via reverse DNS lookup."""
        try:
            return socket.gethostbyaddr(ip)[0]
        except:
            return None
    
    def _identify_device_by_services(self, ip: str) -> str:
        """Identify device type by open services."""
        service_map = {
            22: 'ssh_device',
            23: 'telnet_device',
            80: 'web_device',
            443: 'web_device',
            3389: 'windows_device',
            445: 'windows_device',
            548: 'mac_device',
        }
        
        for port, device_type in service_map.items():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                result = sock.connect_ex((ip, port))
                sock.close()
                if result == 0:
                    return device_type
            except:
                pass
        
        return 'unknown'
    
    def save_to_database(self) -> int:
        """Save discovered devices to database."""
        saved_count = 0
        
        for discovered in self.discovered_devices:
            # Check if device already exists
            device = Device.query.filter_by(ip_address=discovered.ip_address).first()
            
            if not device:
                device = Device(
                    ip_address=discovered.ip_address,
                    hostname=discovered.hostname or f"device-{discovered.ip_address}",
                    mac_address=discovered.mac_address,
                    device_type=discovered.device_type,
                    manufacturer=discovered.manufacturer,
                    model=discovered.model,
                    location=discovered.location,
                    status='active',
                    last_seen=datetime.utcnow()
                )
                db.session.add(device)
                saved_count += 1
            else:
                # Update existing device
                device.last_seen = datetime.utcnow()
                device.status = 'active'
                if discovered.hostname:
                    device.hostname = discovered.hostname
                if discovered.mac_address:
                    device.mac_address = discovered.mac_address
                if discovered.device_type:
                    device.device_type = discovered.device_type
                if discovered.manufacturer:
                    device.manufacturer = discovered.manufacturer
                if discovered.location:
                    device.location = discovered.location
            
            db.session.commit()
        
        return saved_count