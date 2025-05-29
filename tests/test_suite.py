# Path: tests/test_suite.py
# Comprehensive test suite for both VLANVision and FileOrganizer projects
import unittest
import tempfile
import shutil
import os
import json
import sys
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List
from pathlib import Path

# Add project paths to sys.path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Test base classes
class BaseTestCase(unittest.TestCase):
    """Base test case with common setup and utilities."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(self.cleanup_temp_dir)
    
    def cleanup_temp_dir(self):
        """Clean up temporary directory."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_test_file(self, filename: str, content: str = "test content") -> str:
        """Create a test file in temp directory."""
        file_path = os.path.join(self.temp_dir, filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(content)
        return file_path
    
    def create_test_config(self, config_data: Dict[str, Any]) -> str:
        """Create a test configuration file."""
        config_path = os.path.join(self.temp_dir, "test_config.json")
        with open(config_path, 'w') as f:
            json.dump(config_data, f)
        return config_path


# VLANVision Tests
class TestVLANVision(BaseTestCase):
    """Test cases for VLANVision components."""
    
    def setUp(self):
        super().setUp()
        # Import VLANVision modules
        try:
            from src.network.vlan import VLAN, VLANManager
            from src.security.firewall import FirewallRule, FirewallManager
            from src.integration.grafana import GrafanaIntegration
            self.vlan_classes = (VLAN, VLANManager)
            self.firewall_classes = (FirewallRule, FirewallManager)
            self.grafana_class = GrafanaIntegration
        except ImportError as e:
            self.skipTest(f"VLANVision modules not available: {e}")
    
    def test_vlan_creation(self):
        """Test VLAN creation and management."""
        VLAN, VLANManager = self.vlan_classes
        
        # Test VLAN object creation
        vlan = VLAN(100, "Test VLAN", "Test Description")
        self.assertEqual(vlan.vlan_id, 100)
        self.assertEqual(vlan.name, "Test VLAN")
        self.assertEqual(vlan.description, "Test Description")
        self.assertEqual(len(vlan.devices), 0)
        
        # Test VLAN string representation
        vlan_str = str(vlan)
        self.assertIn("100", vlan_str)
        self.assertIn("Test VLAN", vlan_str)
    
    def test_vlan_manager(self):
        """Test VLAN manager functionality."""
        VLAN, VLANManager = self.vlan_classes
        
        manager = VLANManager()
        
        # Test VLAN creation
        manager.create_vlan(100, "Test VLAN", "Test Description")
        self.assertIn(100, manager.vlans)
        
        # Test duplicate VLAN creation
        with self.assertRaises(ValueError):
            manager.create_vlan(100, "Duplicate", "Should fail")
        
        # Test VLAN retrieval
        vlan = manager.get_vlan(100)
        self.assertEqual(vlan.name, "Test VLAN")
        
        # Test VLAN update
        manager.update_vlan(100, "Updated VLAN", "Updated Description")
        vlan = manager.get_vlan(100)
        self.assertEqual(vlan.name, "Updated VLAN")
        
        # Test VLAN listing
        vlans = manager.list_vlans()
        self.assertEqual(len(vlans), 1)
        
        # Test VLAN deletion
        manager.delete_vlan(100)
        self.assertNotIn(100, manager.vlans)
        
        # Test non-existent VLAN operations
        with self.assertRaises(ValueError):
            manager.get_vlan(999)
        
        with self.assertRaises(ValueError):
            manager.update_vlan(999, "Non-existent", "Should fail")
        
        with self.assertRaises(ValueError):
            manager.delete_vlan(999)


# FileOrganizer Tests  
class TestFileOrganizer(BaseTestCase):
    """Test cases for FileOrganizer components."""
    
    def setUp(self):
        super().setUp()
        
        # Create test configuration
        self.test_config = {
            "file_categories": {
                "Images": [".jpg", ".png", ".gif"],
                "Documents": [".pdf", ".docx", ".txt"],
                "Audio": [".mp3", ".wav"]
            },
            "subfolders": {
                ".jpg": "Images",
                ".png": "Images", 
                ".pdf": "Documents",
                ".txt": "Documents",
                ".mp3": "Audio"
            },
            "default_duplicate_action": "k"
        }
        
        # Create test files
        self.create_test_file("test_image.jpg", "fake image content")
        self.create_test_file("document.pdf", "fake pdf content")
        self.create_test_file("song.mp3", "fake audio content")
        self.create_test_file("readme.txt", "readme content")
        
        # Try to import FileOrganizer modules
        try:
            from file_handler.file_utils import organize_files, load_config
            from file_handler.file_operations import calculate_file_hash
            self.organize_files = organize_files
            self.load_config = load_config
            self.calculate_file_hash = calculate_file_hash
        except ImportError as e:
            self.skipTest(f"FileOrganizer modules not available: {e}")
    
    def test_config_loading(self):
        """Test configuration loading."""
        config_file = self.create_test_config(self.test_config)
        
        config = self.load_config(config_file)
        self.assertIsNotNone(config)
        self.assertIn("file_categories", config)
        self.assertEqual(config["default_duplicate_action"], "k")
        
        # Test loading non-existent config
        config = self.load_config("non_existent.json")
        self.assertIsNone(config)


# Main execution
if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(
        level=logging.WARNING,  # Reduce noise during tests
        format='%(name)s - %(levelname)s - %(message)s'
    )
    
    # Run tests
    unittest.main(verbosity=2)
