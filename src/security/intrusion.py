# Path: /src/security/intrusion.py
# This is the class for intrusion detection event and intrusion detection manager class
import json
import datetime


class IntrusionEvent:
    def __init__(self, timestamp, src_ip, dest_ip, severity, description):
        self.timestamp = timestamp
        self.src_ip = src_ip
        self.dest_ip = dest_ip
        self.severity = severity
        self.description = description

    def to_dict(self):
        return {
            'timestamp': self.timestamp.isoformat(),
            'src_ip': self.src_ip,
            'dest_ip': self.dest_ip,
            'severity': self.severity,
            'description': self.description
        }

    @staticmethod
    def from_dict(event_data):
        timestamp = datetime.datetime.fromisoformat(event_data['timestamp'])
        return IntrusionEvent(
            timestamp,
            event_data['src_ip'],
            event_data['dest_ip'],
            event_data['severity'],
            event_data['description']
        )


class IntrusionDetectionManager:
    def __init__(self, idps_data_file):
        self.idps_data_file = idps_data_file
        self.events = self.load_events()

    def load_events(self):
        try:
            with open(self.idps_data_file, 'r') as file:
                idps_data = json.load(file)
        except FileNotFoundError:
            idps_data = []

        events = []
        for event_dict in idps_data:
            event = IntrusionEvent.from_dict(event_dict)
            events.append(event)

        return events

    def save_events(self):
        idps_data = [event.to_dict() for event in self.events]
        with open(self.idps_data_file, 'w') as file:
            json.dump(idps_data, file, indent=2)

    def add_event(self, src_ip, dest_ip, severity, description):
        timestamp = datetime.datetime.now()
        event = IntrusionEvent(timestamp, src_ip, dest_ip, severity, description)
        self.events.append(event)
        self.save_events()

    def get_events(self, start_time=None, end_time=None):
        if start_time is None and end_time is None:
            return self.events

        filtered_events = []
        for event in self.events:
            if start_time is not None and event.timestamp < start_time:
                continue
            if end_time is not None and event.timestamp > end_time:
                continue
            filtered_events.append(event)

        return filtered_events
