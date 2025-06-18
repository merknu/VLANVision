# Path: src/ui/app.py
# Enhanced Flask application with better error handling, security, and structure
import os
import time
import logging
from typing import Dict, Any, Optional
from flask import Flask, render_template, request, jsonify, abort, session
from flask_login import LoginManager, login_required, current_user
from werkzeug.exceptions import BadRequest, InternalServerError
from functools import wraps

# Import our models and managers
from src.database import db, User, VLAN, Device, FirewallRule, init_db
from src.network.vlan import VLANManager
from src.security.firewall import FirewallManager
from src.integration.grafana import GrafanaIntegration
from src.integration.node_red import NodeRedIntegration
from src.auth import auth_bp
from src.network.discovery import NetworkDiscovery


class VLANVisionApp:
    """Main application class for VLANVision."""
    
    def __init__(self, config_path: str = None):
        self.app = Flask(__name__, template_folder='../../templates')
        self.config_app()
        self.setup_logging()
        self.setup_login_manager()
        self.setup_managers()
        self.register_blueprints()
        self.register_routes()
        self.register_error_handlers()
    
    def config_app(self):
        """Configure Flask application."""
        self.app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
        self.app.config['WTF_CSRF_ENABLED'] = True
        self.app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
        self.app.config['SESSION_COOKIE_HTTPONLY'] = True
        self.app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
        
        # Database configuration
        self.app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///vlanvision.db')
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        # Initialize database
        init_db(self.app)
    
    def setup_logging(self):
        """Setup application logging."""
        if not self.app.debug:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s %(levelname)s %(name)s %(message)s'
            )
    
    def setup_login_manager(self):
        """Setup Flask-Login."""
        self.login_manager = LoginManager()
        self.login_manager.init_app(self.app)
        self.login_manager.login_view = 'auth.login'
        self.login_manager.login_message = 'Please log in to access this page.'
        
        @self.login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))
    
    def setup_managers(self):
        """Initialize business logic managers."""
        with self.app.app_context():
            self.vlan_manager = VLANManager()
            self.firewall_manager = FirewallManager()
        
        # Setup integrations if configured
        grafana_url = os.environ.get('GRAFANA_URL')
        grafana_key = os.environ.get('GRAFANA_API_KEY')
        if grafana_url and grafana_key:
            self.grafana_integration = GrafanaIntegration(grafana_url, grafana_key)
        else:
            self.grafana_integration = None
            
        node_red_url = os.environ.get('NODE_RED_URL')
        node_red_key = os.environ.get('NODE_RED_API_KEY')
        if node_red_url and node_red_key:
            self.node_red_integration = NodeRedIntegration(node_red_url, node_red_key)
        else:
            self.node_red_integration = None
    
    def register_blueprints(self):
        """Register Flask blueprints."""
        self.app.register_blueprint(auth_bp)
    
    def require_json(f):
        """Decorator to ensure request has JSON content."""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                abort(400, description="Request must be JSON")
            return f(*args, **kwargs)
        return decorated_function
    
    def validate_vlan_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate VLAN creation/update data."""
        required_fields = ['vlan_id', 'name', 'description']
        if not all(field in data for field in required_fields):
            raise BadRequest("Missing required fields: vlan_id, name, description")
        
        # Validate VLAN ID
        try:
            vlan_id = int(data['vlan_id'])
            if not 1 <= vlan_id <= 4094:
                raise BadRequest("VLAN ID must be between 1 and 4094")
        except ValueError:
            raise BadRequest("VLAN ID must be a valid integer")
        
        # Validate name and description
        name = str(data['name']).strip()
        description = str(data['description']).strip()
        
        if not name or len(name) > 32:
            raise BadRequest("VLAN name must be 1-32 characters")
        
        if len(description) > 255:
            raise BadRequest("VLAN description must be less than 255 characters")
        
        return {
            'vlan_id': vlan_id,
            'name': name,
            'description': description
        }
    
    def register_routes(self):
        """Register all application routes."""
        
        # Web routes
        @self.app.route('/')
        def index():
            return render_template('index.html')
        
        @self.app.route('/dashboard')
        @login_required
        def dashboard():
            try:
                # Get summary data for dashboard
                vlans = self.vlan_manager.list_vlans()
                vlan_count = len(vlans)
                return render_template('dashboard.html', vlan_count=vlan_count)
            except Exception as e:
                logging.error(f"Error loading dashboard: {e}")
                return render_template('dashboard.html', error="Error loading dashboard data")
        
        @self.app.route('/network')
        @login_required
        def network():
            return render_template('network.html')
        
        @self.app.route('/network/topology')
        @login_required
        def network_topology():
            return render_template('network_visualization.html')
        
        @self.app.route('/security')
        @login_required
        def security():
            return render_template('security.html')
        
        @self.app.route('/integration')
        @login_required
        def integration():
            integrations_status = {
                'grafana': self.grafana_integration is not None,
                'node_red': self.node_red_integration is not None
            }
            return render_template('integration.html', integrations=integrations_status)
        
        # API routes
        @self.app.route('/api/health', methods=['GET'])
        def health_check():
            """Health check endpoint."""
            return jsonify({
                "status": "healthy",
                "version": "1.0.0",
                "integrations": {
                    "grafana": self.grafana_integration is not None,
                    "node_red": self.node_red_integration is not None
                }
            })
        
        @self.app.route('/api/data', methods=['GET'])
        @login_required
        def api_data():
            """General API data endpoint."""
            return jsonify({
                "message": "ok",
                "user": current_user.username if current_user.is_authenticated else None,
                "timestamp": int(time.time())
            })
        
        # VLAN API routes
        @self.app.route('/api/vlan', methods=['POST'])
        @login_required
        @self.require_json
        def create_vlan():
            """Create a new VLAN."""
            try:
                vlan_data = self.validate_vlan_data(request.json)
                self.vlan_manager.create_vlan(
                    vlan_data['vlan_id'],
                    vlan_data['name'],
                    vlan_data['description']
                )
                
                logging.info(f"VLAN {vlan_data['vlan_id']} created by {current_user.username}")
                return jsonify({
                    "message": "VLAN created successfully",
                    "vlan_id": vlan_data['vlan_id']
                }), 201
                
            except ValueError as e:
                logging.warning(f"VLAN creation failed: {e}")
                abort(400, description=str(e))
            except Exception as e:
                logging.error(f"Unexpected error creating VLAN: {e}")
                abort(500, description="Internal server error")
        
        @self.app.route('/api/vlan/<int:vlan_id>', methods=['PUT'])
        @login_required
        @self.require_json
        def update_vlan(vlan_id: int):
            """Update an existing VLAN."""
            try:
                if not request.json or not all(k in request.json for k in ['name', 'description']):
                    abort(400, description="Missing name or description")
                
                name = str(request.json['name']).strip()
                description = str(request.json['description']).strip()
                
                if not name or len(name) > 32:
                    abort(400, description="VLAN name must be 1-32 characters")
                
                if len(description) > 255:
                    abort(400, description="VLAN description must be less than 255 characters")
                
                self.vlan_manager.update_vlan(vlan_id, name, description)
                
                logging.info(f"VLAN {vlan_id} updated by {current_user.username}")
                return jsonify({"message": "VLAN updated successfully"})
                
            except ValueError as e:
                logging.warning(f"VLAN update failed: {e}")
                abort(400, description=str(e))
            except Exception as e:
                logging.error(f"Unexpected error updating VLAN: {e}")
                abort(500, description="Internal server error")
        
        @self.app.route('/api/vlan/<int:vlan_id>', methods=['DELETE'])
        @login_required
        def delete_vlan(vlan_id: int):
            """Delete a VLAN."""
            try:
                self.vlan_manager.delete_vlan(vlan_id)
                logging.info(f"VLAN {vlan_id} deleted by {current_user.username}")
                return jsonify({"message": "VLAN deleted successfully"})
                
            except ValueError as e:
                logging.warning(f"VLAN deletion failed: {e}")
                abort(400, description=str(e))
            except Exception as e:
                logging.error(f"Unexpected error deleting VLAN: {e}")
                abort(500, description="Internal server error")
        
        @self.app.route('/api/vlan', methods=['GET'])
        @login_required
        def list_vlans():
            """List all VLANs."""
            try:
                vlans = self.vlan_manager.list_vlans()
                return jsonify({"vlans": vlans, "count": len(vlans)})
            except Exception as e:
                logging.error(f"Error listing VLANs: {e}")
                abort(500, description="Error retrieving VLANs")
        
        @self.app.route('/api/vlan/<int:vlan_id>', methods=['GET'])
        @login_required
        def get_vlan(vlan_id: int):
            """Get a specific VLAN."""
            try:
                vlan = self.vlan_manager.get_vlan(vlan_id)
                return jsonify({
                    "vlan_id": vlan.vlan_id,
                    "name": vlan.name,
                    "description": vlan.description,
                    "device_count": len(vlan.devices)
                })
            except ValueError as e:
                abort(404, description=str(e))
            except Exception as e:
                logging.error(f"Error getting VLAN {vlan_id}: {e}")
                abort(500, description="Error retrieving VLAN")
        
        # Firewall API routes
        @self.app.route('/api/firewall/rules', methods=['GET'])
        @login_required
        def list_firewall_rules():
            """List all firewall rules."""
            try:
                rules = [rule.to_dict() for rule in self.firewall_manager.rules]
                return jsonify({"rules": rules, "count": len(rules)})
            except Exception as e:
                logging.error(f"Error listing firewall rules: {e}")
                abort(500, description="Error retrieving firewall rules")
        
        @self.app.route('/api/firewall/rules', methods=['POST'])
        @login_required
        @self.require_json
        def add_firewall_rule():
            """Add a new firewall rule."""
            try:
                required_fields = ['src_ip', 'dest_ip', 'src_port', 'dest_port', 'protocol', 'action']
                if not all(field in request.json for field in required_fields):
                    abort(400, description=f"Missing required fields: {required_fields}")
                
                self.firewall_manager.add_rule(
                    request.json['src_ip'],
                    request.json['dest_ip'],
                    request.json['src_port'],
                    request.json['dest_port'],
                    request.json['protocol'],
                    request.json['action']
                )
                
                logging.info(f"Firewall rule added by {current_user.username}")
                return jsonify({"message": "Firewall rule added successfully"}), 201
                
            except Exception as e:
                logging.error(f"Error adding firewall rule: {e}")
                abort(500, description="Error adding firewall rule")
        
        # Integration API routes
        @self.app.route('/api/integration/grafana/dashboards', methods=['GET'])
        @login_required
        def list_grafana_dashboards():
            """List Grafana dashboards."""
            if not self.grafana_integration:
                abort(503, description="Grafana integration not configured")
            
            try:
                dashboards = self.grafana_integration.list_dashboards()
                return jsonify({"dashboards": dashboards})
            except Exception as e:
                logging.error(f"Error listing Grafana dashboards: {e}")
                abort(500, description="Error communicating with Grafana")
        
        @self.app.route('/api/integration/node-red/flows', methods=['GET'])
        @login_required
        def list_node_red_flows():
            """List Node-RED flows."""
            if not self.node_red_integration:
                abort(503, description="Node-RED integration not configured")
            
            try:
                flows = self.node_red_integration.get_flows()
                return jsonify({"flows": flows})
            except Exception as e:
                logging.error(f"Error listing Node-RED flows: {e}")
                abort(500, description="Error communicating with Node-RED")
        
        # Network Discovery API routes
        @self.app.route('/api/network/discover', methods=['POST'])
        @login_required
        @self.require_json
        def discover_network():
            """Discover devices on a network range."""
            try:
                network_range = request.json.get('network_range')
                if not network_range:
                    abort(400, description="Missing network_range parameter")
                
                # Validate network range
                import ipaddress
                try:
                    ipaddress.ip_network(network_range, strict=False)
                except ValueError:
                    abort(400, description="Invalid network range format")
                
                # Get SNMP community from request or use default
                snmp_community = request.json.get('snmp_community', os.environ.get('SNMP_COMMUNITY', 'public'))
                
                # Perform discovery
                discovery = NetworkDiscovery(snmp_community=snmp_community)
                devices = discovery.discover_network(network_range)
                
                # Save to database
                saved_count = discovery.save_to_database()
                
                return jsonify({
                    "message": f"Discovery completed. Found {len(devices)} devices, saved {saved_count} new devices.",
                    "devices_found": len(devices),
                    "devices_saved": saved_count,
                    "devices": [
                        {
                            "ip_address": d.ip_address,
                            "hostname": d.hostname,
                            "mac_address": d.mac_address,
                            "device_type": d.device_type,
                            "manufacturer": d.manufacturer,
                            "location": d.location
                        } for d in devices
                    ]
                })
                
            except Exception as e:
                logging.error(f"Network discovery failed: {e}")
                abort(500, description=f"Discovery failed: {str(e)}")
        
        @self.app.route('/api/network/devices', methods=['GET'])
        @login_required
        def list_network_devices():
            """List all network devices."""
            try:
                devices = Device.query.all()
                return jsonify({
                    "devices": [device.to_dict() for device in devices],
                    "count": len(devices)
                })
            except Exception as e:
                logging.error(f"Error listing devices: {e}")
                abort(500, description="Error retrieving devices")
        
        @self.app.route('/api/network/devices/<int:device_id>', methods=['GET'])
        @login_required
        def get_network_device(device_id: int):
            """Get a specific network device."""
            try:
                device = Device.query.get(device_id)
                if not device:
                    abort(404, description="Device not found")
                
                return jsonify(device.to_dict())
            except Exception as e:
                logging.error(f"Error getting device {device_id}: {e}")
                abort(500, description="Error retrieving device")
        
        @self.app.route('/api/network/devices/<int:device_id>', methods=['PUT'])
        @login_required
        @self.require_json
        def update_network_device(device_id: int):
            """Update a network device."""
            try:
                device = Device.query.get(device_id)
                if not device:
                    abort(404, description="Device not found")
                
                # Update allowed fields
                allowed_fields = ['hostname', 'location', 'device_type', 'status']
                for field in allowed_fields:
                    if field in request.json:
                        setattr(device, field, request.json[field])
                
                db.session.commit()
                
                logging.info(f"Device {device_id} updated by {current_user.username}")
                return jsonify({
                    "message": "Device updated successfully",
                    "device": device.to_dict()
                })
                
            except Exception as e:
                logging.error(f"Error updating device {device_id}: {e}")
                abort(500, description="Error updating device")
        
        @self.app.route('/api/network/devices/<int:device_id>/assign-vlan', methods=['POST'])
        @login_required
        @self.require_json
        def assign_device_to_vlan(device_id: int):
            """Assign a device to a VLAN."""
            try:
                vlan_id = request.json.get('vlan_id')
                if not vlan_id:
                    abort(400, description="Missing vlan_id parameter")
                
                device = self.vlan_manager.add_device_to_vlan(device_id, vlan_id)
                
                logging.info(f"Device {device_id} assigned to VLAN {vlan_id} by {current_user.username}")
                return jsonify({
                    "message": "Device assigned to VLAN successfully",
                    "device": device.to_dict()
                })
                
            except ValueError as e:
                abort(404, description=str(e))
            except Exception as e:
                logging.error(f"Error assigning device to VLAN: {e}")
                abort(500, description="Error assigning device to VLAN")
    
    def register_error_handlers(self):
        """Register error handlers."""
        
        @self.app.errorhandler(400)
        def handle_bad_request(e):
            return jsonify({
                "error": "Bad Request",
                "message": str(e.description)
            }), 400
        
        @self.app.errorhandler(401)
        def handle_unauthorized(e):
            return jsonify({
                "error": "Unauthorized",
                "message": "Authentication required"
            }), 401
        
        @self.app.errorhandler(403)
        def handle_forbidden(e):
            return jsonify({
                "error": "Forbidden",
                "message": "Insufficient permissions"
            }), 403
        
        @self.app.errorhandler(404)
        def handle_not_found(e):
            return jsonify({
                "error": "Not Found",
                "message": str(e.description)
            }), 404
        
        @self.app.errorhandler(500)
        def handle_internal_error(e):
            return jsonify({
                "error": "Internal Server Error",
                "message": "An unexpected error occurred"
            }), 500
        
        @self.app.errorhandler(503)
        def handle_service_unavailable(e):
            return jsonify({
                "error": "Service Unavailable",
                "message": str(e.description)
            }), 503
    
    def run(self, host: str = '127.0.0.1', port: int = 5000, debug: bool = False):
        """Run the Flask application."""
        if debug:
            logging.warning("Running in debug mode - not for production use!")
        
        self.app.run(debug=debug, host=host, port=port)


# Factory function for creating the app
def create_app(config_path: str = None) -> Flask:
    """Application factory function."""
    vlan_app = VLANVisionApp(config_path)
    return vlan_app.app


# For backwards compatibility
def run():
    """Run the application (backwards compatibility)."""
    app = VLANVisionApp()
    app.run(debug=True)


if __name__ == "__main__":
    import time
    app = VLANVisionApp()
    app.run(debug=True)
