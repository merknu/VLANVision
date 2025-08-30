"""
Advanced Network Topology Mapper
Automatically discovers and maps network topology using CDP, LLDP, and MAC address tables.
"""

import json
import ipaddress
import networkx as nx
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re

from pysnmp.hlapi import *
from src.database import db, Device, VLAN


class LinkType(Enum):
    """Types of network links."""
    TRUNK = "trunk"
    ACCESS = "access"
    AGGREGATE = "aggregate"
    UPLINK = "uplink"
    CROSSCONNECT = "crossconnect"
    WIRELESS = "wireless"


class DeviceRole(Enum):
    """Network device roles in topology."""
    CORE = "core"
    DISTRIBUTION = "distribution"
    ACCESS = "access"
    EDGE = "edge"
    INTERNET = "internet"
    SERVER = "server"
    ENDPOINT = "endpoint"


@dataclass
class NetworkNode:
    """Represents a node in the network topology."""
    id: str
    ip_address: str
    hostname: str
    device_type: str
    role: DeviceRole
    vendor: Optional[str] = None
    model: Optional[str] = None
    location: Optional[str] = None
    vlans: List[int] = field(default_factory=list)
    interfaces: Dict[str, Any] = field(default_factory=dict)
    coordinates: Optional[Tuple[float, float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NetworkLink:
    """Represents a link between network nodes."""
    source_id: str
    target_id: str
    source_interface: str
    target_interface: str
    link_type: LinkType
    speed: Optional[int] = None  # Mbps
    vlans: List[int] = field(default_factory=list)
    utilization: Optional[float] = None  # Percentage
    status: str = "up"
    metadata: Dict[str, Any] = field(default_factory=dict)


class TopologyMapper:
    """Advanced network topology discovery and mapping."""
    
    # SNMP OIDs for topology discovery
    OID_CDP_CACHE = '1.3.6.1.4.1.9.9.23.1.2.1.1'  # Cisco CDP
    OID_LLDP_REM = '1.0.8802.1.1.2.1.4.1.1'      # LLDP neighbors
    OID_MAC_TABLE = '1.3.6.1.2.1.17.4.3.1.2'      # MAC address table
    OID_ARP_TABLE = '1.3.6.1.2.1.4.22.1.2'        # ARP table
    OID_STP_ROOT = '1.3.6.1.2.1.17.2.5.0'         # STP root bridge
    OID_IF_TABLE = '1.3.6.1.2.1.2.2.1'            # Interface table
    
    def __init__(self, snmp_community: str = 'public'):
        self.snmp_community = snmp_community
        self.nodes: Dict[str, NetworkNode] = {}
        self.links: List[NetworkLink] = []
        self.topology_graph = nx.Graph()
        self.discovered_macs: Dict[str, str] = {}  # MAC -> Device IP
        self.interface_mappings: Dict[str, Dict[str, str]] = {}  # Device -> Interface -> Connected Device
        
    def discover_topology(self, seed_devices: List[str]) -> Dict[str, Any]:
        """
        Discover network topology starting from seed devices.
        
        Args:
            seed_devices: List of IP addresses to start discovery from
            
        Returns:
            Dictionary containing topology data
        """
        print(f"Starting topology discovery from {len(seed_devices)} seed devices")
        
        discovered = set()
        to_discover = set(seed_devices)
        
        while to_discover:
            current_ip = to_discover.pop()
            if current_ip in discovered:
                continue
                
            print(f"Discovering device: {current_ip}")
            
            # Discover device details
            node = self._discover_device_node(current_ip)
            if node:
                self.nodes[node.id] = node
                discovered.add(current_ip)
                
                # Discover neighbors
                neighbors = self._discover_neighbors(current_ip)
                for neighbor_ip in neighbors:
                    if neighbor_ip not in discovered:
                        to_discover.add(neighbor_ip)
                
                # Discover links
                self._discover_device_links(current_ip)
        
        # Build topology graph
        self._build_topology_graph()
        
        # Analyze topology
        topology_data = self._analyze_topology()
        
        return topology_data
    
    def _discover_device_node(self, ip_address: str) -> Optional[NetworkNode]:
        """Discover details about a network device."""
        try:
            # Get basic device info via SNMP
            hostname = self._snmp_get(ip_address, '1.3.6.1.2.1.1.5.0') or f"device-{ip_address}"
            sys_descr = self._snmp_get(ip_address, '1.3.6.1.2.1.1.1.0') or ""
            location = self._snmp_get(ip_address, '1.3.6.1.2.1.1.6.0')
            
            # Determine device type and vendor
            device_type, vendor = self._identify_device_type(sys_descr)
            
            # Determine device role
            role = self._determine_device_role(hostname, device_type, ip_address)
            
            # Get VLANs
            vlans = self._get_device_vlans(ip_address)
            
            # Get interfaces
            interfaces = self._get_device_interfaces(ip_address)
            
            node = NetworkNode(
                id=ip_address,
                ip_address=ip_address,
                hostname=hostname,
                device_type=device_type,
                role=role,
                vendor=vendor,
                location=location,
                vlans=vlans,
                interfaces=interfaces
            )
            
            return node
            
        except Exception as e:
            print(f"Error discovering device {ip_address}: {e}")
            return None
    
    def _discover_neighbors(self, ip_address: str) -> List[str]:
        """Discover neighbor devices using CDP/LLDP."""
        neighbors = []
        
        # Try CDP first (Cisco)
        cdp_neighbors = self._get_cdp_neighbors(ip_address)
        neighbors.extend(cdp_neighbors)
        
        # Try LLDP (standard)
        lldp_neighbors = self._get_lldp_neighbors(ip_address)
        neighbors.extend(lldp_neighbors)
        
        # Fallback to MAC/ARP tables
        if not neighbors:
            mac_neighbors = self._get_mac_table_neighbors(ip_address)
            neighbors.extend(mac_neighbors)
        
        return list(set(neighbors))  # Remove duplicates
    
    def _get_cdp_neighbors(self, ip_address: str) -> List[str]:
        """Get CDP neighbors from a Cisco device."""
        neighbors = []
        
        try:
            # CDP neighbor table OID
            for (errorIndication, errorStatus, errorIndex, varBinds) in nextCmd(
                SnmpEngine(),
                CommunityData(self.snmp_community),
                UdpTransportTarget((ip_address, 161), timeout=2, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(self.OID_CDP_CACHE + '.4')),  # CDP neighbor addresses
                lexicographicMode=False
            ):
                if errorIndication or errorStatus:
                    break
                    
                for varBind in varBinds:
                    # Extract IP address from CDP cache
                    value = varBind[1]
                    if value:
                        # CDP stores IP as hex string
                        ip_hex = value.hex()
                        if len(ip_hex) >= 8:
                            ip_parts = [str(int(ip_hex[i:i+2], 16)) for i in range(0, 8, 2)]
                            neighbor_ip = '.'.join(ip_parts)
                            if self._is_valid_ip(neighbor_ip):
                                neighbors.append(neighbor_ip)
        except:
            pass
        
        return neighbors
    
    def _get_lldp_neighbors(self, ip_address: str) -> List[str]:
        """Get LLDP neighbors from a device."""
        neighbors = []
        
        try:
            # LLDP remote management address
            for (errorIndication, errorStatus, errorIndex, varBinds) in nextCmd(
                SnmpEngine(),
                CommunityData(self.snmp_community),
                UdpTransportTarget((ip_address, 161), timeout=2, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(self.OID_LLDP_REM + '.8')),  # Management address
                lexicographicMode=False
            ):
                if errorIndication or errorStatus:
                    break
                    
                for varBind in varBinds:
                    value = str(varBind[1])
                    if self._is_valid_ip(value):
                        neighbors.append(value)
        except:
            pass
        
        return neighbors
    
    def _get_mac_table_neighbors(self, ip_address: str) -> List[str]:
        """Get potential neighbors from MAC address table."""
        neighbors = []
        
        try:
            # Get ARP table to map MACs to IPs
            arp_table = {}
            for (errorIndication, errorStatus, errorIndex, varBinds) in nextCmd(
                SnmpEngine(),
                CommunityData(self.snmp_community),
                UdpTransportTarget((ip_address, 161), timeout=2, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(self.OID_ARP_TABLE)),
                lexicographicMode=False
            ):
                if errorIndication or errorStatus:
                    break
                    
                for varBind in varBinds:
                    # Parse ARP entry
                    oid_parts = str(varBind[0]).split('.')
                    if len(oid_parts) >= 4:
                        neighbor_ip = '.'.join(oid_parts[-4:])
                        if self._is_valid_ip(neighbor_ip):
                            neighbors.append(neighbor_ip)
        except:
            pass
        
        return neighbors[:10]  # Limit to prevent too many discoveries
    
    def _discover_device_links(self, ip_address: str):
        """Discover links from a device to its neighbors."""
        node = self.nodes.get(ip_address)
        if not node:
            return
        
        # Get CDP/LLDP link details
        cdp_links = self._get_cdp_link_details(ip_address)
        lldp_links = self._get_lldp_link_details(ip_address)
        
        # Process discovered links
        for link_info in cdp_links + lldp_links:
            if link_info['neighbor_ip'] in self.nodes:
                link = NetworkLink(
                    source_id=ip_address,
                    target_id=link_info['neighbor_ip'],
                    source_interface=link_info['local_interface'],
                    target_interface=link_info['remote_interface'],
                    link_type=self._determine_link_type(link_info),
                    speed=link_info.get('speed'),
                    vlans=link_info.get('vlans', [])
                )
                
                # Avoid duplicate links
                if not self._link_exists(link):
                    self.links.append(link)
    
    def _get_cdp_link_details(self, ip_address: str) -> List[Dict[str, Any]]:
        """Get detailed CDP link information."""
        links = []
        
        try:
            # Query multiple CDP cache entries for complete link info
            cache_entries = {}
            
            # Get neighbor device IDs
            for (errorIndication, errorStatus, errorIndex, varBinds) in nextCmd(
                SnmpEngine(),
                CommunityData(self.snmp_community),
                UdpTransportTarget((ip_address, 161), timeout=2, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(self.OID_CDP_CACHE + '.6')),  # Device ID
                lexicographicMode=False
            ):
                if not errorIndication and not errorStatus:
                    for varBind in varBinds:
                        oid = str(varBind[0])
                        index = oid.split('.')[-1]
                        if index not in cache_entries:
                            cache_entries[index] = {}
                        cache_entries[index]['device_id'] = str(varBind[1])
            
            # Build link information
            for index, entry in cache_entries.items():
                link_info = {
                    'neighbor_ip': entry.get('ip_address', ''),
                    'local_interface': entry.get('local_interface', f'if-{index}'),
                    'remote_interface': entry.get('remote_interface', ''),
                    'platform': entry.get('platform', ''),
                    'capabilities': entry.get('capabilities', '')
                }
                
                if link_info['neighbor_ip']:
                    links.append(link_info)
        
        except Exception as e:
            print(f"Error getting CDP details from {ip_address}: {e}")
        
        return links
    
    def _get_lldp_link_details(self, ip_address: str) -> List[Dict[str, Any]]:
        """Get detailed LLDP link information."""
        links = []
        
        # Similar to CDP but using LLDP MIB
        # Implementation would follow similar pattern
        
        return links
    
    def _determine_link_type(self, link_info: Dict[str, Any]) -> LinkType:
        """Determine the type of link based on interface and device information."""
        local_if = link_info.get('local_interface', '').lower()
        remote_if = link_info.get('remote_interface', '').lower()
        
        # Check for trunk indicators
        if 'trunk' in local_if or 'trunk' in remote_if:
            return LinkType.TRUNK
        
        # Check for uplink patterns
        if any(x in local_if for x in ['gi0/0', 'te', 'fo', 'uplink']):
            return LinkType.UPLINK
        
        # Check for aggregate links
        if 'po' in local_if or 'port-channel' in local_if:
            return LinkType.AGGREGATE
        
        # Default to access
        return LinkType.ACCESS
    
    def _get_device_vlans(self, ip_address: str) -> List[int]:
        """Get VLANs configured on a device."""
        vlans = []
        
        try:
            # Query VLAN table (Cisco-specific)
            vlan_oid = '1.3.6.1.4.1.9.9.46.1.3.1.1.2'
            
            for (errorIndication, errorStatus, errorIndex, varBinds) in nextCmd(
                SnmpEngine(),
                CommunityData(self.snmp_community),
                UdpTransportTarget((ip_address, 161), timeout=2, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(vlan_oid)),
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
        
        return sorted(set(vlans))
    
    def _get_device_interfaces(self, ip_address: str) -> Dict[str, Any]:
        """Get interface information from a device."""
        interfaces = {}
        
        try:
            # Get interface descriptions
            for (errorIndication, errorStatus, errorIndex, varBinds) in nextCmd(
                SnmpEngine(),
                CommunityData(self.snmp_community),
                UdpTransportTarget((ip_address, 161), timeout=2, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(self.OID_IF_TABLE + '.2')),  # ifDescr
                lexicographicMode=False
            ):
                if errorIndication or errorStatus:
                    break
                    
                for varBind in varBinds:
                    if_index = str(varBind[0]).split('.')[-1]
                    if_name = str(varBind[1])
                    
                    interfaces[if_name] = {
                        'index': if_index,
                        'status': 'unknown',
                        'speed': None,
                        'type': self._get_interface_type(if_name)
                    }
        except:
            pass
        
        return interfaces
    
    def _get_interface_type(self, interface_name: str) -> str:
        """Determine interface type from name."""
        name_lower = interface_name.lower()
        
        if any(x in name_lower for x in ['gi', 'gig', 'ethernet']):
            return 'ethernet'
        elif any(x in name_lower for x in ['fa', 'fast']):
            return 'fastethernet'
        elif any(x in name_lower for x in ['te', 'ten']):
            return 'tengigabit'
        elif 'vlan' in name_lower:
            return 'vlan'
        elif 'lo' in name_lower:
            return 'loopback'
        else:
            return 'unknown'
    
    def _identify_device_type(self, sys_description: str) -> Tuple[str, str]:
        """Identify device type and vendor from system description."""
        desc_lower = sys_description.lower()
        
        # Cisco devices
        if 'cisco' in desc_lower:
            if 'catalyst' in desc_lower or 'switch' in desc_lower:
                return 'switch', 'Cisco'
            elif 'router' in desc_lower or 'ios xr' in desc_lower:
                return 'router', 'Cisco'
            elif 'asa' in desc_lower or 'firewall' in desc_lower:
                return 'firewall', 'Cisco'
            elif 'access point' in desc_lower or 'ap' in desc_lower:
                return 'access_point', 'Cisco'
        
        # Juniper devices
        elif 'juniper' in desc_lower or 'junos' in desc_lower:
            if 'ex' in desc_lower:
                return 'switch', 'Juniper'
            elif 'mx' in desc_lower or 'srx' in desc_lower:
                return 'router', 'Juniper'
        
        # Arista devices
        elif 'arista' in desc_lower:
            return 'switch', 'Arista'
        
        # HP/Aruba devices
        elif 'hp' in desc_lower or 'aruba' in desc_lower:
            if 'switch' in desc_lower:
                return 'switch', 'HP'
            elif 'ap' in desc_lower:
                return 'access_point', 'HP'
        
        # Generic detection
        elif 'switch' in desc_lower:
            return 'switch', 'Unknown'
        elif 'router' in desc_lower:
            return 'router', 'Unknown'
        
        return 'network_device', 'Unknown'
    
    def _determine_device_role(self, hostname: str, device_type: str, ip_address: str) -> DeviceRole:
        """Determine the role of a device in the network topology."""
        hostname_lower = hostname.lower()
        
        # Check hostname patterns
        if any(x in hostname_lower for x in ['core', 'backbone']):
            return DeviceRole.CORE
        elif any(x in hostname_lower for x in ['dist', 'distribution']):
            return DeviceRole.DISTRIBUTION
        elif any(x in hostname_lower for x in ['access', 'acc']):
            return DeviceRole.ACCESS
        elif any(x in hostname_lower for x in ['edge', 'dmz', 'internet']):
            return DeviceRole.EDGE
        elif device_type == 'server':
            return DeviceRole.SERVER
        elif device_type in ['workstation', 'pc', 'laptop']:
            return DeviceRole.ENDPOINT
        
        # Default based on device type
        if device_type == 'router':
            return DeviceRole.EDGE
        elif device_type == 'switch':
            return DeviceRole.ACCESS
        
        return DeviceRole.ACCESS
    
    def _build_topology_graph(self):
        """Build NetworkX graph from discovered nodes and links."""
        # Add nodes
        for node_id, node in self.nodes.items():
            self.topology_graph.add_node(
                node_id,
                hostname=node.hostname,
                device_type=node.device_type,
                role=node.role.value,
                vendor=node.vendor,
                vlans=node.vlans
            )
        
        # Add edges
        for link in self.links:
            if link.source_id in self.nodes and link.target_id in self.nodes:
                self.topology_graph.add_edge(
                    link.source_id,
                    link.target_id,
                    link_type=link.link_type.value,
                    source_interface=link.source_interface,
                    target_interface=link.target_interface,
                    speed=link.speed
                )
    
    def _analyze_topology(self) -> Dict[str, Any]:
        """Analyze the discovered topology and generate insights."""
        analysis = {
            'summary': {
                'total_nodes': len(self.nodes),
                'total_links': len(self.links),
                'connected_components': nx.number_connected_components(self.topology_graph),
                'is_connected': nx.is_connected(self.topology_graph)
            },
            'node_distribution': {},
            'link_distribution': {},
            'critical_nodes': [],
            'redundancy_analysis': {},
            'vlan_distribution': {}
        }
        
        # Node distribution by role
        for node in self.nodes.values():
            role = node.role.value
            if role not in analysis['node_distribution']:
                analysis['node_distribution'][role] = 0
            analysis['node_distribution'][role] += 1
        
        # Link distribution by type
        for link in self.links:
            link_type = link.link_type.value
            if link_type not in analysis['link_distribution']:
                analysis['link_distribution'][link_type] = 0
            analysis['link_distribution'][link_type] += 1
        
        # Find critical nodes (high betweenness centrality)
        if len(self.nodes) > 0:
            centrality = nx.betweenness_centrality(self.topology_graph)
            sorted_centrality = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
            analysis['critical_nodes'] = [
                {
                    'node': self.nodes[node_id].hostname,
                    'ip': node_id,
                    'centrality': score
                }
                for node_id, score in sorted_centrality[:5]
            ]
        
        # Check redundancy
        analysis['redundancy_analysis'] = {
            'single_points_of_failure': self._find_single_points_of_failure(),
            'redundant_paths': self._check_redundant_paths()
        }
        
        # VLAN distribution
        vlan_counts = {}
        for node in self.nodes.values():
            for vlan in node.vlans:
                if vlan not in vlan_counts:
                    vlan_counts[vlan] = 0
                vlan_counts[vlan] += 1
        analysis['vlan_distribution'] = dict(sorted(vlan_counts.items()))
        
        return analysis
    
    def _find_single_points_of_failure(self) -> List[str]:
        """Find nodes whose failure would partition the network."""
        spof = []
        
        if nx.is_connected(self.topology_graph):
            # Find articulation points (cut vertices)
            articulation_points = list(nx.articulation_points(self.topology_graph))
            for node_id in articulation_points:
                if node_id in self.nodes:
                    spof.append(self.nodes[node_id].hostname)
        
        return spof
    
    def _check_redundant_paths(self) -> Dict[str, Any]:
        """Check for redundant paths between critical nodes."""
        redundancy = {
            'has_redundancy': False,
            'redundant_pairs': []
        }
        
        # Check paths between core nodes
        core_nodes = [n.id for n in self.nodes.values() if n.role == DeviceRole.CORE]
        
        for i, source in enumerate(core_nodes):
            for target in core_nodes[i+1:]:
                if source in self.topology_graph and target in self.topology_graph:
                    try:
                        paths = list(nx.edge_disjoint_paths(self.topology_graph, source, target))
                        if len(paths) > 1:
                            redundancy['has_redundancy'] = True
                            redundancy['redundant_pairs'].append({
                                'source': self.nodes[source].hostname,
                                'target': self.nodes[target].hostname,
                                'path_count': len(paths)
                            })
                    except:
                        pass
        
        return redundancy
    
    def _link_exists(self, new_link: NetworkLink) -> bool:
        """Check if a link already exists (bidirectional check)."""
        for existing_link in self.links:
            if ((existing_link.source_id == new_link.source_id and 
                 existing_link.target_id == new_link.target_id) or
                (existing_link.source_id == new_link.target_id and 
                 existing_link.target_id == new_link.source_id)):
                return True
        return False
    
    def _is_valid_ip(self, ip_string: str) -> bool:
        """Check if string is a valid IP address."""
        try:
            ipaddress.ip_address(ip_string)
            return True
        except ValueError:
            return False
    
    def _snmp_get(self, ip_address: str, oid: str) -> Optional[str]:
        """Perform SNMP GET operation."""
        try:
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(self.snmp_community),
                UdpTransportTarget((ip_address, 161), timeout=2, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(oid))
            )
            
            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            
            if not errorIndication and not errorStatus:
                for varBind in varBinds:
                    return str(varBind[1])
        except:
            pass
        
        return None
    
    def export_topology(self, format: str = 'json') -> str:
        """Export topology in various formats."""
        if format == 'json':
            export_data = {
                'nodes': [
                    {
                        'id': node.id,
                        'hostname': node.hostname,
                        'ip_address': node.ip_address,
                        'type': node.device_type,
                        'role': node.role.value,
                        'vendor': node.vendor,
                        'vlans': node.vlans,
                        'location': node.location
                    }
                    for node in self.nodes.values()
                ],
                'links': [
                    {
                        'source': link.source_id,
                        'target': link.target_id,
                        'source_interface': link.source_interface,
                        'target_interface': link.target_interface,
                        'type': link.link_type.value,
                        'speed': link.speed,
                        'vlans': link.vlans
                    }
                    for link in self.links
                ],
                'analysis': self._analyze_topology()
            }
            return json.dumps(export_data, indent=2)
        
        elif format == 'graphml':
            # Export as GraphML for visualization tools
            import io
            buffer = io.StringIO()
            nx.write_graphml(self.topology_graph, buffer)
            return buffer.getvalue()
        
        elif format == 'dot':
            # Export as Graphviz DOT format
            from networkx.drawing.nx_agraph import write_dot
            import io
            buffer = io.StringIO()
            write_dot(self.topology_graph, buffer)
            return buffer.getvalue()
        
        else:
            raise ValueError(f"Unsupported export format: {format}")