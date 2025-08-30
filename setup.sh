#!/bin/bash

# VLANVision Setup Script
# This script sets up the development environment for VLANVision

echo "========================================="
echo "      VLANVision Setup Script           "
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

print_status "Python 3 is installed: $(python3 --version)"

# Create virtual environment
if [ ! -d "venv" ]; then
    print_status "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        print_error "Failed to create virtual environment"
        exit 1
    fi
    print_status "Virtual environment created"
else
    print_warning "Virtual environment already exists"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip -q

# Install dependencies
print_status "Installing dependencies from requirements.txt..."
pip install -r requirements.txt -q
if [ $? -ne 0 ]; then
    print_error "Failed to install dependencies"
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    print_status "Creating .env file from template..."
    cp template.env .env
    print_warning "Please edit .env file with your configuration"
else
    print_warning ".env file already exists"
fi

# Create database directory if needed
mkdir -p instance

# Initialize database
print_status "Initializing database..."
python3 -c "
from src.database import db
from src.ui.app import create_app
app = create_app()
with app.app_context():
    db.create_all()
    print('Database initialized successfully')
" 2>/dev/null

if [ $? -eq 0 ]; then
    print_status "Database initialized successfully"
else
    print_warning "Database initialization skipped or already exists"
fi

# Create default admin user
print_status "Creating default admin user..."
python3 -c "
from src.database import db, User
from src.ui.app import create_app
app = create_app()
with app.app_context():
    # Check if admin user exists
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@vlanvision.local',
            is_admin=True
        )
        admin.set_password('admin')
        db.session.add(admin)
        db.session.commit()
        print('Default admin user created')
        print('Username: admin')
        print('Password: admin')
        print('⚠️  Please change the default password after first login!')
    else:
        print('Admin user already exists')
" 2>/dev/null

echo ""
echo "========================================="
echo "      Setup Complete!                   "
echo "========================================="
echo ""
print_status "VLANVision setup is complete!"
echo ""
echo "To start the application:"
echo "  1. Activate the virtual environment:"
echo "     source venv/bin/activate"
echo ""
echo "  2. Run the application:"
echo "     python3 run.py"
echo ""
echo "  3. Open your browser and navigate to:"
echo "     http://localhost:5000"
echo ""
echo "Default credentials:"
echo "  Username: admin"
echo "  Password: admin"
echo ""
print_warning "Remember to change the default password after first login!"
echo ""