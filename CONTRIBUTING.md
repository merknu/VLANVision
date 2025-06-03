# Contributing to VLANVision

Thank you for your interest in contributing to VLANVision! This document provides guidelines for contributing to the project.

## Getting Started

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR-USERNAME/VLANVision.git
   cd VLANVision
   ```

2. **Set up Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   pip install -e .
   ```

4. **Set up Pre-commit Hooks**
   ```bash
   pre-commit install
   ```

5. **Copy Environment Template**
   ```bash
   cp template.env .env
   # Edit .env with your local configuration
   ```

## Development Workflow

### 1. Create a Feature Branch
```bash
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes
- Follow the coding standards (enforced by pre-commit hooks)
- Write tests for new functionality
- Update documentation as needed

### 3. Run Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test types
pytest -m unit
pytest -m integration
```

### 4. Code Quality Checks
```bash
# Format code
black src/

# Check linting
flake8 src/

# Type checking
mypy src/

# Security check
bandit -r src/
```

### 5. Commit Changes
```bash
git add .
git commit -m "feat: add your feature description"
```

### 6. Push and Create PR
```bash
git push origin feature/your-feature-name
# Then create a Pull Request on GitHub
```

## Code Standards

### Python Code Style
- Follow PEP 8 style guide
- Use Black for code formatting (line length: 88)
- Use type hints where appropriate
- Write docstrings for modules, classes, and functions

### Commit Messages
Follow conventional commit format:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `test:` for test additions/changes
- `refactor:` for code refactoring
- `style:` for formatting changes
- `ci:` for CI/CD changes

### Testing
- Write unit tests for all new functions
- Use integration tests for complex workflows
- Mock external dependencies (network calls, databases)
- Aim for >80% test coverage

## Project Structure

```
VLANVision/
├── src/
│   ├── main.py              # Application entry point
│   ├── ui/                  # Flask web interface
│   ├── network/             # Network management modules
│   ├── models/              # Data models
│   ├── security/            # Security and authentication
│   └── integration/         # External tool integrations
├── tests/                   # Test suite
├── docs/                    # Documentation
├── config/                  # Configuration files
└── scripts/                 # Development/deployment scripts
```

## Areas Needing Contribution

### High Priority
1. **Core Network Functionality** (Issue #16)
   - SNMP client implementation
   - Device discovery and inventory
   - VLAN management operations

2. **Authentication System** (Issue #12)
   - User management and roles
   - Session handling
   - Security features

3. **Database Integration** (Issue #11)
   - Data models and migrations
   - CRUD operations
   - Backup/restore functionality

### Medium Priority
1. **Frontend Improvements** (Issue #10)
   - Responsive design
   - Interactive network diagrams
   - Real-time updates

2. **External Integrations** (Issues #4, #6, #7)
   - Grafana dashboard integration
   - Node-RED workflow automation
   - MQTT communication

### Documentation
- API documentation
- User guides and tutorials
- Architecture documentation
- Deployment guides

## Testing Guidelines

### Unit Tests
- Test individual functions and classes
- Mock external dependencies
- Use descriptive test names
- Group related tests in classes

```python
class TestNetworkDiscovery:
    def test_scan_network_returns_active_devices(self):
        # Test implementation
        pass
```

### Integration Tests
- Test component interactions
- Use test database/environment
- Mark with `@pytest.mark.integration`

### Network Tests
- Mock network calls for reliability
- Use `@pytest.mark.network` for real network tests
- Document any external dependencies

## Documentation

### Code Documentation
- Use docstrings for all public functions
- Include parameter types and return values
- Provide usage examples for complex functions

```python
def discover_network_devices(network_range: str, timeout: int = 5) -> List[Device]:
    """
    Discover active devices in the specified network range.
    
    Args:
        network_range: CIDR notation network (e.g., "192.168.1.0/24")
        timeout: Discovery timeout in seconds
        
    Returns:
        List of discovered network devices
        
    Example:
        >>> devices = discover_network_devices("192.168.1.0/24")
        >>> print(f"Found {len(devices)} devices")
    """
    pass
```

### README Updates
- Keep installation instructions current
- Update feature lists as they're implemented
- Add troubleshooting for common issues

## Bug Reports

When reporting bugs, please include:
- Python version and OS
- VLANVision version
- Steps to reproduce
- Expected vs actual behavior
- Error messages and tracebacks
- Network environment details (if relevant)

## Feature Requests

For new features:
- Check existing issues first
- Describe the use case and benefit
- Consider implementation complexity
- Provide examples if possible

## Security

- Report security issues privately to merknu@gmail.com
- Do not include credentials or sensitive data in commits
- Use environment variables for configuration
- Follow security best practices for network tools

## Code Review Process

1. All changes require a Pull Request
2. At least one review is required
3. CI checks must pass
4. Code coverage should not decrease
5. Documentation must be updated for new features

## Questions?

- Check the [Wiki](../../wiki) for detailed documentation
- Open a [Discussion](../../discussions) for questions
- Create an [Issue](../../issues) for bugs or feature requests
- Contact: merknu@gmail.com

Thank you for contributing to VLANVision! 🚀
