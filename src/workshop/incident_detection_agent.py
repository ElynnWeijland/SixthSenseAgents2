import os
import re
import uuid
import json
import asyncio
import logging
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
    SLACK_AVAILABLE = True
except Exception:
    SLACK_AVAILABLE = False

try:
    from azure.identity import DefaultAzureCredential
    import httpx
    AZURE_MONITOR_AVAILABLE = True
except Exception as e:
    AZURE_MONITOR_AVAILABLE = False
    logger.debug(f"Azure Monitor dependencies not available: {e}")

# utils may provide project_client and helper constants; import if available but do not require it
try:
    from utils import project_client  # noqa: F401
except Exception:
    project_client = None

load_dotenv()
logger = logging.getLogger(__name__)

SLACK_TOKEN_ENV = "SLACK_BOT_TOKEN"
SLACK_CHANNEL_ENV = "SLACK_CHANNEL"

# Use Europe/Paris to represent CET/CEST (Central European Time with DST)
CET_ZONE = ZoneInfo("Europe/Paris")

RAISED_BY = "AIDA - Advanced Incident Detection Agent"

# Mapping between application names and Azure VM names
# Used to determine which VM to query for metrics and reboot if needed
APP_TO_VM_MAPPING = {
    "AppZwaagdijk": "VirtualMachine",
    # Add more mappings as needed
    # "AppName": "vm-name",
}


def generate_ticket_id() -> str:
    """
    Generate a unique ticket ID in the format INC + 7 random digits.

    Example: INC1234567

    Returns:
        str: A unique ticket ID
    """
    random_digits = ''.join([str(random.randint(0, 9)) for _ in range(7)])
    ticket_id = f"INC{random_digits}"
    logger.debug(f"Generated ticket ID: {ticket_id}")
    return ticket_id


def format_metrics_summary(metrics: Dict[str, Any]) -> str:
    """
    Format Azure Monitor metrics into a human-readable summary for the Resolution Agent.

    Parameters:
    - metrics: Dictionary with cpu_max, memory_max, network metrics, etc.

    Returns:
    - Formatted string describing the metrics findings
    """
    if not metrics or metrics.get("status") != "success":
        return ""

    summary_parts = []

    # CPU metrics
    cpu = metrics.get("cpu_max")
    if cpu is not None:
        if cpu > 80:
            summary_parts.append(f"HIGH CPU: {cpu}% (Critical)")
        elif cpu > 60:
            summary_parts.append(f"Elevated CPU: {cpu}%")
        else:
            summary_parts.append(f"CPU: {cpu}%")

    # Memory metrics (convert bytes to GB if available)
    memory = metrics.get("memory_max")
    if memory is not None:
        memory_gb = memory / (1024**3)  # Convert bytes to GB
        if memory_gb > 8:
            summary_parts.append(f"HIGH Memory: {memory_gb:.2f}GB")
        else:
            summary_parts.append(f"Memory: {memory_gb:.2f}GB")

    # Network metrics
    network_in = metrics.get("network_in_max")
    if network_in is not None and network_in > 0:
        network_in_gb = network_in / (1024**3)
        summary_parts.append(f"Network In: {network_in_gb:.2f}GB")

    network_out = metrics.get("network_out_max")
    if network_out is not None and network_out > 0:
        network_out_gb = network_out / (1024**3)
        summary_parts.append(f"Network Out: {network_out_gb:.2f}GB")

    if summary_parts:
        return "Azure Monitor metrics: " + " | ".join(summary_parts)
    return ""


def extract_vm_name(application_name: str, metrics: Dict[str, Any] = None) -> str:
    """
    Extract or derive VM name from application name and metrics using the APP_TO_VM_MAPPING.

    Parameters:
    - application_name: Application name from monitoring data
    - metrics: Metrics dictionary (may contain vm_name)

    Returns:
    - Azure VM name for the Resolution Agent to use
    """
    # If metrics contain vm_name, use it
    if metrics and metrics.get("vm_name"):
        return metrics.get("vm_name")

    # Check if application name is in the mapping
    if application_name and application_name in APP_TO_VM_MAPPING:
        vm_name = APP_TO_VM_MAPPING[application_name]
        logger.info(f"Mapped application '{application_name}' to VM '{vm_name}'")
        return vm_name

    # If application name provided but not in mapping, log warning and use it as fallback
    if application_name and application_name != "Unknown":
        logger.warning(f"Application '{application_name}' not found in APP_TO_VM_MAPPING, using as VM name")
        return application_name

    # Fallback
    logger.warning("No application name available, defaulting to 'VirtualMachine'")
    return "VirtualMachine"


def _validate_env() -> tuple[str, str]:
    bot_token = os.getenv(SLACK_TOKEN_ENV)
    channel = os.getenv(SLACK_CHANNEL_ENV)
    if not bot_token:
        raise EnvironmentError(f"Missing environment variable: {SLACK_TOKEN_ENV}")
    if not channel:
        raise EnvironmentError(f"Missing environment variable: {SLACK_CHANNEL_ENV}")
    return bot_token, channel


def _get_azure_credential():
    """
    Get Azure credential using DefaultAzureCredential.

    This automatically handles authentication in the following order:
    1. Environment variables (AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID)
    2. Managed identities (for Azure services)
    3. Shared token cache (from az login, VS Code, etc.)
    4. Visual Studio Code authentication
    5. Azure CLI (az login session)
    6. Interactive browser login

    This method picks up your 'az login' session automatically.
    """
    try:
        credential = DefaultAzureCredential()
        logger.debug("Successfully created DefaultAzureCredential")
        return credential
    except Exception as e:
        logger.error(f"Failed to create Azure credential: {e}")
        logger.error("Ensure you are authenticated with Azure. Run: az login")
        return None


def _construct_vm_resource_id(vm_name: str, subscription_id: str = None, resource_group: str = None) -> str:
    """
    Construct the full resource ID for an Azure VM.

    Format: /subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Compute/virtualMachines/{vmName}
    """
    if not subscription_id:
        subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
    if not resource_group:
        resource_group = os.getenv("AZURE_RESOURCE_GROUP_NAME")

    if not subscription_id or not resource_group:
        logger.warning("Missing AZURE_SUBSCRIPTION_ID or AZURE_RESOURCE_GROUP_NAME in environment")
        return None

    resource_id = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Compute/virtualMachines/{vm_name}"
    return resource_id


async def fetch_azure_monitor_metrics(
    vm_name: str,
    detection_time: str = None,
    lookback_minutes: int = 60,
    lookahead_minutes: int = 10
) -> Dict[str, Any]:
    """
    Fetch real metrics from Azure Monitor for a specific VM.

    Parameters:
    - vm_name: Name of the virtual machine
    - detection_time: ISO8601 timestamp when the issue was detected (defaults to now)
    - lookback_minutes: How many minutes before detection time to query
    - lookahead_minutes: How many minutes after detection time to query

    Returns:
    - Dictionary with metrics data (CPU, Memory, Network, Disk)
    """
    metrics: Dict[str, Any] = {
        "cpu_max": None,
        "memory_max": None,
        "network_in_max": None,
        "network_out_max": None,
        "disk_read_max": None,
        "disk_write_max": None,
        "raw_data": [],
        "status": "not_fetched"
    }

    if not AZURE_MONITOR_AVAILABLE:
        logger.debug("Azure Monitor dependencies not available")
        metrics["status"] = "azure_monitor_unavailable"
        return metrics

    try:
        # Note: Azure Monitor metrics are only available for recent data (typically last 30 days).
        # Even though we have a detection_time from logs (which could be old), we query metrics
        # around CURRENT TIME because that's when metric data is available.
        # The detection_time is used for the incident ticket, but metrics are current system state.

        logger.info(f"Detection time from logs: {detection_time}")
        logger.info(f"Note: Metrics will be queried around current time (not log detection time)")

        # Calculate time range using CURRENT TIME, not detection_time
        # This ensures we get available metric data from Azure Monitor
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=lookback_minutes)

        logger.info(f"Querying Azure Monitor for VM '{vm_name}'")
        logger.info(f"Time range: {start_time} to {end_time}")

        # Get resource ID
        resource_id = _construct_vm_resource_id(vm_name)
        if not resource_id:
            metrics["status"] = "resource_id_construction_failed"
            return metrics

        logger.debug(f"Resource ID: {resource_id}")

        # Get subscription ID for client
        subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        if not subscription_id:
            logger.error("AZURE_SUBSCRIPTION_ID not set")
            metrics["status"] = "subscription_id_missing"
            return metrics

        # Create credentials
        credential = _get_azure_credential()
        if not credential:
            metrics["status"] = "credential_failed"
            return metrics

        # Map of metric names to their storage keys
        # These are Platform Metrics from "Virtual Machine Host" namespace
        metrics_to_query = {
            "Percentage CPU": "cpu_max",
            "Available Memory Bytes": "memory_max",
            "Network In Total": "network_in_max",
            "Network Out Total": "network_out_max",
            "Disk Read Bytes": "disk_read_max",
            "Disk Write Bytes": "disk_write_max",
        }

        # Format timespan in ISO 8601 format (Azure API requires UTC with Z suffix)
        # Convert to UTC before formatting to handle timezones correctly
        start_time_utc = start_time.astimezone(timezone.utc) if start_time.tzinfo else start_time
        end_time_utc = end_time.astimezone(timezone.utc) if end_time.tzinfo else end_time

        start_str = start_time_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_str = end_time_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
        timespan_str = f"{start_str}/{end_str}"

        logger.debug(f"Timespan: {timespan_str}")

        try:
            # Get access token for REST API
            access_token = credential.get_token("https://management.azure.com/.default").token

            # Azure Monitor REST API endpoint
            api_url = f"https://management.azure.com{resource_id}/providers/microsoft.insights/metrics"

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            # Query parameters for REST API
            # API version 2018-01-01 works and properly returns aggregated values
            params = {
                "api-version": "2018-01-01",
                "timespan": timespan_str,
                "interval": "PT5M",  # 5 minute intervals
                "aggregation": "Maximum",  # Get maximum values as requested
                "metricnames": ",".join(metrics_to_query.keys()),  # Join all metric names
            }


            # Make REST API call
            async with httpx.AsyncClient() as client:
                response = await client.get(api_url, headers=headers, params=params)

                logger.debug(f"API response status: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()


                    if "value" in data and data["value"]:
                        logger.info(f"Got {len(data['value'])} metrics from Azure Monitor")
                        logger.debug(f"Raw API response: {data}")

                        for metric in data["value"]:
                            metric_name = metric.get("name", {}).get("value", "Unknown")
                            metric_unit = metric.get("unit", "Unknown")
                            logger.info(f"Processing metric: {metric_name} (Unit: {metric_unit})")

                            # Get timeseries data
                            timeseries = metric.get("timeseries", [])
                            if timeseries:
                                for ts in timeseries:
                                    data_points = ts.get("data", [])
                                    if data_points:
                                        logger.info(f"  Timeseries for {metric_name}: {len(data_points)} data points")
                                        logger.info(f"  Data points structure: {data_points[0] if data_points else 'empty'}")

                                        # Find maximum value
                                        max_val = None


                                        for i, dp in enumerate(data_points):
                                            # Try both "maximum" and other possible field names
                                            if "maximum" in dp and dp["maximum"] is not None:
                                                if max_val is None or dp["maximum"] > max_val:
                                                    max_val = dp["maximum"]
                                            elif "total" in dp and dp["total"] is not None:
                                                # Some metrics use "total" instead of "maximum"
                                                if max_val is None or dp["total"] > max_val:
                                                    max_val = dp["total"]
                                            elif "average" in dp and dp["average"] is not None:
                                                # Some metrics use "average"
                                                if max_val is None or dp["average"] > max_val:
                                                    max_val = dp["average"]


                                        # Store metric by name
                                        if max_val is not None:
                                            for query_name, storage_key in metrics_to_query.items():
                                                if query_name.lower() in metric_name.lower():
                                                    metrics[storage_key] = max_val
                                                    logger.info(f"Stored {metric_name}: {max_val} {metric_unit} in {storage_key}")
                                                    break

                                        metric_info = {
                                            "name": metric_name,
                                            "unit": metric_unit,
                                            "max": max_val,
                                            "data_points": len(data_points)
                                        }
                                        metrics["raw_data"].append(metric_info)
                            else:
                                logger.warning(f"No timeseries data for metric: {metric_name}")

                        metrics["status"] = "success"
                        logger.info(f"Successfully fetched metrics for VM '{vm_name}'")
                    else:
                        metrics["status"] = "no_data_returned"
                        metrics["error"] = "Azure Monitor returned no metrics data"
                        logger.warning("No metrics data returned from Azure Monitor")

                elif response.status_code == 400:
                    logger.error(f"Bad request: {response.text}")
                    metrics["status"] = "bad_request"
                    metrics["error"] = "Bad request to Azure Monitor API"

                elif response.status_code == 401:
                    logger.error("Unauthorized - Azure authentication failed")
                    metrics["status"] = "auth_failed"
                    metrics["error"] = "Azure authentication failed"

                elif response.status_code == 404:
                    logger.error(f"VM not found: {resource_id}")
                    metrics["status"] = "vm_not_found"
                    metrics["error"] = f"VM '{vm_name}' not found"

                else:
                    logger.error(f"API error: {response.status_code}")
                    metrics["status"] = "api_error"
                    metrics["error"] = f"Azure Monitor API error: {response.status_code}"

                return metrics

        except Exception as e:
            logger.error(f"Error making REST API call: {e}")
            metrics["status"] = "api_call_failed"
            metrics["error"] = str(e)
            return metrics

    except Exception as e:
        logger.error(f"Error fetching Azure Monitor metrics: {e}")
        metrics["status"] = "error"
        metrics["error"] = str(e)
        return metrics


def _parse_alert(alert_text: str) -> Dict[str, Optional[str]]:
    """
    Lightweight triage: extract service, region, timestamp, severity from a monitoring availability alert.
    This is heuristic-based and intended to run without Azure SDKs.
    """
    service = None
    region = None
    severity = "Medium"
    ts = None

    # common patterns
    svc_match = re.search(r"service[-_\s]?([A-Za-z0-9\-]+)", alert_text, re.IGNORECASE)
    if svc_match:
        service = svc_match.group(0)

    region_match = re.search(r"(eu|us|ap|asia|emea)[-_]?\w*", alert_text, re.IGNORECASE)
    if region_match:
        region = region_match.group(0)

    # Match ISO 8601 timestamps with either Z suffix or timezone offset (±HH:MM)
    # Pattern: YYYY-MM-DDTHH:MM:SS followed by Z or ±HH:MM
    time_match = re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})", alert_text)

    if time_match:
        ts = time_match.group(0)
        logger.info(f"_parse_alert: Successfully extracted timestamp: {ts}")
    else:
        # No ISO 8601 match found - log the full text for debugging and fallback to current time
        logger.warning(f"_parse_alert: Could not extract ISO 8601 timestamp from alert_text")
        logger.warning(f"_parse_alert: Full alert_text:\n{alert_text}")
        ts = datetime.now(CET_ZONE).isoformat()
        logger.warning(f"_parse_alert: Using fallback current time: {ts}")

    sev_match = re.search(r"\b(critical|high|medium|low)\b", alert_text, re.IGNORECASE)
    if sev_match:
        severity = sev_match.group(1).capitalize()

    return {"service": service, "region": region, "severity": severity, "timestamp": ts}


async def _gather_azure_context(parsed: Dict[str, Optional[str]]) -> Dict[str, Any]:
    """
    Optionally query Azure (if project_client is available) to enrich the ticket.
    This function is best-effort: failures are logged but do not interrupt ticket creation.
    """
    context: Dict[str, Any] = {}
    if not project_client:
        return context

    try:
        # Placeholder: try to fetch a small sample of metrics if a metrics interface exists.
        # Real implementations should replace with azure.monitor.query or similar.
        if hasattr(project_client, "metrics") or hasattr(project_client, "resources"):
            try:
                context["azure_query_sample"] = "executed"
            except Exception:
                context["azure_query_sample"] = "failed"
    except Exception as e:
        logger.debug("Azure context enrichment failed: %s", e)
    return context


async def fetch_azure_metrics(
    parsed: Dict[str, Optional[str]],
    lookback_seconds: int = 300,
    vm_name: str = "VirtualMachine",
    detection_time: str = None
) -> Dict[str, Any]:
    """
    Fetch metrics from Azure Monitor for a VM.

    Parameters:
    - parsed: Dictionary with service/region info from alert parsing
    - lookback_seconds: Fallback for time calculation (converted to minutes)
    - vm_name: Name of the VM to query metrics for (default: "VirtualMachine")
    - detection_time: Optional explicit detection time (preferred over regex/parsing)

    Returns:
    - Dictionary with metrics data (cpu_max, memory_max, network_in_max, etc.)
    """
    try:
        lookback_minutes = max(1, lookback_seconds // 60)  # Convert seconds to minutes, min 1

        logger.info(f"Fetching Azure Monitor metrics for VM: {vm_name}")

        # Use provided detection_time if available, otherwise try to extract from log lines or parsed data
        if not detection_time:
            # Try to extract detection time from related_log_lines if available
            related_log_lines = parsed.get("related_log_lines", [])

            if related_log_lines and isinstance(related_log_lines, list):
                try:
                    # Log lines start with timestamp, e.g., "2025-10-21T18:46:00+02:00 app=..."
                    # Extract all timestamps and use the latest one
                    timestamps = []
                    for line in related_log_lines:
                        if isinstance(line, str) and line.strip():
                            # First token before space is the timestamp
                            parts = line.split()
                            if parts:
                                ts = parts[0]
                                timestamps.append(ts)

                    if timestamps:
                        # Use the latest timestamp
                        detection_time = timestamps[-1]
                        logger.info(f"Extracted detection_time from log lines: {detection_time}")
                except Exception as e:
                    logger.debug(f"Could not extract timestamp from log lines: {e}")

            if not detection_time:
                logger.warning("No detection_time from log lines, using parsed timestamp")
                detection_time = parsed.get("timestamp")

        logger.info(f"Using detection_time for metrics: {detection_time}")

        # Call the real Azure Monitor metrics fetcher
        metrics = await fetch_azure_monitor_metrics(
            vm_name=vm_name,
            detection_time=detection_time,
            lookback_minutes=lookback_minutes
        )

        return metrics

    except Exception as e:
        logger.error(f"Azure metrics fetch failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "cpu_max": None,
            "memory_max": None,
            "network_in_max": None,
            "network_out_max": None,
        }


def correlate_metrics(parsed: Dict[str, Optional[str]], metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Correlate alert and metrics using Azure Monitor data.
    Returns correlation summary suitable for inclusion in ticket handed to resolution agent.
    """
    summary: Dict[str, Any] = {"correlated": False, "notes": [], "ml_score": None}

    if not metrics:
        summary["notes"].append("No metrics available for correlation")
        return summary

    try:
        # Check metrics status
        status = metrics.get("status")
        if status == "error":
            summary["notes"].append(f"Metrics fetch error: {metrics.get('error')}")
            return summary
        elif status == "azure_monitor_unavailable":
            summary["notes"].append("Azure Monitor Query client not available")
            return summary
        elif status != "success":
            summary["notes"].append(f"Metrics status: {status}")
            return summary

        # Correlate based on maximum values from Azure Monitor
        cpu_max = metrics.get("cpu_max")
        memory_max = metrics.get("memory_max")
        network_in_max = metrics.get("network_in_max")
        network_out_max = metrics.get("network_out_max")
        disk_read_max = metrics.get("disk_read_max")
        disk_write_max = metrics.get("disk_write_max")

        # Heuristics for correlation
        if isinstance(cpu_max, (int, float)) and cpu_max > 80:
            summary["correlated"] = True
            summary["notes"].append(f"High CPU peak observed: {cpu_max:.1f}%")

        if isinstance(memory_max, (int, float)):
            # Memory bytes to percentage (assuming 8GB = 8589934592 bytes as reference)
            memory_gb = memory_max / (1024 ** 3) if memory_max > 1024 else memory_max
            if memory_max > 1000000000:  # > 1GB absolute bytes
                summary["correlated"] = True
                summary["notes"].append(f"High memory usage observed: {memory_gb:.1f}GB")

        if isinstance(network_in_max, (int, float)) and network_in_max > 1000000000:  # > 1GB
            summary["correlated"] = True
            summary["notes"].append(f"High network inbound: {network_in_max / (1024**3):.2f}GB")

        if isinstance(network_out_max, (int, float)) and network_out_max > 1000000000:  # > 1GB
            summary["correlated"] = True
            summary["notes"].append(f"High network outbound: {network_out_max / (1024**3):.2f}GB")

        if isinstance(disk_read_max, (int, float)) and disk_read_max > 100000000:  # > 100MB
            summary["notes"].append(f"High disk read activity: {disk_read_max / (1024**2):.1f}MB")

        if isinstance(disk_write_max, (int, float)) and disk_write_max > 100000000:  # > 100MB
            summary["notes"].append(f"High disk write activity: {disk_write_max / (1024**2):.1f}MB")

        # Include metrics summary
        summary["metrics_summary"] = {
            "cpu_max_percent": cpu_max,
            "memory_max_bytes": memory_max,
            "network_in_max_bytes": network_in_max,
            "network_out_max_bytes": network_out_max,
        }

    except Exception as e:
        logger.error(f"Correlation error: {e}")
        summary["notes"].append(f"Correlation error: {e}")

    # Placeholder ML score
    summary["ml_score"] = 0.65 if summary["correlated"] else 0.3

    return summary


async def send_to_resolution_agent(ticket: Dict[str, Any], correlation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Hand off the ticket to the resolution agent. Best-effort: if a resolution agent module/client
    exists it will be called; otherwise this is a no-op that returns a descriptive result.
    Tests should monkeypatch this function.
    """
    result: Dict[str, Any] = {"sent": False, "detail": "no resolution agent available"}
    try:
        # Try to import a resolution_agent module if present (non-critical)
        try:
            from resolution_agent import receive_incident  # type: ignore
        except Exception:
            receive_incident = None

        payload = {
            "incident_id": ticket.get("id"),
            "title": ticket.get("title"),
            "summary": ticket.get("summary"),
            "created_at": ticket.get("created_at"),
            "triage": ticket.get("triage"),
            "correlation": correlation,
            "azure_context": ticket.get("azure_context", {}),
        }

        if receive_incident:
            # allow resolution agent to be async or sync
            if asyncio.iscoroutinefunction(receive_incident):
                res = await receive_incident(payload)
            else:
                res = receive_incident(payload)
            result = {"sent": True, "response": res}
        else:
            logger.debug("No resolution agent found; skipping handoff")
            result = {"sent": False, "detail": "no resolution agent found"}
    except Exception as e:
        logger.exception("Error sending to resolution agent: %s", e)
        result = {"sent": False, "error": str(e)}
    return result


def create_incident_ticket(alert_text: str, detection_time: str = None, ticket_id: str = None) -> dict:
    """
    Pure ticket creation from alert text. Performs lightweight triage and returns ticket dict.
    No external network calls are made here.

    Parameters:
    - alert_text: Alert text to parse
    - detection_time: Optional explicit detection time (preferred over regex extraction)
    - ticket_id: Optional ticket ID to use (if not provided, generates a new one)
    """
    parsed = _parse_alert(alert_text)

    # Override timestamp with provided detection_time if available
    if detection_time:
        parsed["timestamp"] = detection_time
        logger.info(f"create_incident_ticket: Using provided detection_time: {detection_time}")

    # Use provided ticket_id or generate a new one
    incident_id = ticket_id if ticket_id else generate_ticket_id()
    logger.info(f"create_incident_ticket: Using ticket ID: {incident_id}")
    created_at = datetime.now(CET_ZONE).isoformat()

    title = f"Availability alert - {parsed.get('service') or 'unknown-service'}"
    summary = alert_text.strip()

    ticket = {
        "id": incident_id,
        "title": title,
        "summary": summary,
        "created_at": created_at,
        "status": "open",
        "triage": parsed,
        "azure_context": {},  # to be populated by raise_incident_in_slack if possible
        "raised_by": RAISED_BY,
    }
    return ticket


async def async_send_to_slack(
    ticket_title: str,
    ticket_id: str,
    incident_details: str,
    severity: str = "Medium",
    affected_system: str = "",
    resolution: str = ""
) -> Dict[str, Any]:
    """
    Send a formatted ticket to Slack using Block Kit (if available).
    Returns a dict describing the delivery result.
    """
    await asyncio.sleep(0.01)  # yield control

    slack_token = os.getenv(SLACK_TOKEN_ENV)
    slack_channel = os.getenv(SLACK_CHANNEL_ENV, "#incidents")

    result: Dict[str, Any] = {
        "ticket_id": ticket_id,
        "ticket_title": ticket_title,
        "severity": severity,
        "affected_system": affected_system,
        "slack_channel": slack_channel,
        "delivery_status": "pending",
    }

    if not SLACK_AVAILABLE:
        result["delivery_status"] = "failed"
        result["error"] = "Slack SDK not installed"
        return result

    if not slack_token:
        result["delivery_status"] = "failed"
        result["error"] = "SLACK_BOT_TOKEN not configured"
        return result

    try:
        client = WebClient(token=slack_token)

        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": f"🎫 {ticket_title}", "emoji": True}},
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Ticket ID:*\n`{ticket_id}`"},
                    {"type": "mrkdwn", "text": f"*Severity:*\n{severity}"},
                ],
            },
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Incident Details:*\n{incident_details}"}},
        ]

        if affected_system:
            blocks.insert(2, {"type": "section", "fields": [{"type": "mrkdwn", "text": f"*Affected System:*\n{affected_system}"}]})

        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Created: {datetime.now(CET_ZONE).strftime('%Y-%m-%d %H:%M:%S %Z')}"
                    }
                ],
            }
        )

        # Add "Raised by AIDA" context
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Raised by: {RAISED_BY}"
                    }
                ],
            }
        )

        # Try to send blocks; fallback to simple text for dummy clients used in tests
        try:
            response = client.chat_postMessage(channel=slack_channel, blocks=blocks, text=f"New Ticket: {ticket_title}")
        except TypeError:
            # client may be a test dummy that doesn't accept 'blocks'
            response = client.chat_postMessage(channel=slack_channel, text=f"New Ticket: {ticket_title}\nRaised by: {RAISED_BY}")

        resp_data = getattr(response, "data", None) or response
        result["delivery_status"] = "success"
        result["slack_message_ts"] = resp_data.get("ts")
        result["slack_channel_id"] = resp_data.get("channel")
        result["slack_response"] = resp_data

    except SlackApiError as e:
        result["delivery_status"] = "failed"
        try:
            err = e.response.get("error") if getattr(e, "response", None) else str(e)
        except Exception:
            err = str(e)
        result["error"] = f"Slack API error: {err}"
        logger.error("Slack API error: %s", err)
    except Exception as e:
        result["delivery_status"] = "failed"
        result["error"] = str(e)
        logger.exception("Error sending to Slack")

    return result


async def raise_incident_in_slack(alert_text: str, severity: str = "Medium", affected_system: str = "", detection_time: str = None, ticket_id: str = None) -> dict:
    """
    Create a ticket (triage + enrichment + correlation) and post it to Slack.
    Then hand the incident to the resolution agent.
    Returns the ticket enriched with Slack delivery metadata, Azure context and resolution handoff result.

    Parameters:
    - alert_text: The alert text to process
    - severity: Severity level
    - affected_system: Affected system name
    - detection_time: Optional explicit detection time from the incident
    - ticket_id: Optional ticket ID to use (if not provided, generates a new one)
    """
    ticket = create_incident_ticket(alert_text, detection_time=detection_time, ticket_id=ticket_id)

    # 2) fetch data from azure monitor (use mapping to get correct VM name)
    try:
        # Get application name from affected_system or triage
        app_name = affected_system or ticket.get("triage", {}).get("service", "")

        # Map application name to VM name
        if app_name and app_name in APP_TO_VM_MAPPING:
            vm_name = APP_TO_VM_MAPPING[app_name]
            logger.info(f"Using mapped VM name '{vm_name}' for application '{app_name}'")
        else:
            vm_name = app_name or "VirtualMachine"
            if app_name:
                logger.warning(f"Application '{app_name}' not in mapping, using as VM name")

        logger.info(f"Fetching metrics for VM: {vm_name}")
        metrics = await fetch_azure_metrics(
            ticket.get("triage", {}),
            vm_name=vm_name,
            detection_time=detection_time
        )
        logger.info(f"Metrics fetch result - status: {metrics.get('status')}, cpu_max: {metrics.get('cpu_max')}")
        ticket["metrics"] = metrics
    except Exception as e:
        logger.error(f"Metrics fetch failed with exception: {e}", exc_info=True)
        ticket["metrics"] = {}

    # 3) correlate data (placeholder ML)
    try:
        correlation = correlate_metrics(ticket.get("triage", {}), ticket.get("metrics", {}))
        ticket["correlation"] = correlation
    except Exception as e:
        logger.debug("Correlation failed: %s", e)
        ticket["correlation"] = {"error": str(e)}

    # 4) create incident in Slack
    slack_result = await async_send_to_slack(
        ticket_title=ticket["title"],
        ticket_id=ticket["id"],
        incident_details=ticket["summary"],
        severity=severity or ticket["triage"].get("severity", "Medium"),
        affected_system=affected_system or (ticket["triage"].get("service") or ""),
        resolution="",
    )

    ticket["slack_delivery_status"] = slack_result.get("delivery_status")
    if slack_result.get("delivery_status") == "success":
        ticket["slack_ts"] = slack_result.get("slack_message_ts")
        ticket["slack_channel"] = slack_result.get("slack_channel_id") or slack_result.get("slack_channel")
        ticket["slack_response"] = slack_result.get("slack_response")
    else:
        ticket["slack_error"] = slack_result.get("error")

    # ensure raised_by included in final ticket
    ticket["raised_by"] = RAISED_BY

    return ticket


async def process_monitoring_incident(monitoring_json: Dict[str, Any] | str) -> Dict[str, Any]:
    """
    Process an incident from monitoring agent JSON output.

    Expected JSON format (from monitor_agent):
    {
        "status": "abnormality_detected",
        "title": "Performance Degradation Detected",
        "short_description": "Gradually increasing response times observed...",
        "detection_time": "2025-10-21T17:07:00+02:00",
        "application_name": "AppZwaagdijk",
        "related_log_lines": [...],
        "timestamp_detected": "2025-10-24T11:59:24.577368"
    }

    Parameters:
    - monitoring_json: Dict or JSON string from monitor_agent output

    Returns:
    - Full incident ticket with Slack delivery status and metrics correlation
    - Returns error dict if validation fails
    """

    # Parse JSON string to dict if needed
    if isinstance(monitoring_json, str):
        try:
            data = json.loads(monitoring_json)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse monitoring JSON: {e}")
            return {
                "status": "error",
                "error": "Invalid JSON input",
                "detail": str(e)
            }
    else:
        data = monitoring_json

    # Generate unique ticket ID for this incident
    ticket_id = generate_ticket_id()
    logger.info(f"Generated ticket ID for incident: {ticket_id}")

    # Validate required fields
    required_fields = [
        "status",
        "title",
        "short_description",
        "detection_time",
        "application_name",
        "related_log_lines",
    ]

    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        logger.error(f"Missing required fields in monitoring input: {missing_fields}")
        return {
            "status": "error",
            "error": "Invalid monitoring input",
            "detail": f"Missing required fields: {missing_fields}",
            "expected_format": {
                "status": "abnormality_detected|healthy|error",
                "title": "string",
                "short_description": "string",
                "detection_time": "ISO8601 timestamp",
                "application_name": "string",
                "related_log_lines": "array of strings",
                "timestamp_detected": "ISO8601 timestamp (optional)"
            }
        }

    # Check if monitoring detected abnormalities
    if data.get("status") != "abnormality_detected":
        logger.info(f"Monitoring status is '{data.get('status')}', no incident to process")
        return {
            "status": "no_incident",
            "message": "Monitoring reported no abnormalities",
            "monitoring_status": data.get("status"),
            "application_name": data.get("application_name")
        }

    # Extract monitoring data
    title = data.get("title")
    short_description = data.get("short_description")
    detection_time = data.get("detection_time")
    application_name = data.get("application_name")
    related_log_lines = data.get("related_log_lines", [])

    logger.info(f"Processing incident from monitoring: {application_name} - {title}")
    logger.info(f"DEBUG process_monitoring_incident: detection_time = {detection_time}")
    logger.debug(f"Related log lines: {len(related_log_lines)} lines")

    # Construct alert text from monitoring data
    alert_text = f"{title}\n{short_description}\nDetection Time: {detection_time}\nApplication: {application_name}"
    logger.info(f"DEBUG process_monitoring_incident: alert_text Detection Time line = {[line for line in alert_text.split(chr(10)) if 'Detection Time:' in line]}")
    if related_log_lines:
        alert_text += f"\n\nRelated Log Lines:\n" + "\n".join(related_log_lines)

    # Determine severity from title and description
    severity_lower = (title + short_description).lower()
    if "critical" in severity_lower:
        severity = "Critical"
    elif "high" in severity_lower or "degradation" in severity_lower:
        severity = "High"
    elif "medium" in severity_lower:
        severity = "Medium"
    else:
        severity = "High"  # Default to High for abnormalities

    # Process as incident through the standard workflow
    try:
        # Create incident ticket and send to Slack (pass the generated ticket_id)
        full_ticket = await raise_incident_in_slack(
            alert_text=alert_text,
            severity=severity,
            affected_system=application_name,
            detection_time=detection_time,
            ticket_id=ticket_id
        )

        # Add monitoring context to ticket
        full_ticket["monitoring_source"] = {
            "status": data.get("status"),
            "detection_time": detection_time,
            "related_log_lines": related_log_lines,
            "timestamp_detected": data.get("timestamp_detected")
        }

        logger.info(f"Successfully processed incident for {application_name}")

        # Extract metrics and VM name for downstream agents
        metrics = full_ticket.get("metrics", {})
        vm_name = extract_vm_name(application_name, metrics)
        metrics_summary = format_metrics_summary(metrics)

        # Enhance description with metrics information for Resolution Agent
        enhanced_description = short_description
        if metrics_summary:
            enhanced_description = f"{short_description}\n\n{metrics_summary}"

        # Return the result as output (no handoff to resolution agent)
        logger.info(f"DEBUG returning from process_monitoring_incident: detection_time = {detection_time}")
        return {
            "status": "success",
            "ticket_id": ticket_id,
            "incident_id": full_ticket.get("id"),
            "title": full_ticket.get("title"),
            "application_name": application_name,
            "vm_name": vm_name,
            "severity": severity,
            "description": enhanced_description,
            "short_description": short_description,
            "detection_time": detection_time,
            "slack_delivery": {
                "status": full_ticket.get("slack_delivery_status"),
                "channel": full_ticket.get("slack_channel"),
                "message_timestamp": full_ticket.get("slack_ts"),
                "error": full_ticket.get("slack_error")
            },
            "metrics": metrics,
            "correlation": full_ticket.get("correlation", {}),
            "monitoring_source": full_ticket.get("monitoring_source", {}),
            "full_ticket": full_ticket
        }

    except Exception as e:
        logger.error(f"Error processing monitoring incident: {e}", exc_info=True)
        return {
            "status": "error",
            "error": "Failed to process incident",
            "detail": str(e),
            "application_name": application_name,
            "title": title
        }