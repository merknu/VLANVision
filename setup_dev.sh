#!/bin/bash
# Development setup script for VLANVision

echo "VLANVision Development Setup"
echo "==========================="

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment
echo -e "\n1. Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo -e "\n2. Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo -e "\n3. Upgrading pip..."
python -m pip install --upgrade pip

# Install dependencies
echo -e "\n4. Installing production dependencies..."
pip install -r requirements.txt

echo -e "\n5. Installing development dependencies..."
pip install -r requirements-dev.txt

# Install package in development mode
echo -e "\n6. Installing VLANVision in development mode..."
pip install -e .

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo -e "\n7. Creating .env file from template..."
    cp template.env .env
    echo "✓ Created .env file - please update with your configuration"
else
    echo -e "\n7. .env file already exists"
fi

# Create instance directory for database
echo -e "\n8. Creating instance directory..."
mkdir -p instance

# Run tests
echo -e "\n9. Running application test..."
python test_app.py

echo -e "\n✅ Setup complete!"
echo -e "\nTo activate the virtual environment in the future, run:"
echo "  source venv/bin/activate"
echo -e "\nTo start the application, run:"
echo "  python -m src.main"
echo -e "\nTo deactivate the virtual environment, run:"
echo "  deactivate"