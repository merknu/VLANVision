# Path: /src/security/firewall.py
# Firewall management with database integration
from src.database import db, FirewallRule
from typing import List, Dict, Any


class FirewallManager:
    """Manager class for firewall rules using database."""
    
    def __init__(self, firewall_data_file=None):
        """Initialize FirewallManager. The file parameter is kept for backwards compatibility."""
        # Load existing rules from database
        self.rules = FirewallRule.query.all()
    
    def add_rule(self, src_ip: str, dest_ip: str, src_port: int, dest_port: int, 
                 protocol: str, action: str, name: str = None) -> FirewallRule:
        """Add a new firewall rule."""
        rule = FirewallRule(
            name=name,
            src_ip=src_ip,
            dest_ip=dest_ip,
            src_port=src_port,
            dest_port=dest_port,
            protocol=protocol.upper(),
            action=action.upper()
        )
        
        db.session.add(rule)
        db.session.commit()
        
        # Update local cache
        self.rules = FirewallRule.query.all()
        
        return rule
    
    def remove_rule(self, rule_id: int) -> None:
        """Remove a firewall rule by ID."""
        rule = FirewallRule.query.get(rule_id)
        if not rule:
            raise ValueError(f"Rule with ID {rule_id} not found")
        
        db.session.delete(rule)
        db.session.commit()
        
        # Update local cache
        self.rules = FirewallRule.query.all()
    
    def update_rule(self, rule_id: int, **kwargs) -> FirewallRule:
        """Update a firewall rule."""
        rule = FirewallRule.query.get(rule_id)
        if not rule:
            raise ValueError(f"Rule with ID {rule_id} not found")
        
        # Update fields if provided
        for field, value in kwargs.items():
            if hasattr(rule, field):
                setattr(rule, field, value)
        
        db.session.commit()
        
        # Update local cache
        self.rules = FirewallRule.query.all()
        
        return rule
    
    def get_rule(self, rule_id: int) -> FirewallRule:
        """Get a specific firewall rule."""
        rule = FirewallRule.query.get(rule_id)
        if not rule:
            raise ValueError(f"Rule with ID {rule_id} not found")
        
        return rule
    
    def list_rules(self) -> List[Dict[str, Any]]:
        """List all firewall rules."""
        rules = FirewallRule.query.order_by(FirewallRule.priority.desc()).all()
        return [rule.to_dict() for rule in rules]
    
    def enable_rule(self, rule_id: int) -> FirewallRule:
        """Enable a firewall rule."""
        return self.update_rule(rule_id, enabled=True)
    
    def disable_rule(self, rule_id: int) -> FirewallRule:
        """Disable a firewall rule."""
        return self.update_rule(rule_id, enabled=False)
    
    def set_rule_priority(self, rule_id: int, priority: int) -> FirewallRule:
        """Set the priority of a firewall rule."""
        return self.update_rule(rule_id, priority=priority)
