#!/usr/bin/env python3
"""
Simple startup script for VLANVision.
This provides a direct way to start the application.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Set default environment variables if not set
os.environ.setdefault('SECRET_KEY', 'dev-secret-key-change-in-production')
os.environ.setdefault('FLASK_ENV', 'development')
os.environ.setdefault('DATABASE_URL', 'sqlite:///vlanvision.db')

if __name__ == "__main__":
    try:
        print("Starting VLANVision...")
        print(f"Environment: {os.environ.get('FLASK_ENV', 'production')}")
        
        # Import and run the application
        from src.ui.app import VLANVisionApp
        
        app = VLANVisionApp()
        
        # Get configuration from environment
        host = os.environ.get('FLASK_HOST', '127.0.0.1')
        port = int(os.environ.get('FLASK_PORT', 5000))
        debug = os.environ.get('FLASK_ENV') == 'development'
        
        print(f"Running on http://{host}:{port}")
        print("Press CTRL+C to quit")
        
        app.run(host=host, port=port, debug=debug)
        
    except ImportError as e:
        print(f"Error: Missing dependency - {e}")
        print("\nPlease run the setup script first:")
        print("  ./setup_dev.sh")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)