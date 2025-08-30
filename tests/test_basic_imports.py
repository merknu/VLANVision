"""
Basic import tests to ensure all modules can be imported successfully.
"""

import pytest


def test_network_imports():
    """Test that network modules can be imported."""
    try:
        from src.network import discovery
        from src.network import topology_mapper
        from src.network import config_backup
        from src.network import vendor_manager
        from src.network import vlan_enhanced
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import network modules: {e}")


def test_monitoring_imports():
    """Test that monitoring modules can be imported."""
    try:
        from src.monitoring import network_monitor
        # bandwidth_monitor requires numpy, skip if not available
        try:
            from src.monitoring import bandwidth_monitor
        except ImportError:
            pass  # numpy might not be available in CI
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import monitoring modules: {e}")


def test_database_import():
    """Test that database module can be imported."""
    try:
        from src import database
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import database module: {e}")