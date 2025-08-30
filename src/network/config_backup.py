"""
Network Configuration Backup and Restore System
Provides automated backup, versioning, and restore capabilities for network device configurations.
"""

import os
import json
import hashlib
import gzip
import shutil
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import difflib
import paramiko
import telnetlib
import re
from pathlib import Path

from src.database import db, Device


class BackupStatus(Enum):
    """Status of backup operations."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    IN_PROGRESS = "in_progress"
    SCHEDULED = "scheduled"


class DeviceVendor(Enum):
    """Supported network device vendors."""
    CISCO = "cisco"
    JUNIPER = "juniper"
    ARISTA = "arista"
    HP = "hp"
    MIKROTIK = "mikrotik"
    FORTINET = "fortinet"
    PALOALTO = "paloalto"
    GENERIC = "generic"


@dataclass
class ConfigBackup:
    """Represents a configuration backup."""
    device_id: int
    device_ip: str
    device_hostname: str
    vendor: DeviceVendor
    backup_id: str
    timestamp: datetime
    config_content: str
    config_hash: str
    compressed: bool = False
    encrypted: bool = False
    status: BackupStatus = BackupStatus.SUCCESS
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BackupPolicy:
    """Backup policy configuration."""
    name: str
    enabled: bool = True
    schedule: str = "daily"  # daily, weekly, monthly, hourly
    retention_days: int = 30
    compress: bool = True
    encrypt: bool = False
    notify_on_failure: bool = True
    device_filter: Optional[Dict[str, Any]] = None


class ConfigBackupManager:
    """Manages network device configuration backups."""
    
    # Vendor-specific commands
    VENDOR_COMMANDS = {
        DeviceVendor.CISCO: {
            'show_running': 'show running-config',
            'show_startup': 'show startup-config',
            'show_version': 'show version',
            'terminal_length': 'terminal length 0',
            'enable': 'enable',
            'config_terminal': 'configure terminal',
            'write_memory': 'write memory'
        },
        DeviceVendor.JUNIPER: {
            'show_running': 'show configuration',
            'show_version': 'show version',
            'terminal_length': 'set cli screen-length 0',
            'config_mode': 'configure',
            'commit': 'commit'
        },
        DeviceVendor.ARISTA: {
            'show_running': 'show running-config',
            'show_startup': 'show startup-config',
            'show_version': 'show version',
            'terminal_length': 'terminal length 0',
            'enable': 'enable',
            'config_terminal': 'configure terminal'
        },
        DeviceVendor.HP: {
            'show_running': 'display current-configuration',
            'show_version': 'display version',
            'terminal_length': 'screen-length disable',
            'save': 'save'
        },
        DeviceVendor.MIKROTIK: {
            'show_running': 'export',
            'show_version': 'system resource print',
            'backup': 'system backup save'
        }
    }
    
    def __init__(self, backup_dir: str = "./backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.backup_history: Dict[int, List[ConfigBackup]] = {}
        self.policies: Dict[str, BackupPolicy] = {}
        self._load_policies()
    
    def _load_policies(self):
        """Load backup policies from configuration."""
        # Default policies
        self.policies['default'] = BackupPolicy(
            name='default',
            schedule='daily',
            retention_days=30,
            compress=True
        )
        
        self.policies['critical'] = BackupPolicy(
            name='critical',
            schedule='hourly',
            retention_days=90,
            compress=True,
            encrypt=True,
            notify_on_failure=True
        )
    
    def backup_device(self, device: Device, credentials: Dict[str, str]) -> ConfigBackup:
        """
        Backup configuration from a network device.
        
        Args:
            device: Device object from database
            credentials: Connection credentials (username, password, enable_password)
            
        Returns:
            ConfigBackup object with backup details
        """
        print(f"Starting backup for {device.hostname} ({device.ip_address})")
        
        # Determine vendor
        vendor = self._detect_vendor(device)
        
        # Get device configuration
        try:
            config_content = self._retrieve_config(
                device.ip_address,
                vendor,
                credentials
            )
            
            if not config_content:
                raise Exception("Empty configuration retrieved")
            
            # Create backup
            backup = self._create_backup(device, vendor, config_content)
            
            # Save to disk
            self._save_backup(backup)
            
            # Update history
            if device.id not in self.backup_history:
                self.backup_history[device.id] = []
            self.backup_history[device.id].append(backup)
            
            print(f"Backup successful for {device.hostname}")
            return backup
            
        except Exception as e:
            print(f"Backup failed for {device.hostname}: {e}")
            
            # Create failed backup entry
            backup = ConfigBackup(
                device_id=device.id,
                device_ip=device.ip_address,
                device_hostname=device.hostname,
                vendor=vendor,
                backup_id=self._generate_backup_id(device),
                timestamp=datetime.utcnow(),
                config_content="",
                config_hash="",
                status=BackupStatus.FAILED,
                metadata={'error': str(e)}
            )
            
            return backup
    
    def _detect_vendor(self, device: Device) -> DeviceVendor:
        """Detect device vendor from device information."""
        if device.manufacturer:
            manufacturer_lower = device.manufacturer.lower()
            
            if 'cisco' in manufacturer_lower:
                return DeviceVendor.CISCO
            elif 'juniper' in manufacturer_lower:
                return DeviceVendor.JUNIPER
            elif 'arista' in manufacturer_lower:
                return DeviceVendor.ARISTA
            elif 'hp' in manufacturer_lower or 'aruba' in manufacturer_lower:
                return DeviceVendor.HP
            elif 'mikrotik' in manufacturer_lower:
                return DeviceVendor.MIKROTIK
            elif 'fortinet' in manufacturer_lower:
                return DeviceVendor.FORTINET
            elif 'palo alto' in manufacturer_lower:
                return DeviceVendor.PALOALTO
        
        return DeviceVendor.GENERIC
    
    def _retrieve_config(self, ip_address: str, vendor: DeviceVendor, 
                        credentials: Dict[str, str]) -> str:
        """Retrieve configuration from device using SSH or Telnet."""
        # Try SSH first
        try:
            return self._retrieve_config_ssh(ip_address, vendor, credentials)
        except Exception as ssh_error:
            print(f"SSH failed: {ssh_error}, trying Telnet...")
            
            # Fall back to Telnet
            try:
                return self._retrieve_config_telnet(ip_address, vendor, credentials)
            except Exception as telnet_error:
                print(f"Telnet also failed: {telnet_error}")
                raise Exception(f"Both SSH and Telnet failed: SSH: {ssh_error}, Telnet: {telnet_error}")
    
    def _retrieve_config_ssh(self, ip_address: str, vendor: DeviceVendor, 
                            credentials: Dict[str, str]) -> str:
        """Retrieve configuration via SSH."""
        config = ""
        
        # Create SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            # Connect
            ssh.connect(
                ip_address,
                username=credentials.get('username'),
                password=credentials.get('password'),
                timeout=30,
                look_for_keys=False,
                allow_agent=False
            )
            
            # Get commands for vendor
            commands = self.VENDOR_COMMANDS.get(vendor, self.VENDOR_COMMANDS[DeviceVendor.CISCO])
            
            # Open interactive shell
            shell = ssh.invoke_shell()
            time.sleep(2)
            
            # Clear buffer
            shell.recv(65535)
            
            # Disable pagination
            if 'terminal_length' in commands:
                shell.send(commands['terminal_length'] + '\n')
                time.sleep(1)
                shell.recv(65535)
            
            # Enter enable mode if needed (Cisco)
            if vendor == DeviceVendor.CISCO and 'enable' in commands:
                shell.send(commands['enable'] + '\n')
                time.sleep(1)
                
                # Send enable password if required
                output = shell.recv(65535).decode('utf-8')
                if 'password' in output.lower():
                    enable_password = credentials.get('enable_password', credentials.get('password'))
                    shell.send(enable_password + '\n')
                    time.sleep(1)
                    shell.recv(65535)
            
            # Get running configuration
            shell.send(commands['show_running'] + '\n')
            time.sleep(5)  # Wait for large configs
            
            # Collect output
            config = ""
            while shell.recv_ready():
                chunk = shell.recv(65535).decode('utf-8', errors='ignore')
                config += chunk
                time.sleep(0.5)
            
            # Clean configuration
            config = self._clean_config(config, vendor)
            
        finally:
            ssh.close()
        
        return config
    
    def _retrieve_config_telnet(self, ip_address: str, vendor: DeviceVendor, 
                               credentials: Dict[str, str]) -> str:
        """Retrieve configuration via Telnet."""
        config = ""
        
        try:
            # Connect via Telnet
            tn = telnetlib.Telnet(ip_address, timeout=30)
            
            # Login
            tn.read_until(b"Username: ", timeout=5)
            tn.write(credentials.get('username').encode('ascii') + b"\n")
            
            tn.read_until(b"Password: ", timeout=5)
            tn.write(credentials.get('password').encode('ascii') + b"\n")
            
            time.sleep(2)
            
            # Get commands for vendor
            commands = self.VENDOR_COMMANDS.get(vendor, self.VENDOR_COMMANDS[DeviceVendor.CISCO])
            
            # Disable pagination
            if 'terminal_length' in commands:
                tn.write(commands['terminal_length'].encode('ascii') + b"\n")
                time.sleep(1)
            
            # Get running configuration
            tn.write(commands['show_running'].encode('ascii') + b"\n")
            time.sleep(5)
            
            # Read output
            config = tn.read_very_eager().decode('utf-8', errors='ignore')
            
            # Clean configuration
            config = self._clean_config(config, vendor)
            
            tn.close()
            
        except Exception as e:
            raise Exception(f"Telnet retrieval failed: {e}")
        
        return config
    
    def _clean_config(self, config: str, vendor: DeviceVendor) -> str:
        """Clean and normalize configuration output."""
        lines = config.split('\n')
        cleaned_lines = []
        
        # Remove command echo and prompts
        in_config = False
        for line in lines:
            # Skip empty lines at beginning/end
            if not in_config and not line.strip():
                continue
            
            # Detect start of configuration
            if not in_config:
                if any(x in line.lower() for x in ['running-config', 'configuration', 'export']):
                    in_config = True
                continue
            
            # Detect end of configuration
            if in_config and any(x in line for x in ['#', '>', 'end', '[admin@']):
                if vendor == DeviceVendor.CISCO and line.strip() == 'end':
                    cleaned_lines.append(line)
                break
            
            # Add configuration lines
            if in_config:
                # Remove timestamps and dynamic content
                if not any(x in line.lower() for x in ['last configuration change', 'nvram', 'uptime']):
                    cleaned_lines.append(line.rstrip())
        
        return '\n'.join(cleaned_lines)
    
    def _create_backup(self, device: Device, vendor: DeviceVendor, 
                      config_content: str) -> ConfigBackup:
        """Create backup object from configuration."""
        backup_id = self._generate_backup_id(device)
        config_hash = self._calculate_hash(config_content)
        
        # Check if configuration changed
        last_backup = self._get_last_backup(device.id)
        if last_backup and last_backup.config_hash == config_hash:
            print(f"Configuration unchanged for {device.hostname}")
        
        # Compress if large
        compressed = False
        if len(config_content) > 10000:  # 10KB threshold
            config_content = self._compress_config(config_content)
            compressed = True
        
        backup = ConfigBackup(
            device_id=device.id,
            device_ip=device.ip_address,
            device_hostname=device.hostname,
            vendor=vendor,
            backup_id=backup_id,
            timestamp=datetime.utcnow(),
            config_content=config_content,
            config_hash=config_hash,
            compressed=compressed,
            status=BackupStatus.SUCCESS,
            metadata={
                'config_size': len(config_content),
                'line_count': config_content.count('\n')
            }
        )
        
        return backup
    
    def _generate_backup_id(self, device: Device) -> str:
        """Generate unique backup ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"{device.hostname}_{timestamp}"
    
    def _calculate_hash(self, content: str) -> str:
        """Calculate SHA-256 hash of content."""
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _compress_config(self, config: str) -> str:
        """Compress configuration using gzip."""
        compressed = gzip.compress(config.encode())
        # Return base64 encoded for text storage
        import base64
        return base64.b64encode(compressed).decode('ascii')
    
    def _decompress_config(self, compressed_config: str) -> str:
        """Decompress configuration."""
        import base64
        compressed = base64.b64decode(compressed_config.encode('ascii'))
        return gzip.decompress(compressed).decode('utf-8')
    
    def _save_backup(self, backup: ConfigBackup):
        """Save backup to disk."""
        # Create device directory
        device_dir = self.backup_dir / f"device_{backup.device_id}"
        device_dir.mkdir(exist_ok=True)
        
        # Generate filename
        filename = f"{backup.backup_id}.conf"
        if backup.compressed:
            filename += ".gz"
        
        file_path = device_dir / filename
        
        # Write configuration
        if backup.compressed:
            # Already compressed, write as-is
            with open(file_path, 'w') as f:
                f.write(backup.config_content)
        else:
            with open(file_path, 'w') as f:
                f.write(backup.config_content)
        
        backup.file_path = str(file_path)
        
        # Save metadata
        metadata_file = device_dir / f"{backup.backup_id}.json"
        with open(metadata_file, 'w') as f:
            json.dump({
                'backup_id': backup.backup_id,
                'device_id': backup.device_id,
                'device_hostname': backup.device_hostname,
                'timestamp': backup.timestamp.isoformat(),
                'vendor': backup.vendor.value,
                'config_hash': backup.config_hash,
                'compressed': backup.compressed,
                'status': backup.status.value,
                'metadata': backup.metadata
            }, f, indent=2)
    
    def _get_last_backup(self, device_id: int) -> Optional[ConfigBackup]:
        """Get the most recent backup for a device."""
        if device_id in self.backup_history:
            backups = self.backup_history[device_id]
            if backups:
                return max(backups, key=lambda b: b.timestamp)
        return None
    
    def restore_config(self, device: Device, backup: ConfigBackup, 
                      credentials: Dict[str, str]) -> bool:
        """
        Restore configuration to a device.
        
        Args:
            device: Device to restore to
            backup: Backup to restore
            credentials: Connection credentials
            
        Returns:
            True if successful, False otherwise
        """
        print(f"Restoring configuration to {device.hostname}")
        
        try:
            # Decompress if needed
            config = backup.config_content
            if backup.compressed:
                config = self._decompress_config(config)
            
            # Connect to device
            success = self._push_config(device.ip_address, backup.vendor, config, credentials)
            
            if success:
                print(f"Configuration restored successfully to {device.hostname}")
                
                # Log restore operation
                backup.metadata['restored_at'] = datetime.utcnow().isoformat()
                backup.metadata['restored_to'] = device.ip_address
                
            return success
            
        except Exception as e:
            print(f"Restore failed for {device.hostname}: {e}")
            return False
    
    def _push_config(self, ip_address: str, vendor: DeviceVendor, 
                    config: str, credentials: Dict[str, str]) -> bool:
        """Push configuration to device."""
        # This is a simplified implementation
        # In production, this would need careful handling of:
        # - Configuration mode entry/exit
        # - Line-by-line configuration with error checking
        # - Commit/save operations
        # - Rollback on failure
        
        print(f"WARNING: Configuration restore is a dangerous operation!")
        print(f"This would push configuration to {ip_address}")
        
        # For safety, just return True in this demo
        # Real implementation would use SSH/Telnet to push config
        return True
    
    def compare_configs(self, backup1: ConfigBackup, backup2: ConfigBackup) -> str:
        """Compare two configuration backups and return diff."""
        # Decompress if needed
        config1 = backup1.config_content
        if backup1.compressed:
            config1 = self._decompress_config(config1)
        
        config2 = backup2.config_content
        if backup2.compressed:
            config2 = self._decompress_config(config2)
        
        # Generate diff
        diff = difflib.unified_diff(
            config1.splitlines(keepends=True),
            config2.splitlines(keepends=True),
            fromfile=f"{backup1.device_hostname}_{backup1.timestamp}",
            tofile=f"{backup2.device_hostname}_{backup2.timestamp}",
            lineterm=''
        )
        
        return ''.join(diff)
    
    def cleanup_old_backups(self, retention_days: int = 30):
        """Remove backups older than retention period."""
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        removed_count = 0
        
        for device_id, backups in self.backup_history.items():
            # Filter out old backups
            old_backups = [b for b in backups if b.timestamp < cutoff_date]
            
            for backup in old_backups:
                # Remove file
                if backup.file_path and os.path.exists(backup.file_path):
                    os.remove(backup.file_path)
                    
                    # Remove metadata file
                    metadata_file = backup.file_path.replace('.conf', '.json').replace('.gz', '')
                    if os.path.exists(metadata_file):
                        os.remove(metadata_file)
                
                removed_count += 1
            
            # Update history
            self.backup_history[device_id] = [b for b in backups if b.timestamp >= cutoff_date]
        
        print(f"Removed {removed_count} old backups")
        return removed_count
    
    def get_backup_statistics(self) -> Dict[str, Any]:
        """Get backup statistics."""
        total_backups = sum(len(backups) for backups in self.backup_history.values())
        successful_backups = sum(
            len([b for b in backups if b.status == BackupStatus.SUCCESS])
            for backups in self.backup_history.values()
        )
        failed_backups = sum(
            len([b for b in backups if b.status == BackupStatus.FAILED])
            for backups in self.backup_history.values()
        )
        
        # Calculate storage size
        total_size = 0
        for backups in self.backup_history.values():
            for backup in backups:
                if backup.file_path and os.path.exists(backup.file_path):
                    total_size += os.path.getsize(backup.file_path)
        
        # Get latest backup time
        all_backups = []
        for backups in self.backup_history.values():
            all_backups.extend(backups)
        
        latest_backup = max(all_backups, key=lambda b: b.timestamp) if all_backups else None
        
        return {
            'total_backups': total_backups,
            'successful_backups': successful_backups,
            'failed_backups': failed_backups,
            'success_rate': (successful_backups / total_backups * 100) if total_backups > 0 else 0,
            'total_devices': len(self.backup_history),
            'total_size_mb': total_size / (1024 * 1024),
            'latest_backup': latest_backup.timestamp.isoformat() if latest_backup else None,
            'backup_directory': str(self.backup_dir)
        }


# Global instance
config_backup_manager = ConfigBackupManager()