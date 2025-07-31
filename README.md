# VLANVision

<div align="center">

![VLANVision](https://img.shields.io/badge/VLANVision-Network%20Management-blue)
![Python](https://img.shields.io/badge/Python-3.8%2B-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Windows](https://img.shields.io/badge/Windows-Ready-0078D6?logo=windows)
![Linux](https://img.shields.io/badge/Linux-Ready-FCC624?logo=linux&logoColor=black)

**Enterprise Network Management Made Simple**

[🚀 Quick Start](#-quick-installation) • [📖 Documentation](../../wiki) • [🐛 Report Bug](../../issues) • [✨ Request Feature](../../issues)

</div>

## 🌟 Overview

VLANVision is a powerful, enterprise-grade network management system that's incredibly easy to deploy. Monitor your entire network infrastructure, manage VLANs, track devices, and receive real-time alerts - all through a beautiful, modern interface.

## ✨ Key Features

### 🎯 Core Capabilities
- **🔍 Auto-Discovery**: Automatically discover all devices on your network using SNMP, ARP, and CDP/LLDP
- **📊 Real-time Monitoring**: Track device health, bandwidth, CPU, memory, and interface statistics
- **🔔 Smart Alerts**: Threshold-based alerting with email, webhook, and SMS notifications
- **🌐 VLAN Management**: Create, modify, and assign VLANs across your infrastructure
- **🛡️ Security**: Built-in firewall rule management and access control
- **📈 Network Visualization**: Interactive topology maps with real-time status updates

### 🚀 What's New
- **⚡ 5-Minute Windows Installation**: One-line PowerShell command installs everything
- **🎨 Modern UI**: Beautiful, responsive interface that works on any device
- **📱 Mobile Ready**: Full functionality on tablets and smartphones
- **🌙 Dark Mode**: Easy on the eyes during those late-night troubleshooting sessions
- **🔄 Auto-Updates**: Keep your system current with automatic updates

## 💡 Why VLANVision?

| Feature | VLANVision | SolarWinds | PRTG | Nagios |
|---------|------------|------------|------|---------|
| **Easy Installation** | ✅ 5 minutes | ❌ Hours | ❌ Complex | ❌ Very Complex |
| **Windows Service** | ✅ Automated | ⚠️ Manual | ✅ Yes | ❌ No |
| **Modern UI** | ✅ Beautiful | ❌ Dated | ⚠️ OK | ❌ Basic |
| **Free & Open Source** | ✅ Yes | ❌ Expensive | ❌ Expensive | ✅ Yes |
| **Real-time Monitoring** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Auto-Discovery** | ✅ Yes | ✅ Yes | ✅ Yes | ⚠️ Limited |

## 🚀 Quick Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment (recommended)

### Windows Installation
Open **PowerShell as Administrator** and run:
```powershell
# Clone the repository
git clone https://github.com/merknu/VLANVision.git
cd VLANVision

# Run the automated Windows installer
.\windows\quick-install.ps1
```
[Full Windows Guide](WINDOWS_INSTALL.md)

### Linux/macOS Installation
```bash
# Clone the repository
git clone https://github.com/merknu/VLANVision.git
cd VLANVision

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment configuration
cp template.env .env

# Initialize the database
python -m src.database

# Run the application
python run.py
```

### Docker Installation
```bash
# Using Docker Compose (Recommended)
git clone https://github.com/merknu/VLANVision.git
cd VLANVision
docker-compose up -d

# Or build manually
docker build -t vlanvision .
docker run -d -p 5000:5000 --name vlanvision vlanvision
```

## 🖥️ Screenshots

<div align="center">
<table>
<tr>
<td width="50%">

### Dashboard
<img src="https://via.placeholder.com/400x300" alt="Dashboard">

Real-time network metrics at a glance

</td>
<td width="50%">

### Network Topology
<img src="https://via.placeholder.com/400x300" alt="Topology">

Interactive network visualization

</td>
</tr>
<tr>
<td width="50%">

### Device Management
<img src="https://via.placeholder.com/400x300" alt="Devices">

Complete device inventory and control

</td>
<td width="50%">

### Alert Center
<img src="https://via.placeholder.com/400x300" alt="Alerts">

Smart alerting with multiple channels

</td>
</tr>
</table>
</div>

## Configuration

### Environment Variables
Create a `.env` file in the project root with the following variables:

```bash
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
DEBUG=True

# Database
DATABASE_URL=sqlite:///vlanvision.db

# Network Configuration
SNMP_COMMUNITY=public
DEFAULT_NETWORK_RANGE=192.168.1.0/24

# External Integrations
GRAFANA_URL=http://localhost:3000
GRAFANA_API_KEY=your-grafana-api-key
NODE_RED_URL=http://localhost:1880
```

## Development

### Setting up Development Environment
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Run with coverage
pytest --cov=src

# Format code
black src/
flake8 src/
```

### Project Structure
```
VLANVision/
├── src/
│   ├── main.py           # Application entry point
│   ├── ui/               # Flask web interface
│   ├── network/          # Network management modules
│   ├── models/           # Data models
│   ├── security/         # Security and authentication
│   └── integration/      # External tool integrations
├── tests/                # Test suite
├── config/               # Configuration files
├── requirements.txt      # Production dependencies
├── requirements-dev.txt  # Development dependencies
└── setup.py             # Package configuration
```

## Docker Support

### Using Docker Compose (Recommended)
```bash
# Start all services (VLANVision + Grafana + Node-RED)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Manual Docker Build
```bash
# Build image
docker build -t vlanvision .

# Run container
docker run -p 5000:5000 vlanvision
```

## External Integrations

### Grafana Integration
VLANVision integrates with Grafana for advanced network monitoring and visualization.

1. Install Grafana locally or use existing instance
2. Create API key in Grafana
3. Add API key to `.env` file
4. Configure dashboards through VLANVision interface

### Node-RED Integration
Automate network operations and create custom workflows.

1. Install Node-RED locally or use existing instance
2. Configure MQTT topics and flows
3. Import provided flows from `integration/node-red-flows.json`

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## Troubleshooting

### Common Issues

**Import Errors**: Make sure you've activated your virtual environment and installed dependencies
```bash
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

**Database Issues**: Initialize the database
```bash
python -c "from src.models import db; db.create_all()"
```

**Port Already in Use**: Change the port in your configuration or stop the conflicting service
```bash
export FLASK_PORT=5001  # Use different port
```

## Support & Documentation

- 📖 **Documentation**: [Wiki](../../wiki)
- 🐛 **Bug Reports**: [Issues](../../issues)
- 💬 **Discussions**: [Discussions](../../discussions)
- 📧 **Contact**: merknu@gmail.com

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Flask framework for the robust web foundation
- Grafana for powerful monitoring capabilities
- Node-RED for automation and integration possibilities
- The open-source community for inspiration and tools
