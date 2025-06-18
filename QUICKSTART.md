# VLANVision Quick Start Guide

## Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Git

## Quick Setup (5 minutes)

### 1. Clone and Setup
```bash
# Clone the repository
git clone https://github.com/merknu/VLANVision.git
cd VLANVision

# Run the setup script
chmod +x setup_dev.sh
./setup_dev.sh
```

### 2. Configure Environment
Edit the `.env` file with your settings:
```bash
# Required settings
SECRET_KEY=your-secret-key-here
FLASK_ENV=development

# Optional settings
SNMP_COMMUNITY=public
DEFAULT_NETWORK_RANGE=192.168.1.0/24
```

### 3. Run the Application
```bash
# Activate virtual environment
source venv/bin/activate

# Run the application
python run.py
```

The application will be available at: http://localhost:5000

**Default login credentials:**
- Username: `admin`
- Password: `admin`

## Using Docker (Alternative)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Key Features

### 1. Network Discovery
- Navigate to **Network** → **Discover**
- Enter your network range (e.g., 192.168.1.0/24)
- Click **Start Discovery**

### 2. VLAN Management
- Navigate to **VLANs**
- Create, edit, and delete VLANs
- Assign devices to VLANs

### 3. Network Topology
- Navigate to **Network** → **Topology**
- View real-time network visualization
- Click on devices for details

### 4. Firewall Rules
- Navigate to **Security** → **Firewall**
- Create and manage firewall rules
- Enable/disable rules as needed

## API Documentation

### Authentication
```bash
# Login
curl -X POST http://localhost:5000/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin"
```

### Network Discovery
```bash
# Discover network
curl -X POST http://localhost:5000/api/network/discover \
  -H "Content-Type: application/json" \
  -H "Cookie: session=YOUR_SESSION_COOKIE" \
  -d '{"network_range": "192.168.1.0/24"}'
```

### VLAN Management
```bash
# Create VLAN
curl -X POST http://localhost:5000/api/vlan \
  -H "Content-Type: application/json" \
  -H "Cookie: session=YOUR_SESSION_COOKIE" \
  -d '{"vlan_id": 100, "name": "Guest", "description": "Guest Network"}'
```

## Troubleshooting

### Import Errors
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Database Issues
```bash
# Reset database
rm instance/vlanvision.db
python -c "from src.database import init_db; from src.ui.app import create_app; app = create_app(); init_db(app)"
```

### Port Already in Use
```bash
# Use a different port
export FLASK_PORT=5001
python run.py
```

## Development

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src
```

### Code Quality
```bash
# Format code
black src/

# Lint code
flake8 src/

# Type checking
mypy src/
```

## Support

- **Issues**: [GitHub Issues](https://github.com/merknu/VLANVision/issues)
- **Documentation**: [Wiki](https://github.com/merknu/VLANVision/wiki)
- **Email**: merknu@gmail.com