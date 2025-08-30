"""
Network Monitoring Service
Provides real-time network monitoring, performance metrics, and alerting.
"""

import time
import threading
import queue
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics
import ipaddress
import socket
import subprocess
import platform

from src.database import db, Device, VLAN


class MetricType(Enum):
    """Types of network metrics."""
    LATENCY = "latency"
    PACKET_LOSS = "packet_loss"
    BANDWIDTH = "bandwidth"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    INTERFACE_STATUS = "interface_status"
    TEMPERATURE = "temperature"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class NetworkMetric:
    """Represents a network metric measurement."""
    device_id: int
    metric_type: MetricType
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NetworkAlert:
    """Represents a network alert."""
    device_id: Optional[int]
    severity: AlertSeverity
    title: str
    message: str
    metric_type: Optional[MetricType]
    value: Optional[float]
    threshold: Optional[float]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    acknowledged: bool = False
    resolved: bool = False


class ThresholdConfig:
    """Configuration for metric thresholds."""
    
    DEFAULT_THRESHOLDS = {
        MetricType.LATENCY: {
            "warning": 100,  # ms
            "critical": 500  # ms
        },
        MetricType.PACKET_LOSS: {
            "warning": 1,    # %
            "critical": 5    # %
        },
        MetricType.CPU_USAGE: {
            "warning": 70,   # %
            "critical": 90   # %
        },
        MetricType.MEMORY_USAGE: {
            "warning": 80,   # %
            "critical": 95   # %
        },
        MetricType.TEMPERATURE: {
            "warning": 60,   # Celsius
            "critical": 75   # Celsius
        }
    }
    
    def __init__(self):
        self.thresholds = self.DEFAULT_THRESHOLDS.copy()
    
    def get_threshold(self, metric_type: MetricType, level: str) -> Optional[float]:
        """Get threshold value for a metric type and level."""
        if metric_type in self.thresholds:
            return self.thresholds[metric_type].get(level)
        return None
    
    def set_threshold(self, metric_type: MetricType, level: str, value: float):
        """Set threshold value for a metric type and level."""
        if metric_type not in self.thresholds:
            self.thresholds[metric_type] = {}
        self.thresholds[metric_type][level] = value


class NetworkMonitor:
    """Main network monitoring service."""
    
    def __init__(self):
        self.metrics_queue = queue.Queue()
        self.alerts_queue = queue.Queue()
        self.metrics_history: Dict[int, List[NetworkMetric]] = {}
        self.active_alerts: List[NetworkAlert] = []
        self.threshold_config = ThresholdConfig()
        self.monitoring_enabled = False
        self.monitoring_thread = None
        self.monitored_devices: List[Device] = []
        
    def start_monitoring(self, interval: int = 60):
        """Start the monitoring service."""
        if self.monitoring_enabled:
            return
        
        self.monitoring_enabled = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval,),
            daemon=True
        )
        self.monitoring_thread.start()
        print(f"Network monitoring started with {interval}s interval")
    
    def stop_monitoring(self):
        """Stop the monitoring service."""
        self.monitoring_enabled = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        print("Network monitoring stopped")
    
    def _monitoring_loop(self, interval: int):
        """Main monitoring loop."""
        while self.monitoring_enabled:
            try:
                # Get all active devices
                self.monitored_devices = Device.query.filter_by(status='active').all()
                
                for device in self.monitored_devices:
                    # Collect metrics for each device
                    self._collect_device_metrics(device)
                
                # Process metrics and generate alerts
                self._process_metrics()
                
                # Clean old metrics
                self._cleanup_old_metrics()
                
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
            
            time.sleep(interval)
    
    def _collect_device_metrics(self, device: Device):
        """Collect metrics for a specific device."""
        # Ping test for latency and packet loss
        latency, packet_loss = self._ping_device(device.ip_address)
        
        if latency is not None:
            self.metrics_queue.put(NetworkMetric(
                device_id=device.id,
                metric_type=MetricType.LATENCY,
                value=latency,
                unit="ms"
            ))
        
        if packet_loss is not None:
            self.metrics_queue.put(NetworkMetric(
                device_id=device.id,
                metric_type=MetricType.PACKET_LOSS,
                value=packet_loss,
                unit="%"
            ))
        
        # Simulate other metrics (in production, these would come from SNMP)
        import random
        
        # CPU usage
        self.metrics_queue.put(NetworkMetric(
            device_id=device.id,
            metric_type=MetricType.CPU_USAGE,
            value=random.uniform(10, 90),
            unit="%"
        ))
        
        # Memory usage
        self.metrics_queue.put(NetworkMetric(
            device_id=device.id,
            metric_type=MetricType.MEMORY_USAGE,
            value=random.uniform(30, 95),
            unit="%"
        ))
    
    def _ping_device(self, ip_address: str, count: int = 4) -> Tuple[Optional[float], Optional[float]]:
        """Ping a device and return latency and packet loss."""
        try:
            # Platform-specific ping command
            param = "-n" if platform.system().lower() == "windows" else "-c"
            
            # Run ping command
            result = subprocess.run(
                ["ping", param, str(count), ip_address],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                output = result.stdout
                
                # Parse latency (works for most ping implementations)
                import re
                
                # Extract average latency
                latency_pattern = r"(?:Average|avg).*?(\d+\.?\d*)\s*ms"
                latency_match = re.search(latency_pattern, output, re.IGNORECASE)
                latency = float(latency_match.group(1)) if latency_match else None
                
                # Extract packet loss
                loss_pattern = r"(\d+)%\s+(?:packet\s+)?loss"
                loss_match = re.search(loss_pattern, output, re.IGNORECASE)
                packet_loss = float(loss_match.group(1)) if loss_match else 0.0
                
                return latency, packet_loss
            else:
                # Device unreachable
                return None, 100.0
                
        except (subprocess.TimeoutExpired, Exception):
            return None, None
    
    def _process_metrics(self):
        """Process metrics from the queue and generate alerts."""
        while not self.metrics_queue.empty():
            metric = self.metrics_queue.get()
            
            # Store metric in history
            if metric.device_id not in self.metrics_history:
                self.metrics_history[metric.device_id] = []
            self.metrics_history[metric.device_id].append(metric)
            
            # Check thresholds and generate alerts
            self._check_thresholds(metric)
    
    def _check_thresholds(self, metric: NetworkMetric):
        """Check if metric exceeds thresholds and generate alerts."""
        warning_threshold = self.threshold_config.get_threshold(metric.metric_type, "warning")
        critical_threshold = self.threshold_config.get_threshold(metric.metric_type, "critical")
        
        device = Device.query.get(metric.device_id)
        if not device:
            return
        
        alert = None
        
        if critical_threshold and metric.value >= critical_threshold:
            alert = NetworkAlert(
                device_id=metric.device_id,
                severity=AlertSeverity.CRITICAL,
                title=f"Critical {metric.metric_type.value} on {device.hostname}",
                message=f"{metric.metric_type.value} is {metric.value}{metric.unit} (threshold: {critical_threshold}{metric.unit})",
                metric_type=metric.metric_type,
                value=metric.value,
                threshold=critical_threshold
            )
        elif warning_threshold and metric.value >= warning_threshold:
            alert = NetworkAlert(
                device_id=metric.device_id,
                severity=AlertSeverity.HIGH,
                title=f"High {metric.metric_type.value} on {device.hostname}",
                message=f"{metric.metric_type.value} is {metric.value}{metric.unit} (threshold: {warning_threshold}{metric.unit})",
                metric_type=metric.metric_type,
                value=metric.value,
                threshold=warning_threshold
            )
        
        if alert:
            self.alerts_queue.put(alert)
            self.active_alerts.append(alert)
    
    def _cleanup_old_metrics(self, retention_hours: int = 24):
        """Remove metrics older than retention period."""
        cutoff_time = datetime.utcnow() - timedelta(hours=retention_hours)
        
        for device_id in self.metrics_history:
            self.metrics_history[device_id] = [
                m for m in self.metrics_history[device_id]
                if m.timestamp > cutoff_time
            ]
    
    def get_device_metrics(self, device_id: int, 
                          metric_type: Optional[MetricType] = None,
                          hours: int = 1) -> List[NetworkMetric]:
        """Get metrics for a specific device."""
        if device_id not in self.metrics_history:
            return []
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        metrics = self.metrics_history[device_id]
        
        # Filter by time
        metrics = [m for m in metrics if m.timestamp > cutoff_time]
        
        # Filter by type if specified
        if metric_type:
            metrics = [m for m in metrics if m.metric_type == metric_type]
        
        return sorted(metrics, key=lambda m: m.timestamp)
    
    def get_device_statistics(self, device_id: int, hours: int = 1) -> Dict[str, Any]:
        """Get statistical summary of device metrics."""
        metrics = self.get_device_metrics(device_id, hours=hours)
        
        if not metrics:
            return {}
        
        stats = {}
        
        # Group metrics by type
        by_type = {}
        for metric in metrics:
            if metric.metric_type not in by_type:
                by_type[metric.metric_type] = []
            by_type[metric.metric_type].append(metric.value)
        
        # Calculate statistics for each metric type
        for metric_type, values in by_type.items():
            if values:
                stats[metric_type.value] = {
                    "current": values[-1],
                    "min": min(values),
                    "max": max(values),
                    "avg": statistics.mean(values),
                    "median": statistics.median(values),
                    "samples": len(values)
                }
        
        return stats
    
    def get_network_health_score(self) -> float:
        """Calculate overall network health score (0-100)."""
        if not self.monitored_devices:
            return 100.0
        
        scores = []
        
        for device in self.monitored_devices:
            device_score = 100.0
            stats = self.get_device_statistics(device.id, hours=1)
            
            # Deduct points based on metrics
            if "latency" in stats:
                latency_avg = stats["latency"]["avg"]
                if latency_avg > 500:
                    device_score -= 30
                elif latency_avg > 100:
                    device_score -= 15
            
            if "packet_loss" in stats:
                loss_avg = stats["packet_loss"]["avg"]
                if loss_avg > 5:
                    device_score -= 40
                elif loss_avg > 1:
                    device_score -= 20
            
            if "cpu_usage" in stats:
                cpu_avg = stats["cpu_usage"]["avg"]
                if cpu_avg > 90:
                    device_score -= 25
                elif cpu_avg > 70:
                    device_score -= 10
            
            scores.append(max(0, device_score))
        
        return statistics.mean(scores) if scores else 100.0
    
    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[NetworkAlert]:
        """Get active (unresolved) alerts."""
        alerts = [a for a in self.active_alerts if not a.resolved]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)
    
    def acknowledge_alert(self, alert_index: int) -> bool:
        """Acknowledge an alert."""
        if 0 <= alert_index < len(self.active_alerts):
            self.active_alerts[alert_index].acknowledged = True
            return True
        return False
    
    def resolve_alert(self, alert_index: int) -> bool:
        """Resolve an alert."""
        if 0 <= alert_index < len(self.active_alerts):
            self.active_alerts[alert_index].resolved = True
            return True
        return False
    
    def get_summary_report(self) -> Dict[str, Any]:
        """Get a summary report of network monitoring."""
        total_devices = len(self.monitored_devices)
        active_devices = sum(1 for d in self.monitored_devices if d.status == 'active')
        
        # Count alerts by severity
        alert_counts = {
            "critical": len([a for a in self.active_alerts if a.severity == AlertSeverity.CRITICAL and not a.resolved]),
            "high": len([a for a in self.active_alerts if a.severity == AlertSeverity.HIGH and not a.resolved]),
            "medium": len([a for a in self.active_alerts if a.severity == AlertSeverity.MEDIUM and not a.resolved]),
            "low": len([a for a in self.active_alerts if a.severity == AlertSeverity.LOW and not a.resolved]),
            "info": len([a for a in self.active_alerts if a.severity == AlertSeverity.INFO and not a.resolved])
        }
        
        return {
            "health_score": self.get_network_health_score(),
            "total_devices": total_devices,
            "active_devices": active_devices,
            "monitoring_enabled": self.monitoring_enabled,
            "total_alerts": len(self.active_alerts),
            "unresolved_alerts": sum(alert_counts.values()),
            "alert_breakdown": alert_counts,
            "metrics_collected": sum(len(metrics) for metrics in self.metrics_history.values()),
            "monitored_device_types": list(set(d.device_type for d in self.monitored_devices if d.device_type))
        }


# Global monitor instance
network_monitor = NetworkMonitor()