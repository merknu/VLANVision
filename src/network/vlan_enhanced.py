"""
Enhanced VLAN Management Module
Provides advanced VLAN management capabilities including trunk configuration,
VLAN trunking protocol (VTP), and inter-VLAN routing support.
"""

import ipaddress
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from src.database import db, VLAN, Device


class VLANType(Enum):
    """VLAN types based on IEEE 802.1Q standard."""
    DEFAULT = "default"  # VLAN 1
    DATA = "data"       # Regular data VLANs
    VOICE = "voice"     # Voice VLANs for VoIP
    MANAGEMENT = "mgmt"  # Management VLANs
    NATIVE = "native"    # Native VLAN for trunk ports
    GUEST = "guest"      # Guest/isolated VLANs
    DMZ = "dmz"         # DMZ VLANs


@dataclass
class VLANConfig:
    """Extended VLAN configuration."""
    vlan_id: int
    name: str
    description: str
    vlan_type: VLANType = VLANType.DATA
    subnet: Optional[str] = None
    gateway: Optional[str] = None
    dhcp_enabled: bool = False
    dhcp_pool_start: Optional[str] = None
    dhcp_pool_end: Optional[str] = None
    qos_priority: int = 0  # 0-7, higher is better
    mtu: int = 1500
    is_private: bool = False
    acl_rules: List[Dict] = field(default_factory=list)


@dataclass
class TrunkPort:
    """Trunk port configuration."""
    port_name: str
    device_id: int
    allowed_vlans: List[int] = field(default_factory=list)
    native_vlan: int = 1
    mode: str = "trunk"  # trunk, access, dynamic
    encapsulation: str = "802.1q"  # 802.1q or ISL
    pruning_enabled: bool = True


class EnhancedVLANManager:
    """Enhanced VLAN manager with advanced features."""
    
    # Reserved VLAN IDs
    RESERVED_VLANS = {
        1: "default",
        1002: "fddi-default",
        1003: "token-ring-default",
        1004: "fddinet-default",
        1005: "trnet-default"
    }
    
    # Common VLAN ranges
    VLAN_RANGES = {
        "standard": (1, 1005),
        "extended": (1006, 4094),
        "reserved": (1002, 1005)
    }
    
    def __init__(self):
        self.trunk_ports: Dict[str, TrunkPort] = {}
        self.vlan_configs: Dict[int, VLANConfig] = {}
        self._load_vlan_configs()
    
    def _load_vlan_configs(self):
        """Load VLAN configurations from database."""
        vlans = VLAN.query.all()
        for vlan in vlans:
            # Parse extended config from description or metadata
            config = VLANConfig(
                vlan_id=vlan.vlan_id,
                name=vlan.name,
                description=vlan.description
            )
            self.vlan_configs[vlan.vlan_id] = config
    
    def create_vlan_with_config(self, config: VLANConfig) -> VLAN:
        """Create a VLAN with extended configuration."""
        # Validate VLAN ID
        if not self._validate_vlan_id(config.vlan_id):
            raise ValueError(f"Invalid VLAN ID: {config.vlan_id}")
        
        # Check if VLAN already exists
        existing = VLAN.query.filter_by(vlan_id=config.vlan_id).first()
        if existing:
            raise ValueError(f"VLAN {config.vlan_id} already exists")
        
        # Validate subnet if provided
        if config.subnet:
            try:
                network = ipaddress.ip_network(config.subnet, strict=False)
                if config.gateway:
                    gateway_ip = ipaddress.ip_address(config.gateway)
                    if gateway_ip not in network:
                        raise ValueError(f"Gateway {config.gateway} not in subnet {config.subnet}")
            except ValueError as e:
                raise ValueError(f"Invalid network configuration: {e}")
        
        # Create VLAN in database
        vlan = VLAN(
            vlan_id=config.vlan_id,
            name=config.name,
            description=config.description
        )
        
        db.session.add(vlan)
        db.session.commit()
        
        # Store extended configuration
        self.vlan_configs[config.vlan_id] = config
        
        return vlan
    
    def _validate_vlan_id(self, vlan_id: int) -> bool:
        """Validate VLAN ID according to IEEE 802.1Q."""
        if not isinstance(vlan_id, int):
            return False
        
        # Check if in valid range
        if not (1 <= vlan_id <= 4094):
            return False
        
        # Check if reserved
        if vlan_id in self.RESERVED_VLANS and vlan_id != 1:
            return False
        
        return True
    
    def create_vlan_range(self, start: int, end: int, prefix: str, vlan_type: VLANType) -> List[VLAN]:
        """Create a range of VLANs."""
        if start > end:
            raise ValueError("Start VLAN ID must be less than or equal to end VLAN ID")
        
        created_vlans = []
        for vlan_id in range(start, end + 1):
            if self._validate_vlan_id(vlan_id):
                try:
                    config = VLANConfig(
                        vlan_id=vlan_id,
                        name=f"{prefix}-{vlan_id}",
                        description=f"{vlan_type.value} VLAN {vlan_id}",
                        vlan_type=vlan_type
                    )
                    vlan = self.create_vlan_with_config(config)
                    created_vlans.append(vlan)
                except ValueError:
                    # Skip if VLAN already exists
                    continue
        
        return created_vlans
    
    def configure_trunk_port(self, device_id: int, port_name: str, 
                           allowed_vlans: List[int] = None,
                           native_vlan: int = 1) -> TrunkPort:
        """Configure a trunk port on a device."""
        device = Device.query.get(device_id)
        if not device:
            raise ValueError(f"Device {device_id} not found")
        
        # Validate allowed VLANs
        if allowed_vlans:
            for vlan_id in allowed_vlans:
                if not self._validate_vlan_id(vlan_id):
                    raise ValueError(f"Invalid VLAN ID in allowed list: {vlan_id}")
        else:
            # Allow all VLANs by default
            allowed_vlans = list(range(1, 4095))
        
        trunk = TrunkPort(
            port_name=port_name,
            device_id=device_id,
            allowed_vlans=allowed_vlans,
            native_vlan=native_vlan
        )
        
        self.trunk_ports[f"{device_id}:{port_name}"] = trunk
        return trunk
    
    def get_vlan_statistics(self, vlan_id: int) -> Dict[str, Any]:
        """Get detailed statistics for a VLAN."""
        vlan = VLAN.query.filter_by(vlan_id=vlan_id).first()
        if not vlan:
            raise ValueError(f"VLAN {vlan_id} not found")
        
        # Get device count
        device_count = len(vlan.devices)
        
        # Get VLAN configuration
        config = self.vlan_configs.get(vlan_id)
        
        # Calculate IP usage if subnet is configured
        ip_usage = None
        if config and config.subnet:
            try:
                network = ipaddress.ip_network(config.subnet, strict=False)
                total_ips = network.num_addresses - 2  # Exclude network and broadcast
                used_ips = device_count
                ip_usage = {
                    "total": total_ips,
                    "used": used_ips,
                    "available": total_ips - used_ips,
                    "utilization": (used_ips / total_ips * 100) if total_ips > 0 else 0
                }
            except:
                pass
        
        return {
            "vlan_id": vlan_id,
            "name": vlan.name,
            "description": vlan.description,
            "device_count": device_count,
            "type": config.vlan_type.value if config else "unknown",
            "subnet": config.subnet if config else None,
            "gateway": config.gateway if config else None,
            "ip_usage": ip_usage,
            "created_at": vlan.created_at.isoformat() if vlan.created_at else None,
            "updated_at": vlan.updated_at.isoformat() if vlan.updated_at else None
        }
    
    def get_vlan_topology(self) -> Dict[str, Any]:
        """Get VLAN topology showing inter-VLAN connections."""
        vlans = VLAN.query.all()
        devices = Device.query.all()
        
        topology = {
            "vlans": [],
            "devices": [],
            "connections": []
        }
        
        # Build VLAN nodes
        for vlan in vlans:
            config = self.vlan_configs.get(vlan.vlan_id)
            topology["vlans"].append({
                "id": f"vlan-{vlan.vlan_id}",
                "vlan_id": vlan.vlan_id,
                "name": vlan.name,
                "type": config.vlan_type.value if config else "data",
                "device_count": len(vlan.devices)
            })
        
        # Build device nodes and connections
        for device in devices:
            topology["devices"].append({
                "id": f"device-{device.id}",
                "hostname": device.hostname,
                "ip": device.ip_address,
                "type": device.device_type,
                "vlan_id": device.vlan_id
            })
            
            if device.vlan_id:
                topology["connections"].append({
                    "source": f"device-{device.id}",
                    "target": f"vlan-{device.vlan_id}",
                    "type": "access"
                })
        
        # Add trunk connections
        for trunk_key, trunk in self.trunk_ports.items():
            for vlan_id in trunk.allowed_vlans[:10]:  # Limit for visualization
                topology["connections"].append({
                    "source": f"device-{trunk.device_id}",
                    "target": f"vlan-{vlan_id}",
                    "type": "trunk"
                })
        
        return topology
    
    def validate_vlan_change(self, device_id: int, new_vlan_id: int) -> Tuple[bool, str]:
        """Validate if a device can be moved to a different VLAN."""
        device = Device.query.get(device_id)
        if not device:
            return False, "Device not found"
        
        new_vlan = VLAN.query.filter_by(vlan_id=new_vlan_id).first()
        if not new_vlan:
            return False, f"VLAN {new_vlan_id} does not exist"
        
        # Check if device type is compatible with VLAN type
        config = self.vlan_configs.get(new_vlan_id)
        if config:
            if config.vlan_type == VLANType.VOICE and device.device_type != "voip_phone":
                return False, "Only VoIP devices can be assigned to voice VLANs"
            
            if config.vlan_type == VLANType.MANAGEMENT and device.device_type not in ["switch", "router", "firewall"]:
                return False, "Only network devices can be assigned to management VLANs"
        
        return True, "Change is valid"
    
    def get_vlan_recommendations(self, device: Device) -> List[Dict[str, Any]]:
        """Get VLAN recommendations for a device based on its type."""
        recommendations = []
        
        # Map device types to recommended VLAN types
        type_mapping = {
            "voip_phone": VLANType.VOICE,
            "printer": VLANType.DATA,
            "server": VLANType.DATA,
            "workstation": VLANType.DATA,
            "guest_device": VLANType.GUEST,
            "switch": VLANType.MANAGEMENT,
            "router": VLANType.MANAGEMENT,
            "firewall": VLANType.MANAGEMENT,
            "access_point": VLANType.MANAGEMENT
        }
        
        recommended_type = type_mapping.get(device.device_type, VLANType.DATA)
        
        # Find VLANs of the recommended type
        for vlan_id, config in self.vlan_configs.items():
            if config.vlan_type == recommended_type:
                vlan = VLAN.query.filter_by(vlan_id=vlan_id).first()
                if vlan:
                    recommendations.append({
                        "vlan_id": vlan_id,
                        "name": vlan.name,
                        "type": config.vlan_type.value,
                        "reason": f"Recommended for {device.device_type} devices",
                        "current_device_count": len(vlan.devices)
                    })
        
        return recommendations[:5]  # Return top 5 recommendations
    
    def export_vlan_config(self, format: str = "cisco") -> str:
        """Export VLAN configuration in various formats."""
        vlans = VLAN.query.all()
        
        if format == "cisco":
            config = "! VLAN Configuration\n"
            config += "! Generated by VLANVision\n!\n"
            
            for vlan in vlans:
                config += f"vlan {vlan.vlan_id}\n"
                config += f" name {vlan.name}\n"
                if vlan.description:
                    config += f" ! {vlan.description}\n"
                config += "!\n"
            
            # Add trunk configurations
            for trunk in self.trunk_ports.values():
                config += f"interface {trunk.port_name}\n"
                config += f" switchport mode {trunk.mode}\n"
                config += f" switchport trunk encapsulation {trunk.encapsulation}\n"
                config += f" switchport trunk native vlan {trunk.native_vlan}\n"
                if len(trunk.allowed_vlans) < 100:
                    vlan_list = ",".join(map(str, trunk.allowed_vlans))
                    config += f" switchport trunk allowed vlan {vlan_list}\n"
                config += "!\n"
            
            return config
        
        elif format == "json":
            import json
            export_data = {
                "vlans": [
                    {
                        "id": vlan.vlan_id,
                        "name": vlan.name,
                        "description": vlan.description
                    }
                    for vlan in vlans
                ],
                "trunks": [
                    {
                        "port": trunk.port_name,
                        "device_id": trunk.device_id,
                        "native_vlan": trunk.native_vlan,
                        "allowed_vlans": trunk.allowed_vlans
                    }
                    for trunk in self.trunk_ports.values()
                ]
            }
            return json.dumps(export_data, indent=2)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")