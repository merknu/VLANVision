"""
Metrics collection and storage system
"""

from enum import Enum
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Index
from sqlalchemy.ext.declarative import declarative_base

from src.database import db

Base = declarative_base()


class MetricType(Enum):
    """Types of metrics collected."""
    AVAILABILITY = "availability"
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    INTERFACE = "interface"
    TEMPERATURE = "temperature"
    POWER = "power"
    UPTIME = "uptime"
    BANDWIDTH = "bandwidth"
    PACKET_LOSS = "packet_loss"
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    CUSTOM = "custom"


class Metric(db.Model):
    """Time-series metric data."""
    __tablename__ = 'metrics'
    
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, db.ForeignKey('devices.id'), nullable=False)
    metric_type = Column(String(50), nullable=False)
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    metadata = Column(JSON)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_device_metric_time', 'device_id', 'metric_type', 'timestamp'),
        Index('idx_timestamp', 'timestamp'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'device_id': self.device_id,
            'metric_type': self.metric_type,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }


class Alert(db.Model):
    """Alert definitions and thresholds."""
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    device_id = Column(Integer, db.ForeignKey('devices.id'))
    metric_type = Column(String(50), nullable=False)
    condition = Column(String(20), nullable=False)  # gt, lt, eq, ne
    threshold = Column(Float, nullable=False)
    duration = Column(Integer, default=0)  # seconds
    enabled = Column(db.Boolean, default=True)
    severity = Column(String(20), default='warning')  # info, warning, critical
    notification_channels = Column(JSON)  # email, webhook, sms
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def evaluate(self, value: float) -> bool:
        """Evaluate if alert condition is met."""
        if not self.enabled:
            return False
        
        conditions = {
            'gt': value > self.threshold,
            'lt': value < self.threshold,
            'eq': value == self.threshold,
            'ne': value != self.threshold,
            'gte': value >= self.threshold,
            'lte': value <= self.threshold
        }
        
        return conditions.get(self.condition, False)


class AlertEvent(db.Model):
    """Alert event history."""
    __tablename__ = 'alert_events'
    
    id = Column(Integer, primary_key=True)
    alert_id = Column(Integer, db.ForeignKey('alerts.id'), nullable=False)
    device_id = Column(Integer, db.ForeignKey('devices.id'))
    triggered_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)
    value = Column(Float)
    status = Column(String(20), default='active')  # active, acknowledged, resolved
    acknowledged_by = Column(Integer, db.ForeignKey('users.id'))
    notes = Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'alert_id': self.alert_id,
            'device_id': self.device_id,
            'triggered_at': self.triggered_at.isoformat(),
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'value': self.value,
            'status': self.status,
            'duration': self.duration_seconds()
        }
    
    def duration_seconds(self) -> Optional[int]:
        """Calculate alert duration in seconds."""
        if not self.resolved_at:
            return int((datetime.utcnow() - self.triggered_at).total_seconds())
        return int((self.resolved_at - self.triggered_at).total_seconds())


class MetricsCollector:
    """Collects and stores metrics."""
    
    def __init__(self):
        self.alert_manager = AlertManager()
    
    def store_metric(self, device_id: int, metric_type: MetricType, 
                    value: float, metadata: Dict = None) -> Metric:
        """Store a single metric."""
        metric = Metric(
            device_id=device_id,
            metric_type=metric_type.value,
            value=value,
            timestamp=datetime.utcnow(),
            metadata=metadata
        )
        
        db.session.add(metric)
        db.session.commit()
        
        # Check alerts
        self.alert_manager.check_metric(device_id, metric_type, value)
        
        return metric
    
    def store_metrics_batch(self, metrics: List[Dict[str, Any]]) -> int:
        """Store multiple metrics efficiently."""
        metric_objects = []
        
        for m in metrics:
            metric = Metric(
                device_id=m['device_id'],
                metric_type=m['metric_type'],
                value=m['value'],
                timestamp=m.get('timestamp', datetime.utcnow()),
                metadata=m.get('metadata')
            )
            metric_objects.append(metric)
        
        db.session.bulk_save_objects(metric_objects)
        db.session.commit()
        
        # Check alerts for each metric
        for m in metrics:
            self.alert_manager.check_metric(
                m['device_id'], 
                MetricType(m['metric_type']), 
                m['value']
            )
        
        return len(metric_objects)
    
    def get_metrics(self, device_id: int, metric_type: MetricType,
                   start_time: datetime = None, end_time: datetime = None,
                   limit: int = 1000) -> List[Metric]:
        """Retrieve metrics for a device."""
        query = Metric.query.filter_by(
            device_id=device_id,
            metric_type=metric_type.value
        )
        
        if start_time:
            query = query.filter(Metric.timestamp >= start_time)
        
        if end_time:
            query = query.filter(Metric.timestamp <= end_time)
        
        return query.order_by(Metric.timestamp.desc()).limit(limit).all()
    
    def get_latest_metric(self, device_id: int, metric_type: MetricType) -> Optional[Metric]:
        """Get the most recent metric value."""
        return Metric.query.filter_by(
            device_id=device_id,
            metric_type=metric_type.value
        ).order_by(Metric.timestamp.desc()).first()
    
    def get_metric_summary(self, device_id: int, metric_type: MetricType,
                          hours: int = 24) -> Dict[str, Any]:
        """Get metric summary statistics."""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        metrics = self.get_metrics(
            device_id, metric_type, 
            start_time=start_time
        )
        
        if not metrics:
            return {}
        
        values = [m.value for m in metrics]
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'latest': values[0],
            'first_timestamp': metrics[-1].timestamp.isoformat(),
            'last_timestamp': metrics[0].timestamp.isoformat()
        }
    
    def cleanup_old_metrics(self, days: int = 30) -> int:
        """Remove metrics older than specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        deleted = Metric.query.filter(
            Metric.timestamp < cutoff_date
        ).delete()
        
        db.session.commit()
        
        return deleted


class AlertManager:
    """Manages alerts and notifications."""
    
    def __init__(self):
        self.notification_handlers = {
            'email': self._send_email_notification,
            'webhook': self._send_webhook_notification,
            'sms': self._send_sms_notification
        }
    
    def check_metric(self, device_id: int, metric_type: MetricType, value: float):
        """Check if metric triggers any alerts."""
        alerts = Alert.query.filter_by(
            device_id=device_id,
            metric_type=metric_type.value,
            enabled=True
        ).all()
        
        for alert in alerts:
            if alert.evaluate(value):
                self._trigger_alert(alert, value)
            else:
                self._resolve_alert(alert)
    
    def _trigger_alert(self, alert: Alert, value: float):
        """Trigger an alert."""
        # Check if alert is already active
        active_event = AlertEvent.query.filter_by(
            alert_id=alert.id,
            status='active'
        ).first()
        
        if active_event:
            # Alert already active, update value if needed
            return
        
        # Create new alert event
        event = AlertEvent(
            alert_id=alert.id,
            device_id=alert.device_id,
            value=value,
            status='active'
        )
        
        db.session.add(event)
        db.session.commit()
        
        # Send notifications
        self._send_notifications(alert, event)
    
    def _resolve_alert(self, alert: Alert):
        """Resolve an active alert."""
        active_event = AlertEvent.query.filter_by(
            alert_id=alert.id,
            status='active'
        ).first()
        
        if active_event:
            active_event.status = 'resolved'
            active_event.resolved_at = datetime.utcnow()
            db.session.commit()
            
            # Send resolution notification
            self._send_resolution_notification(alert, active_event)
    
    def _send_notifications(self, alert: Alert, event: AlertEvent):
        """Send alert notifications."""
        if not alert.notification_channels:
            return
        
        for channel, config in alert.notification_channels.items():
            handler = self.notification_handlers.get(channel)
            if handler:
                handler(alert, event, config)
    
    def _send_email_notification(self, alert: Alert, event: AlertEvent, config: Dict):
        """Send email notification."""
        # Implementation would use SMTP
        pass
    
    def _send_webhook_notification(self, alert: Alert, event: AlertEvent, config: Dict):
        """Send webhook notification."""
        import requests
        
        webhook_url = config.get('url')
        if not webhook_url:
            return
        
        payload = {
            'alert': alert.name,
            'device_id': alert.device_id,
            'metric_type': alert.metric_type,
            'value': event.value,
            'threshold': alert.threshold,
            'severity': alert.severity,
            'timestamp': event.triggered_at.isoformat()
        }
        
        try:
            requests.post(webhook_url, json=payload, timeout=10)
        except Exception as e:
            logging.error(f"Webhook notification failed: {e}")
    
    def _send_sms_notification(self, alert: Alert, event: AlertEvent, config: Dict):
        """Send SMS notification."""
        # Implementation would use SMS service (Twilio, etc.)
        pass
    
    def _send_resolution_notification(self, alert: Alert, event: AlertEvent):
        """Send notification when alert is resolved."""
        # Similar to _send_notifications but for resolution
        pass
    
    def acknowledge_alert(self, event_id: int, user_id: int, notes: str = None):
        """Acknowledge an alert event."""
        event = AlertEvent.query.get(event_id)
        if event and event.status == 'active':
            event.status = 'acknowledged'
            event.acknowledged_by = user_id
            event.notes = notes
            db.session.commit()
    
    def get_active_alerts(self) -> List[AlertEvent]:
        """Get all active alert events."""
        return AlertEvent.query.filter_by(status='active').all()
    
    def get_alert_history(self, hours: int = 24) -> List[AlertEvent]:
        """Get alert history."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return AlertEvent.query.filter(
            AlertEvent.triggered_at >= cutoff
        ).order_by(AlertEvent.triggered_at.desc()).all()