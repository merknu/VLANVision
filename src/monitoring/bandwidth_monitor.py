"""
Real-time Bandwidth Monitoring and Traffic Analysis
Monitors network interface utilization, traffic patterns, and provides analytics.
"""

import time
import threading
import queue
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics
from collections import deque

from pysnmp.hlapi import *
import numpy as np


class TrafficDirection(Enum):
    """Direction of network traffic."""
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    BIDIRECTIONAL = "bidirectional"


class TrafficType(Enum):
    """Types of network traffic."""
    UNICAST = "unicast"
    BROADCAST = "broadcast"
    MULTICAST = "multicast"
    UNKNOWN = "unknown"


@dataclass
class BandwidthSample:
    """Single bandwidth measurement sample."""
    device_id: int
    interface: str
    timestamp: datetime
    bytes_in: int
    bytes_out: int
    packets_in: int
    packets_out: int
    errors_in: int
    errors_out: int
    discards_in: int
    discards_out: int
    speed: Optional[int] = None  # Interface speed in bits per second
    
    def calculate_utilization(self, previous_sample: 'BandwidthSample') -> Dict[str, float]:
        """Calculate bandwidth utilization between two samples."""
        if not previous_sample or not self.speed:
            return {}
        
        time_delta = (self.timestamp - previous_sample.timestamp).total_seconds()
        if time_delta <= 0:
            return {}
        
        # Calculate bits per second
        bits_in = (self.bytes_in - previous_sample.bytes_in) * 8 / time_delta
        bits_out = (self.bytes_out - previous_sample.bytes_out) * 8 / time_delta
        
        # Calculate utilization percentage
        util_in = (bits_in / self.speed) * 100 if self.speed > 0 else 0
        util_out = (bits_out / self.speed) * 100 if self.speed > 0 else 0
        
        # Calculate packets per second
        pps_in = (self.packets_in - previous_sample.packets_in) / time_delta
        pps_out = (self.packets_out - previous_sample.packets_out) / time_delta
        
        # Calculate error rates
        errors_in = (self.errors_in - previous_sample.errors_in) / time_delta
        errors_out = (self.errors_out - previous_sample.errors_out) / time_delta
        
        return {
            'bps_in': bits_in,
            'bps_out': bits_out,
            'utilization_in': min(util_in, 100),  # Cap at 100%
            'utilization_out': min(util_out, 100),
            'pps_in': pps_in,
            'pps_out': pps_out,
            'error_rate_in': errors_in,
            'error_rate_out': errors_out
        }


@dataclass
class TrafficPattern:
    """Identified traffic pattern."""
    pattern_type: str
    confidence: float
    start_time: datetime
    end_time: Optional[datetime]
    characteristics: Dict[str, Any]
    anomaly_score: float = 0.0


class BandwidthMonitor:
    """Real-time bandwidth monitoring service."""
    
    # SNMP OIDs for interface statistics
    OID_IF_DESCR = '1.3.6.1.2.1.2.2.1.2'           # Interface description
    OID_IF_SPEED = '1.3.6.1.2.1.2.2.1.5'           # Interface speed
    OID_IF_IN_OCTETS = '1.3.6.1.2.1.2.2.1.10'      # Inbound bytes
    OID_IF_OUT_OCTETS = '1.3.6.1.2.1.2.2.1.16'     # Outbound bytes
    OID_IF_IN_UCAST = '1.3.6.1.2.1.2.2.1.11'       # Inbound unicast packets
    OID_IF_OUT_UCAST = '1.3.6.1.2.1.2.2.1.17'      # Outbound unicast packets
    OID_IF_IN_ERRORS = '1.3.6.1.2.1.2.2.1.14'      # Inbound errors
    OID_IF_OUT_ERRORS = '1.3.6.1.2.1.2.2.1.20'     # Outbound errors
    OID_IF_IN_DISCARDS = '1.3.6.1.2.1.2.2.1.13'    # Inbound discards
    OID_IF_OUT_DISCARDS = '1.3.6.1.2.1.2.2.1.19'   # Outbound discards
    
    # High-capacity counters (64-bit) for high-speed interfaces
    OID_IF_HC_IN_OCTETS = '1.3.6.1.2.1.31.1.1.1.6'   # 64-bit inbound bytes
    OID_IF_HC_OUT_OCTETS = '1.3.6.1.2.1.31.1.1.1.10'  # 64-bit outbound bytes
    
    def __init__(self, snmp_community: str = 'public'):
        self.snmp_community = snmp_community
        self.monitoring_enabled = False
        self.monitored_interfaces: Dict[str, Dict[str, Any]] = {}
        self.bandwidth_history: Dict[str, deque] = {}
        self.traffic_patterns: Dict[str, List[TrafficPattern]] = {}
        self.monitoring_thread = None
        self.sample_interval = 10  # seconds
        self.history_size = 360  # Keep 1 hour of 10-second samples
        
    def start_monitoring(self, devices: List[Dict[str, Any]], interval: int = 10):
        """
        Start bandwidth monitoring for specified devices.
        
        Args:
            devices: List of device configurations with IP and interfaces
            interval: Sampling interval in seconds
        """
        self.sample_interval = interval
        self.monitoring_enabled = True
        
        # Initialize monitoring for each device/interface
        for device in devices:
            device_ip = device['ip']
            interfaces = device.get('interfaces', [])
            
            if not interfaces:
                # Discover all interfaces
                interfaces = self._discover_interfaces(device_ip)
            
            for interface in interfaces:
                key = f"{device_ip}:{interface}"
                self.monitored_interfaces[key] = {
                    'device_ip': device_ip,
                    'device_id': device.get('id'),
                    'interface': interface,
                    'last_sample': None
                }
                self.bandwidth_history[key] = deque(maxlen=self.history_size)
        
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitoring_thread.start()
        print(f"Bandwidth monitoring started for {len(self.monitored_interfaces)} interfaces")
    
    def stop_monitoring(self):
        """Stop bandwidth monitoring."""
        self.monitoring_enabled = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        print("Bandwidth monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_enabled:
            start_time = time.time()
            
            # Collect samples from all interfaces
            for key, interface_info in self.monitored_interfaces.items():
                try:
                    sample = self._collect_interface_sample(
                        interface_info['device_ip'],
                        interface_info['interface'],
                        interface_info.get('device_id')
                    )
                    
                    if sample:
                        # Calculate utilization if we have a previous sample
                        if interface_info['last_sample']:
                            metrics = sample.calculate_utilization(interface_info['last_sample'])
                            sample.metrics = metrics
                        
                        # Store sample
                        self.bandwidth_history[key].append(sample)
                        interface_info['last_sample'] = sample
                        
                        # Analyze traffic patterns
                        self._analyze_traffic_patterns(key)
                        
                except Exception as e:
                    print(f"Error monitoring {key}: {e}")
            
            # Sleep for the remaining interval time
            elapsed = time.time() - start_time
            if elapsed < self.sample_interval:
                time.sleep(self.sample_interval - elapsed)
    
    def _discover_interfaces(self, device_ip: str) -> List[str]:
        """Discover network interfaces on a device."""
        interfaces = []
        
        try:
            # Get interface descriptions
            for (errorIndication, errorStatus, errorIndex, varBinds) in nextCmd(
                SnmpEngine(),
                CommunityData(self.snmp_community),
                UdpTransportTarget((device_ip, 161), timeout=2, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(self.OID_IF_DESCR)),
                lexicographicMode=False
            ):
                if errorIndication or errorStatus:
                    break
                
                for varBind in varBinds:
                    interface_name = str(varBind[1])
                    # Filter out virtual/loopback interfaces
                    if not any(x in interface_name.lower() for x in ['null', 'loopback']):
                        interfaces.append(interface_name)
        
        except Exception as e:
            print(f"Error discovering interfaces on {device_ip}: {e}")
        
        return interfaces[:10]  # Limit to first 10 interfaces
    
    def _collect_interface_sample(self, device_ip: str, interface: str, 
                                 device_id: Optional[int] = None) -> Optional[BandwidthSample]:
        """Collect bandwidth sample for a specific interface."""
        try:
            # Get interface index
            if_index = self._get_interface_index(device_ip, interface)
            if not if_index:
                return None
            
            # Collect metrics via SNMP
            metrics = {}
            oids = [
                (self.OID_IF_SPEED, 'speed'),
                (self.OID_IF_HC_IN_OCTETS, 'bytes_in'),
                (self.OID_IF_HC_OUT_OCTETS, 'bytes_out'),
                (self.OID_IF_IN_UCAST, 'packets_in'),
                (self.OID_IF_OUT_UCAST, 'packets_out'),
                (self.OID_IF_IN_ERRORS, 'errors_in'),
                (self.OID_IF_OUT_ERRORS, 'errors_out'),
                (self.OID_IF_IN_DISCARDS, 'discards_in'),
                (self.OID_IF_OUT_DISCARDS, 'discards_out')
            ]
            
            for oid_base, metric_name in oids:
                oid = f"{oid_base}.{if_index}"
                value = self._snmp_get(device_ip, oid)
                if value is not None:
                    try:
                        metrics[metric_name] = int(value)
                    except ValueError:
                        metrics[metric_name] = 0
            
            # Fall back to 32-bit counters if HC counters not available
            if 'bytes_in' not in metrics:
                value = self._snmp_get(device_ip, f"{self.OID_IF_IN_OCTETS}.{if_index}")
                metrics['bytes_in'] = int(value) if value else 0
            
            if 'bytes_out' not in metrics:
                value = self._snmp_get(device_ip, f"{self.OID_IF_OUT_OCTETS}.{if_index}")
                metrics['bytes_out'] = int(value) if value else 0
            
            # Create sample
            sample = BandwidthSample(
                device_id=device_id or 0,
                interface=interface,
                timestamp=datetime.utcnow(),
                bytes_in=metrics.get('bytes_in', 0),
                bytes_out=metrics.get('bytes_out', 0),
                packets_in=metrics.get('packets_in', 0),
                packets_out=metrics.get('packets_out', 0),
                errors_in=metrics.get('errors_in', 0),
                errors_out=metrics.get('errors_out', 0),
                discards_in=metrics.get('discards_in', 0),
                discards_out=metrics.get('discards_out', 0),
                speed=metrics.get('speed', 0)
            )
            
            return sample
            
        except Exception as e:
            print(f"Error collecting sample for {device_ip}:{interface}: {e}")
            return None
    
    def _get_interface_index(self, device_ip: str, interface_name: str) -> Optional[int]:
        """Get SNMP interface index for a named interface."""
        try:
            # Query interface descriptions to find matching index
            for (errorIndication, errorStatus, errorIndex, varBinds) in nextCmd(
                SnmpEngine(),
                CommunityData(self.snmp_community),
                UdpTransportTarget((device_ip, 161), timeout=2, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(self.OID_IF_DESCR)),
                lexicographicMode=False
            ):
                if errorIndication or errorStatus:
                    break
                
                for varBind in varBinds:
                    oid = str(varBind[0])
                    value = str(varBind[1])
                    
                    if value == interface_name:
                        # Extract index from OID
                        return int(oid.split('.')[-1])
        
        except Exception:
            pass
        
        return None
    
    def _snmp_get(self, ip_address: str, oid: str) -> Optional[str]:
        """Perform SNMP GET operation."""
        try:
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(self.snmp_community),
                UdpTransportTarget((ip_address, 161), timeout=2, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(oid))
            )
            
            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            
            if not errorIndication and not errorStatus:
                for varBind in varBinds:
                    return str(varBind[1])
        except:
            pass
        
        return None
    
    def _analyze_traffic_patterns(self, interface_key: str):
        """Analyze traffic patterns for anomaly detection."""
        history = list(self.bandwidth_history.get(interface_key, []))
        if len(history) < 10:
            return
        
        # Extract utilization values
        util_values = []
        for sample in history[-30:]:  # Last 5 minutes
            if hasattr(sample, 'metrics') and sample.metrics:
                util_in = sample.metrics.get('utilization_in', 0)
                util_out = sample.metrics.get('utilization_out', 0)
                util_values.append(max(util_in, util_out))
        
        if not util_values:
            return
        
        # Detect patterns
        patterns = []
        
        # 1. Sustained high utilization
        if len(util_values) >= 10:
            recent_avg = statistics.mean(util_values[-10:])
            if recent_avg > 80:
                patterns.append(TrafficPattern(
                    pattern_type="high_utilization",
                    confidence=min(recent_avg / 100, 1.0),
                    start_time=history[-10].timestamp,
                    end_time=None,
                    characteristics={'average_utilization': recent_avg}
                ))
        
        # 2. Traffic spike detection
        if len(util_values) >= 20:
            baseline = statistics.mean(util_values[:-10])
            recent = statistics.mean(util_values[-10:])
            if baseline > 0 and recent > baseline * 2:
                patterns.append(TrafficPattern(
                    pattern_type="traffic_spike",
                    confidence=min((recent - baseline) / baseline, 1.0),
                    start_time=history[-10].timestamp,
                    end_time=None,
                    characteristics={
                        'baseline': baseline,
                        'spike_level': recent,
                        'increase_factor': recent / baseline
                    }
                ))
        
        # 3. Periodic pattern detection (simplified)
        if len(util_values) >= 36:  # 6 minutes of data
            # Check for repeating patterns every minute
            period_size = 6  # 1 minute with 10-second samples
            periods = [util_values[i:i+period_size] for i in range(0, len(util_values)-period_size, period_size)]
            
            if len(periods) >= 3:
                # Calculate correlation between periods
                correlations = []
                for i in range(len(periods)-1):
                    if len(periods[i]) == len(periods[i+1]):
                        corr = np.corrcoef(periods[i], periods[i+1])[0, 1]
                        correlations.append(corr)
                
                if correlations and statistics.mean(correlations) > 0.7:
                    patterns.append(TrafficPattern(
                        pattern_type="periodic",
                        confidence=statistics.mean(correlations),
                        start_time=history[-36].timestamp,
                        end_time=None,
                        characteristics={'period_minutes': 1, 'correlation': statistics.mean(correlations)}
                    ))
        
        # Store identified patterns
        if patterns:
            if interface_key not in self.traffic_patterns:
                self.traffic_patterns[interface_key] = []
            self.traffic_patterns[interface_key].extend(patterns)
            
            # Keep only recent patterns (last hour)
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            self.traffic_patterns[interface_key] = [
                p for p in self.traffic_patterns[interface_key]
                if p.start_time > cutoff_time
            ]
    
    def get_interface_statistics(self, interface_key: str, 
                                minutes: int = 5) -> Dict[str, Any]:
        """Get statistical summary for an interface."""
        history = list(self.bandwidth_history.get(interface_key, []))
        if not history:
            return {}
        
        # Filter by time
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        recent_samples = [s for s in history if s.timestamp > cutoff_time]
        
        if not recent_samples:
            return {}
        
        # Extract metrics
        util_in_values = []
        util_out_values = []
        bps_in_values = []
        bps_out_values = []
        error_rates = []
        
        for sample in recent_samples:
            if hasattr(sample, 'metrics') and sample.metrics:
                util_in_values.append(sample.metrics.get('utilization_in', 0))
                util_out_values.append(sample.metrics.get('utilization_out', 0))
                bps_in_values.append(sample.metrics.get('bps_in', 0))
                bps_out_values.append(sample.metrics.get('bps_out', 0))
                error_rates.append(
                    sample.metrics.get('error_rate_in', 0) + 
                    sample.metrics.get('error_rate_out', 0)
                )
        
        # Calculate statistics
        stats = {
            'interface': interface_key,
            'sample_count': len(recent_samples),
            'time_range_minutes': minutes
        }
        
        if util_in_values:
            stats['utilization_in'] = {
                'current': util_in_values[-1] if util_in_values else 0,
                'average': statistics.mean(util_in_values),
                'maximum': max(util_in_values),
                'minimum': min(util_in_values)
            }
        
        if util_out_values:
            stats['utilization_out'] = {
                'current': util_out_values[-1] if util_out_values else 0,
                'average': statistics.mean(util_out_values),
                'maximum': max(util_out_values),
                'minimum': min(util_out_values)
            }
        
        if bps_in_values:
            stats['bandwidth_in_mbps'] = {
                'current': bps_in_values[-1] / 1_000_000 if bps_in_values else 0,
                'average': statistics.mean(bps_in_values) / 1_000_000,
                'maximum': max(bps_in_values) / 1_000_000,
                'minimum': min(bps_in_values) / 1_000_000
            }
        
        if bps_out_values:
            stats['bandwidth_out_mbps'] = {
                'current': bps_out_values[-1] / 1_000_000 if bps_out_values else 0,
                'average': statistics.mean(bps_out_values) / 1_000_000,
                'maximum': max(bps_out_values) / 1_000_000,
                'minimum': min(bps_out_values) / 1_000_000
            }
        
        if error_rates:
            stats['error_rate'] = {
                'current': error_rates[-1] if error_rates else 0,
                'average': statistics.mean(error_rates),
                'total_errors': sum(error_rates)
            }
        
        # Add identified patterns
        patterns = self.traffic_patterns.get(interface_key, [])
        stats['patterns'] = [
            {
                'type': p.pattern_type,
                'confidence': p.confidence,
                'detected_at': p.start_time.isoformat(),
                'characteristics': p.characteristics
            }
            for p in patterns[-5:]  # Last 5 patterns
        ]
        
        return stats
    
    def get_top_interfaces(self, metric: str = 'utilization', 
                          count: int = 10) -> List[Dict[str, Any]]:
        """Get top interfaces by specified metric."""
        interface_metrics = []
        
        for interface_key, history in self.bandwidth_history.items():
            if not history:
                continue
            
            recent_samples = list(history)[-6:]  # Last minute
            if not recent_samples:
                continue
            
            # Calculate metric value
            metric_value = 0
            
            if metric == 'utilization':
                util_values = []
                for sample in recent_samples:
                    if hasattr(sample, 'metrics') and sample.metrics:
                        util_in = sample.metrics.get('utilization_in', 0)
                        util_out = sample.metrics.get('utilization_out', 0)
                        util_values.append(max(util_in, util_out))
                
                if util_values:
                    metric_value = statistics.mean(util_values)
            
            elif metric == 'bandwidth':
                bps_values = []
                for sample in recent_samples:
                    if hasattr(sample, 'metrics') and sample.metrics:
                        bps_in = sample.metrics.get('bps_in', 0)
                        bps_out = sample.metrics.get('bps_out', 0)
                        bps_values.append(bps_in + bps_out)
                
                if bps_values:
                    metric_value = statistics.mean(bps_values) / 1_000_000  # Convert to Mbps
            
            elif metric == 'errors':
                error_values = []
                for sample in recent_samples:
                    if hasattr(sample, 'metrics') and sample.metrics:
                        errors = (sample.metrics.get('error_rate_in', 0) + 
                                sample.metrics.get('error_rate_out', 0))
                        error_values.append(errors)
                
                if error_values:
                    metric_value = sum(error_values)
            
            interface_metrics.append({
                'interface': interface_key,
                'metric': metric,
                'value': metric_value,
                'last_updated': recent_samples[-1].timestamp.isoformat() if recent_samples else None
            })
        
        # Sort by metric value
        interface_metrics.sort(key=lambda x: x['value'], reverse=True)
        
        return interface_metrics[:count]
    
    def export_bandwidth_data(self, interface_key: str, 
                            format: str = 'csv') -> str:
        """Export bandwidth data for analysis."""
        history = list(self.bandwidth_history.get(interface_key, []))
        
        if format == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'Timestamp', 'Bytes In', 'Bytes Out', 'Packets In', 'Packets Out',
                'Utilization In (%)', 'Utilization Out (%)', 'BPS In', 'BPS Out',
                'Errors In', 'Errors Out'
            ])
            
            # Write data
            for sample in history:
                metrics = sample.metrics if hasattr(sample, 'metrics') else {}
                writer.writerow([
                    sample.timestamp.isoformat(),
                    sample.bytes_in,
                    sample.bytes_out,
                    sample.packets_in,
                    sample.packets_out,
                    metrics.get('utilization_in', ''),
                    metrics.get('utilization_out', ''),
                    metrics.get('bps_in', ''),
                    metrics.get('bps_out', ''),
                    sample.errors_in,
                    sample.errors_out
                ])
            
            return output.getvalue()
        
        elif format == 'json':
            import json
            
            export_data = []
            for sample in history:
                metrics = sample.metrics if hasattr(sample, 'metrics') else {}
                export_data.append({
                    'timestamp': sample.timestamp.isoformat(),
                    'bytes_in': sample.bytes_in,
                    'bytes_out': sample.bytes_out,
                    'packets_in': sample.packets_in,
                    'packets_out': sample.packets_out,
                    'utilization_in': metrics.get('utilization_in'),
                    'utilization_out': metrics.get('utilization_out'),
                    'bps_in': metrics.get('bps_in'),
                    'bps_out': metrics.get('bps_out'),
                    'errors_in': sample.errors_in,
                    'errors_out': sample.errors_out
                })
            
            return json.dumps(export_data, indent=2)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Global bandwidth monitor instance
bandwidth_monitor = BandwidthMonitor()