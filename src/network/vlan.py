# Path: /src/network/vlan.py
# VLAN management with database integration
from src.database import db, VLAN, Device
from typing import List, Dict, Any


class VLANManager:
    """Manager class for VLAN operations using database."""
    
    def create_vlan(self, vlan_id: int, name: str, description: str) -> VLAN:
        """Create a new VLAN."""
        # Check if VLAN ID already exists
        existing = VLAN.query.filter_by(vlan_id=vlan_id).first()
        if existing:
            raise ValueError(f"VLAN ID {vlan_id} already exists")
        
        # Create new VLAN
        vlan = VLAN(
            vlan_id=vlan_id,
            name=name,
            description=description
        )
        
        db.session.add(vlan)
        db.session.commit()
        
        return vlan
    
    def delete_vlan(self, vlan_id: int) -> None:
        """Delete a VLAN."""
        vlan = VLAN.query.filter_by(vlan_id=vlan_id).first()
        if not vlan:
            raise ValueError(f"VLAN ID {vlan_id} not found")
        
        db.session.delete(vlan)
        db.session.commit()
    
    def update_vlan(self, vlan_id: int, name: str, description: str) -> VLAN:
        """Update a VLAN."""
        vlan = VLAN.query.filter_by(vlan_id=vlan_id).first()
        if not vlan:
            raise ValueError(f"VLAN ID {vlan_id} not found")
        
        vlan.name = name
        vlan.description = description
        
        db.session.commit()
        return vlan
    
    def get_vlan(self, vlan_id: int) -> VLAN:
        """Get a VLAN by ID."""
        vlan = VLAN.query.filter_by(vlan_id=vlan_id).first()
        if not vlan:
            raise ValueError(f"VLAN ID {vlan_id} not found")
        
        return vlan
    
    def list_vlans(self) -> List[Dict[str, Any]]:
        """List all VLANs."""
        vlans = VLAN.query.all()
        return [vlan.to_dict() for vlan in vlans]
    
    def add_device_to_vlan(self, device_id: int, vlan_id: int) -> Device:
        """Add a device to a VLAN."""
        device = Device.query.get(device_id)
        if not device:
            raise ValueError(f"Device ID {device_id} not found")
        
        vlan = VLAN.query.filter_by(vlan_id=vlan_id).first()
        if not vlan:
            raise ValueError(f"VLAN ID {vlan_id} not found")
        
        device.vlan_id = vlan.id
        db.session.commit()
        
        return device
    
    def remove_device_from_vlan(self, device_id: int) -> Device:
        """Remove a device from its VLAN."""
        device = Device.query.get(device_id)
        if not device:
            raise ValueError(f"Device ID {device_id} not found")
        
        device.vlan_id = None
        db.session.commit()
        
        return device
