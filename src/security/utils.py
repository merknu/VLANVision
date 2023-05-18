# Path: /src/security/utils.py
# This is the utils file for security module which contains common functions for security module
# This file is imported by firewall.py and user.py file to use common functions
import hashlib
import os
import json
from functools import wraps


def hash_password(password, salt):
    """Hash a password with a given salt."""
    hasher = hashlib.sha256()
    hasher.update((password + salt).encode('utf-8'))
    return hasher.hexdigest()


def initialize_security():
    # Initialize security here
    pass


def generate_salt():
    """Generate a random salt for password hashing."""
    return os.urandom(16).hex()


def load_json_file(file_path):
    """Load a JSON file and return its contents."""
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        data = {}
    return data


def save_json_file(file_path, data):
    """Save data to a JSON file."""
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=2)


def require_authentication(func):
    """Decorator for functions that require authentication."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        user_manager, request = args
        token = request.get('token')
        if not user_manager.validate_token(token):
            return {'error': 'Authentication required'}
        return func(*args, **kwargs)
    return wrapper


def analyze_logs(logs):
    analysis = {
        "intrusions": 0,
        "successful_connections": 0
    }

    for log in logs:
        if "unauthorized access" in log:
            analysis["intrusions"] += 1
        if "connected successfully" in log:
            analysis["successful_connections"] += 1

    return analysis
