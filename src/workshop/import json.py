import json
from datetime import datetime
from typing import Dict, Any, Optional

# ... existing imports ...

def parse_monitoring_alert(alert_json: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """
    Parse the JSON payload from the Monitoring Agent and extract relevant fields.
    """
    service = alert_json.get("application_name", "unknown")
    region = "unknown"  # Region is not provided in the payload
    severity = "Medium"  # Default severity
    timestamp = alert_json.get("detection_time", datetime.now(CET_ZONE).isoformat())
    title = alert_json.get("title", "No Title Provided")
    description = alert_json.get("short_description", "No Description Provided")
    logs = alert_json.get("related_log_lines", [])

    return {
        "service": service,
        "region": region,
        "severity": severity,
        "timestamp": timestamp,
        "title": title,
        "description": description,
        "logs": logs,
    }


def create_incident_ticket_from_alert(alert_json: Dict[str, Any]) -> dict:
    """
    Create an incident ticket from the Monitoring Agent's JSON payload.
    """
    parsed_alert = parse_monitoring_alert(alert_json)
    incident_id = str(uuid.uuid4())
    created_at = datetime.now(CET_ZONE).isoformat()

    ticket = {
        "id": incident_id,
        "title": parsed_alert["title"],
        "summary": parsed_alert["description"],
        "created_at": created_at,
        "status": "open",
        "triage": {
            "service": parsed_alert["service"],
            "region": parsed_alert["region"],
            "severity": parsed_alert["severity"],
            "timestamp": parsed_alert["timestamp"],
        },
        "logs": parsed_alert["logs"],
        "raised_by": RAISED_BY,
    }
    return ticket