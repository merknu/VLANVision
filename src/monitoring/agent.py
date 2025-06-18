"""
VLANVision Monitoring Agent
Collects real-time metrics from network devices and system
"""

import asyncio
import json
import logging
import platform
import psutil
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, List, Any, Optional

import aiohttp
from pysnmp.hlapi import *

from src.database import db, Device
from src.monitoring.metrics import MetricsCollector, MetricType


class MonitoringAgent:
    """Background monitoring agent for continuous device monitoring."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.running = False
        self.collectors = {}
        self.executor = ThreadPoolExecutor(max_workers=config.get('max_workers', 20))
        self.metrics_buffer = []
        self.logger = logging.getLogger('vlanvision.monitor')
        
        # Initialize collectors
        self._init_collectors()
    
    def _init_collectors(self):
        """Initialize metric collectors."""
        # SNMP collector
        self.collectors['snmp'] = SNMPCollector(
            community=self.config.get('snmp_community', 'public'),
            timeout=self.config.get('snmp_timeout', 5)
        )
        
        # ICMP collector (ping)
        self.collectors['icmp'] = ICMPCollector()
        
        # System collector (for local system metrics)
        if platform.system() == 'Windows':
            self.collectors['system'] = WindowsSystemCollector()
        else:
            self.collectors['system'] = LinuxSystemCollector()
    
    async def start(self):
        """Start the monitoring agent."""
        self.running = True
        self.logger.info("Monitoring agent started")
        
        # Start collection tasks
        tasks = [
            self._device_monitor_loop(),
            self._metrics_processor_loop(),
            self._health_check_loop()
        ]
        
        await asyncio.gather(*tasks)
    
    async def stop(self):
        """Stop the monitoring agent."""
        self.running = False
        self.executor.shutdown(wait=True)
        self.logger.info("Monitoring agent stopped")
    
    async def _device_monitor_loop(self):
        """Main monitoring loop for devices."""
        while self.running:
            try:
                # Get all active devices
                devices = await self._get_active_devices()
                
                # Monitor each device
                tasks = []
                for device in devices:
                    task = self._monitor_device(device)
                    tasks.append(task)
                
                # Wait for all monitoring tasks
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for device, result in zip(devices, results):
                    if isinstance(result, Exception):
                        self.logger.error(f"Error monitoring device {device.ip_address}: {result}")
                    else:
                        self.metrics_buffer.extend(result)
                
                # Wait before next cycle
                await asyncio.sleep(self.config.get('poll_interval', 60))
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(10)
    
    async def _monitor_device(self, device: Device) -> List[Dict[str, Any]]:
        """Monitor a single device."""
        metrics = []
        
        # Ping test
        ping_result = await self._run_in_executor(
            self.collectors['icmp'].ping,
            device.ip_address
        )
        
        metrics.append({
            'device_id': device.id,
            'metric_type': MetricType.AVAILABILITY,
            'value': 1 if ping_result['success'] else 0,
            'timestamp': datetime.utcnow(),
            'metadata': {
                'response_time': ping_result.get('rtt'),
                'packet_loss': ping_result.get('packet_loss', 0)
            }
        })
        
        # If device is reachable, collect more metrics
        if ping_result['success']:
            # SNMP metrics
            if device.snmp_enabled:
                snmp_metrics = await self._collect_snmp_metrics(device)
                metrics.extend(snmp_metrics)
            
            # SSH metrics (if applicable)
            if device.ssh_enabled and device.device_type in ['switch', 'router']:
                ssh_metrics = await self._collect_ssh_metrics(device)
                metrics.extend(ssh_metrics)
        
        return metrics
    
    async def _collect_snmp_metrics(self, device: Device) -> List[Dict[str, Any]]:
        """Collect SNMP metrics from device."""
        metrics = []
        
        try:
            # System metrics
            system_oids = {
                'sysUptime': '1.3.6.1.2.1.1.3.0',
                'sysDescr': '1.3.6.1.2.1.1.1.0',
                'cpu': '1.3.6.1.4.1.9.2.1.56.0',  # Cisco CPU
                'memory': '1.3.6.1.4.1.9.9.48.1.1.1.5.1'  # Cisco memory
            }
            
            for metric_name, oid in system_oids.items():
                value = await self._run_in_executor(
                    self.collectors['snmp'].get,
                    device.ip_address,
                    oid
                )
                
                if value is not None:
                    metric_type = self._get_metric_type(metric_name)
                    metrics.append({
                        'device_id': device.id,
                        'metric_type': metric_type,
                        'value': self._parse_snmp_value(value),
                        'timestamp': datetime.utcnow(),
                        'metadata': {'oid': oid}
                    })
            
            # Interface metrics
            interface_metrics = await self._collect_interface_metrics(device)
            metrics.extend(interface_metrics)
            
        except Exception as e:
            self.logger.error(f"SNMP collection error for {device.ip_address}: {e}")
        
        return metrics
    
    async def _collect_interface_metrics(self, device: Device) -> List[Dict[str, Any]]:
        """Collect interface-specific metrics."""
        metrics = []
        
        # Interface OIDs
        oids = {
            'ifInOctets': '1.3.6.1.2.1.2.2.1.10',
            'ifOutOctets': '1.3.6.1.2.1.2.2.1.16',
            'ifInErrors': '1.3.6.1.2.1.2.2.1.14',
            'ifOutErrors': '1.3.6.1.2.1.2.2.1.20',
            'ifOperStatus': '1.3.6.1.2.1.2.2.1.8'
        }
        
        # Walk interfaces
        for metric_name, base_oid in oids.items():
            try:
                values = await self._run_in_executor(
                    self.collectors['snmp'].walk,
                    device.ip_address,
                    base_oid
                )
                
                for oid, value in values:
                    interface_index = str(oid).split('.')[-1]
                    
                    metrics.append({
                        'device_id': device.id,
                        'metric_type': MetricType.INTERFACE,
                        'value': self._parse_snmp_value(value),
                        'timestamp': datetime.utcnow(),
                        'metadata': {
                            'interface_index': interface_index,
                            'metric_name': metric_name
                        }
                    })
            except Exception as e:
                self.logger.debug(f"Interface metric error: {e}")
        
        return metrics
    
    async def _metrics_processor_loop(self):
        """Process and store collected metrics."""
        while self.running:
            try:
                if self.metrics_buffer:
                    # Get metrics to process
                    metrics_to_process = self.metrics_buffer[:1000]
                    self.metrics_buffer = self.metrics_buffer[1000:]
                    
                    # Store in database
                    await self._store_metrics(metrics_to_process)
                    
                    # Send to real-time subscribers
                    await self._publish_metrics(metrics_to_process)
                
                await asyncio.sleep(5)
                
            except Exception as e:
                self.logger.error(f"Metrics processor error: {e}")
                await asyncio.sleep(10)
    
    async def _store_metrics(self, metrics: List[Dict[str, Any]]):
        """Store metrics in time-series database."""
        # This would typically use InfluxDB or TimescaleDB
        # For now, we'll use a simple database table
        pass
    
    async def _publish_metrics(self, metrics: List[Dict[str, Any]]):
        """Publish metrics to real-time subscribers."""
        # This would use WebSocket or message queue
        pass
    
    async def _health_check_loop(self):
        """Monitor agent health."""
        while self.running:
            try:
                # Log agent status
                self.logger.info(f"Agent health: Buffer size: {len(self.metrics_buffer)}")
                
                # Check system resources
                cpu_percent = psutil.cpu_percent(interval=1)
                memory_percent = psutil.virtual_memory().percent
                
                if cpu_percent > 80:
                    self.logger.warning(f"High CPU usage: {cpu_percent}%")
                
                if memory_percent > 80:
                    self.logger.warning(f"High memory usage: {memory_percent}%")
                
                await asyncio.sleep(60)
                
            except Exception as e:
                self.logger.error(f"Health check error: {e}")
                await asyncio.sleep(60)
    
    async def _get_active_devices(self) -> List[Device]:
        """Get list of active devices to monitor."""
        # In a real implementation, this would query the database
        # For now, return a mock list
        return []
    
    async def _run_in_executor(self, func, *args):
        """Run blocking function in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, func, *args)
    
    def _get_metric_type(self, metric_name: str) -> MetricType:
        """Map metric name to metric type."""
        mapping = {
            'cpu': MetricType.CPU,
            'memory': MetricType.MEMORY,
            'sysUptime': MetricType.UPTIME,
            'temperature': MetricType.TEMPERATURE
        }
        return mapping.get(metric_name, MetricType.CUSTOM)
    
    def _parse_snmp_value(self, value):
        """Parse SNMP value to appropriate type."""
        if hasattr(value, 'prettyPrint'):
            value = value.prettyPrint()
        
        # Try to convert to number
        try:
            if '.' in str(value):
                return float(value)
            return int(value)
        except (ValueError, TypeError):
            return str(value)


class SNMPCollector:
    """SNMP metric collector."""
    
    def __init__(self, community: str = 'public', timeout: int = 5):
        self.community = community
        self.timeout = timeout
    
    def get(self, ip: str, oid: str) -> Optional[Any]:
        """Get single SNMP value."""
        errorIndication, errorStatus, errorIndex, varBinds = next(
            getCmd(SnmpEngine(),
                   CommunityData(self.community),
                   UdpTransportTarget((ip, 161), timeout=self.timeout),
                   ContextData(),
                   ObjectType(ObjectIdentity(oid)))
        )
        
        if errorIndication or errorStatus:
            return None
        
        return varBinds[0][1] if varBinds else None
    
    def walk(self, ip: str, oid: str) -> List[tuple]:
        """Walk SNMP tree."""
        results = []
        
        for (errorIndication,
             errorStatus,
             errorIndex,
             varBinds) in nextCmd(SnmpEngine(),
                                  CommunityData(self.community),
                                  UdpTransportTarget((ip, 161), timeout=self.timeout),
                                  ContextData(),
                                  ObjectType(ObjectIdentity(oid)),
                                  lexicographicMode=False):
            
            if errorIndication or errorStatus:
                break
            
            for varBind in varBinds:
                results.append(varBind)
        
        return results


class ICMPCollector:
    """ICMP (ping) collector."""
    
    def ping(self, ip: str, count: int = 4) -> Dict[str, Any]:
        """Ping a host and return results."""
        if platform.system() == 'Windows':
            return self._ping_windows(ip, count)
        else:
            return self._ping_unix(ip, count)
    
    def _ping_windows(self, ip: str, count: int) -> Dict[str, Any]:
        """Windows ping implementation."""
        import subprocess
        
        try:
            result = subprocess.run(
                ['ping', '-n', str(count), ip],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            output = result.stdout
            
            # Parse Windows ping output
            if 'Received = 0' in output or 'could not find host' in output:
                return {'success': False, 'packet_loss': 100}
            
            # Extract RTT
            import re
            rtt_match = re.search(r'Average = (\d+)ms', output)
            rtt = int(rtt_match.group(1)) if rtt_match else None
            
            # Extract packet loss
            loss_match = re.search(r'\((\d+)% loss\)', output)
            packet_loss = int(loss_match.group(1)) if loss_match else 0
            
            return {
                'success': packet_loss < 100,
                'rtt': rtt,
                'packet_loss': packet_loss
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _ping_unix(self, ip: str, count: int) -> Dict[str, Any]:
        """Unix/Linux ping implementation."""
        import subprocess
        
        try:
            result = subprocess.run(
                ['ping', '-c', str(count), '-W', '1', ip],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            output = result.stdout
            
            # Parse Unix ping output
            if '0 received' in output or 'Unreachable' in output:
                return {'success': False, 'packet_loss': 100}
            
            # Extract RTT
            import re
            rtt_match = re.search(r'avg = ([\d.]+)', output)
            rtt = float(rtt_match.group(1)) if rtt_match else None
            
            # Extract packet loss
            loss_match = re.search(r'(\d+)% packet loss', output)
            packet_loss = int(loss_match.group(1)) if loss_match else 0
            
            return {
                'success': packet_loss < 100,
                'rtt': rtt,
                'packet_loss': packet_loss
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}


class WindowsSystemCollector:
    """Windows system metrics collector."""
    
    def collect(self) -> Dict[str, Any]:
        """Collect Windows system metrics."""
        try:
            import wmi
            c = wmi.WMI()
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('C:\\')
            
            # Network interfaces
            network = psutil.net_io_counters()
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available': memory.available,
                'disk_percent': disk.percent,
                'disk_free': disk.free,
                'network_bytes_sent': network.bytes_sent,
                'network_bytes_recv': network.bytes_recv
            }
            
        except Exception as e:
            return {'error': str(e)}


class LinuxSystemCollector:
    """Linux system metrics collector."""
    
    def collect(self) -> Dict[str, Any]:
        """Collect Linux system metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Network interfaces
            network = psutil.net_io_counters()
            
            # Load average
            load_avg = os.getloadavg()
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available': memory.available,
                'disk_percent': disk.percent,
                'disk_free': disk.free,
                'network_bytes_sent': network.bytes_sent,
                'network_bytes_recv': network.bytes_recv,
                'load_avg_1': load_avg[0],
                'load_avg_5': load_avg[1],
                'load_avg_15': load_avg[2]
            }
            
        except Exception as e:
            return {'error': str(e)}