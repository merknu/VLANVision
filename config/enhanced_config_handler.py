# Path: config/enhanced_config_handler.py
# Enhanced configuration management system for both projects
import json
import os
import logging
from typing import Dict, Any, Optional, Union, List
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
import shutil


@dataclass
class NetworkConfig:
    """Network configuration data class."""
    default_vlan_range: tuple = (1, 4094)
    max_vlans_per_device: int = 1000
    enable_vlan_validation: bool = True
    default_subnet_mask: str = "255.255.255.0"
    enable_auto_backup: bool = True
    backup_interval_hours: int = 24


@dataclass
class SecurityConfig:
    """Security configuration data class."""
    session_timeout_minutes: int = 30
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15
    require_strong_passwords: bool = True
    enable_audit_logging: bool = True
    firewall_rule_limit: int = 1000


@dataclass
class IntegrationConfig:
    """Integration configuration data class."""
    grafana_timeout_seconds: int = 30
    node_red_timeout_seconds: int = 30
    retry_attempts: int = 3
    retry_delay_seconds: int = 5
    enable_ssl_verification: bool = True


@dataclass
class FileOrganizerConfig:
    """File organizer configuration data class."""
    default_duplicate_action: str = "k"  # keep, overwrite, rename
    max_file_size_mb: int = 1000
    enable_metadata_extraction: bool = True
    create_backup_before_move: bool = False
    preserve_timestamps: bool = True
    max_filename_length: int = 255


class ConfigurationManager:
    """Enhanced configuration manager for both VLANVision and FileOrganizer."""
    
    def __init__(self, config_dir: str = "config", app_name: str = "app"):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Directory to store configuration files
            app_name: Application name for config file naming
        """
        self.config_dir = Path(config_dir)
        self.app_name = app_name
        self.config_file = self.config_dir / f"{app_name}_config.json"
        self.backup_dir = self.config_dir / "backups"
        
        # Ensure directories exist
        self.config_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
        
        # Configuration data
        self._config: Dict[str, Any] = {}
        self._default_config: Dict[str, Any] = {}
        self._config_schema: Dict[str, Any] = {}
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self._load_default_config()
        self.load_configuration()
    
    def _load_default_config(self):
        """Load default configuration based on application type."""
        if "vlan" in self.app_name.lower():
            self._default_config = self._get_vlanvision_defaults()
        elif "file" in self.app_name.lower() or "organizer" in self.app_name.lower():
            self._default_config = self._get_fileorganizer_defaults()
        else:
            self._default_config = self._get_generic_defaults()
    
    def _get_vlanvision_defaults(self) -> Dict[str, Any]:
        """Get default configuration for VLANVision."""
        return {
            "network": asdict(NetworkConfig()),
            "security": asdict(SecurityConfig()),
            "integration": asdict(IntegrationConfig()),
            "ui": {
                "theme": "dark",
                "refresh_interval_seconds": 30,
                "enable_animations": True,
                "default_dashboard_widgets": ["vlan_summary", "device_status", "recent_activities"]
            },
            "logging": {
                "level": "INFO",
                "max_file_size_mb": 10,
                "backup_count": 5,
                "log_to_file": True,
                "log_to_console": True
            },
            "database": {
                "type": "sqlite",
                "path": "data/vlanvision.db",
                "backup_enabled": True,
                "backup_interval_hours": 6
            }
        }
    
    def _get_fileorganizer_defaults(self) -> Dict[str, Any]:
        """Get default configuration for FileOrganizer."""
        return {
            "file_organizer": asdict(FileOrganizerConfig()),
            "file_categories": {
                "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".svg", ".webp", ".heic"],
                "Documents": [".pdf", ".docx", ".doc", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".rtf"],
                "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"],
                "Video": [".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"],
                "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
                "Code": [".py", ".js", ".html", ".css", ".cpp", ".java", ".c", ".h"]
            },
            "subfolders": {
                ".pdf": "Documents/PDF",
                ".docx": "Documents/Word",
                ".xlsx": "Documents/Excel",
                ".pptx": "Documents/PowerPoint",
                ".jpg": "Images/JPEG",
                ".png": "Images/PNG",
                ".mp4": "Video/MP4",
                ".mp3": "Audio/MP3"
            },
            "exclusions": {
                "file_patterns": ["*.tmp", "*.temp", ".*", "Thumbs.db", ".DS_Store"],
                "folder_patterns": [".git", ".svn", "__pycache__", "node_modules"],
                "extensions": [".log", ".cache"]
            },
            "ui": {
                "window_size": [1200, 800],
                "theme": "light",
                "show_preview_by_default": True,
                "confirm_before_processing": True
            }
        }
    
    def _get_generic_defaults(self) -> Dict[str, Any]:
        """Get generic default configuration."""
        return {
            "general": {
                "app_name": self.app_name,
                "version": "1.0.0",
                "debug_mode": False
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        }
    
    def load_configuration(self) -> bool:
        """
        Load configuration from file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                self.logger.info(f"Configuration loaded from {self.config_file}")
            else:
                self.logger.info("Configuration file not found, using defaults")
                self._config = self._default_config.copy()
                self.save_configuration()
            
            # Merge with defaults to ensure all keys exist
            self._merge_with_defaults()
            return True
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in configuration file: {e}")
            return self._load_backup_config()
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            return self._load_backup_config()
    
    def _load_backup_config(self) -> bool:
        """Load configuration from backup."""
        try:
            backup_files = list(self.backup_dir.glob(f"{self.app_name}_config_*.json"))
            if backup_files:
                latest_backup = max(backup_files, key=lambda x: x.stat().st_mtime)
                with open(latest_backup, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                self.logger.info(f"Configuration loaded from backup: {latest_backup}")
                return True
        except Exception as e:
            self.logger.error(f"Error loading backup configuration: {e}")
        
        # Fall back to defaults
        self._config = self._default_config.copy()
        self.logger.warning("Using default configuration")
        return False
    
    def _merge_with_defaults(self):
        """Merge current config with defaults to ensure all keys exist."""
        def merge_dict(default: Dict, current: Dict) -> Dict:
            result = default.copy()
            for key, value in current.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = merge_dict(result[key], value)
                else:
                    result[key] = value
            return result
        
        self._config = merge_dict(self._default_config, self._config)
    
    def save_configuration(self) -> bool:
        """
        Save configuration to file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create backup first
            self._create_backup()
            
            # Save current configuration
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Configuration saved to {self.config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            return False
    
    def _create_backup(self):
        """Create a backup of current configuration."""
        try:
            if self.config_file.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = self.backup_dir / f"{self.app_name}_config_{timestamp}.json"
                shutil.copy2(self.config_file, backup_file)
                
                # Clean old backups (keep last 10)
                self._cleanup_old_backups()
                
        except Exception as e:
            self.logger.warning(f"Could not create configuration backup: {e}")
    
    def _cleanup_old_backups(self, keep_count: int = 10):
        """Clean up old backup files."""
        try:
            backup_files = list(self.backup_dir.glob(f"{self.app_name}_config_*.json"))
            if len(backup_files) > keep_count:
                # Sort by modification time and remove oldest
                backup_files.sort(key=lambda x: x.stat().st_mtime)
                for old_backup in backup_files[:-keep_count]:
                    old_backup.unlink()
                    self.logger.debug(f"Removed old backup: {old_backup}")
        except Exception as e:
            self.logger.warning(f"Error cleaning up old backups: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key: Configuration key (supports dot notation like 'network.default_vlan_range')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        try:
            keys = key.split('.')
            value = self._config
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            return value
            
        except Exception as e:
            self.logger.warning(f"Error getting config key '{key}': {e}")
            return default
    
    def set(self, key: str, value: Any) -> bool:
        """
        Set configuration value using dot notation.
        
        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
            
        Returns:
            True if successful, False otherwise
        """
        try:
            keys = key.split('.')
            target = self._config
            
            # Navigate to parent of target key
            for k in keys[:-1]:
                if k not in target:
                    target[k] = {}
                target = target[k]
            
            # Set the value
            target[keys[-1]] = value
            self.logger.debug(f"Set config {key} = {value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting config key '{key}': {e}")
            return False
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get the complete configuration dictionary."""
        return self._config.copy()


# Factory functions for specific applications
def create_vlanvision_config(config_dir: str = "config") -> ConfigurationManager:
    """Create configuration manager for VLANVision."""
    return ConfigurationManager(config_dir, "vlanvision")


def create_fileorganizer_config(config_dir: str = "config") -> ConfigurationManager:
    """Create configuration manager for FileOrganizer."""
    return ConfigurationManager(config_dir, "fileorganizer")
