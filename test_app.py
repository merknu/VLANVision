#!/usr/bin/env python3
"""Test script to verify VLANVision application can start."""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set minimal environment variables
os.environ['SECRET_KEY'] = 'test-secret-key'
os.environ['FLASK_ENV'] = 'development'

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from src.loader import initialize_application
        print("✓ Loader module imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import loader: {e}")
        return False
    
    try:
        from src.ui.app import VLANVisionApp
        print("✓ App module imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import app: {e}")
        return False
    
    try:
        from src.database import db, User, VLAN, Device
        print("✓ Database module imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import database: {e}")
        return False
    
    try:
        from src.auth import auth_bp
        print("✓ Auth module imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import auth: {e}")
        return False
    
    return True

def test_app_creation():
    """Test that the Flask app can be created."""
    print("\nTesting app creation...")
    
    try:
        from src.ui.app import create_app
        app = create_app()
        print("✓ Flask app created successfully")
        
        # Test routes are registered
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        print(f"✓ Registered {len(rules)} routes")
        
        # Check for key routes
        key_routes = ['/login', '/api/health', '/api/vlan', '/api/network/discover']
        for route in key_routes:
            if any(route in rule for rule in rules):
                print(f"  ✓ Route {route} registered")
            else:
                print(f"  ✗ Route {route} NOT registered")
        
        return True
    except Exception as e:
        print(f"✗ Failed to create app: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("VLANVision Application Test")
    print("=" * 40)
    
    # Test imports
    if not test_imports():
        print("\n❌ Import test failed!")
        return 1
    
    # Test app creation
    if not test_app_creation():
        print("\n❌ App creation test failed!")
        return 1
    
    print("\n✅ All tests passed! The application should be ready to run.")
    print("\nTo start the application, run:")
    print("  python -m src.main")
    print("\nOr with Docker:")
    print("  docker-compose up")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())