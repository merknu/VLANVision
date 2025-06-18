# Database setup and models
import os
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        """Set user password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if password is correct."""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class VLAN(db.Model):
    """VLAN model for network management."""
    __tablename__ = 'vlans'
    
    id = db.Column(db.Integer, primary_key=True)
    vlan_id = db.Column(db.Integer, unique=True, nullable=False)
    name = db.Column(db.String(32), nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    devices = db.relationship('Device', backref='vlan', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'vlan_id': self.vlan_id,
            'name': self.name,
            'description': self.description,
            'device_count': len(self.devices),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Device(db.Model):
    """Network device model."""
    __tablename__ = 'devices'
    
    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(255), nullable=False)
    ip_address = db.Column(db.String(45), unique=True, nullable=False)
    mac_address = db.Column(db.String(17))
    device_type = db.Column(db.String(50))
    manufacturer = db.Column(db.String(100))
    model = db.Column(db.String(100))
    location = db.Column(db.String(255))
    status = db.Column(db.String(20), default='unknown')
    last_seen = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys
    vlan_id = db.Column(db.Integer, db.ForeignKey('vlans.id'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'hostname': self.hostname,
            'ip_address': self.ip_address,
            'mac_address': self.mac_address,
            'device_type': self.device_type,
            'manufacturer': self.manufacturer,
            'model': self.model,
            'location': self.location,
            'status': self.status,
            'vlan_id': self.vlan_id,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None
        }

class FirewallRule(db.Model):
    """Firewall rule model."""
    __tablename__ = 'firewall_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    src_ip = db.Column(db.String(45), nullable=False)
    dest_ip = db.Column(db.String(45), nullable=False)
    src_port = db.Column(db.Integer)
    dest_port = db.Column(db.Integer)
    protocol = db.Column(db.String(10), nullable=False)
    action = db.Column(db.String(10), nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    priority = db.Column(db.Integer, default=100)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'src_ip': self.src_ip,
            'dest_ip': self.dest_ip,
            'src_port': self.src_port,
            'dest_port': self.dest_port,
            'protocol': self.protocol,
            'action': self.action,
            'enabled': self.enabled,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class NetworkTopology(db.Model):
    """Network topology model for storing network maps."""
    __tablename__ = 'network_topology'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    data = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
def init_db(app):
    """Initialize the database."""
    db.init_app(app)
    with app.app_context():
        db.create_all()
        
        # Create default admin user if none exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@vlanvision.local',
                is_admin=True
            )
            admin.set_password('admin')  # Change this in production!
            db.session.add(admin)
            db.session.commit()