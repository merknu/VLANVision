# VLANVision

> 🚧 This project is currently under development and may not be fully functional.

## Overview

VLANVision is a comprehensive network management solution designed to simplify network administration. With seamless integration of powerful tools like Grafana and Node-RED, it offers a robust set of features wrapped in an intuitive user interface.

## Features

- 📊 **Intuitive Dashboard**: Key performance indicators and visualizations at your fingertips.
- 🌐 **VLAN Management**: Hassle-free management of VLANs, devices, and configurations.
- 🛠️ **Tool Integration**: Advanced monitoring and customization with Grafana and Node-RED.
- 📱 **Responsive Design**: Optimized for desktop, tablet, and mobile devices.
- ♿ **Accessibility**: Built with accessibility and customization in mind.

## Requirements

- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment (recommended)

## Installation

### 1. **Clone the Repository**
```bash
git clone https://github.com/merknu/VLANVision.git
cd VLANVision
```

### 2. **Create Virtual Environment**
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. **Install Dependencies**
```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install project dependencies
pip install -r requirements.txt

# Install project in development mode
pip install -e .
```

### 4. **Environment Setup**
```bash
# Copy template environment file
cp template.env .env

# Edit .env with your configuration
# (Add your Grafana API key, database settings, etc.)
```

### 5. **Run the Application**
```bash
# Start the development server
python -m src.main

# Or use the installed command
vlanvision

# For development with debug mode
python -m src.main --debug
```

The application will be available at `http://localhost:5000`

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
