import os
import re
import uuid
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
    SLACK_AVAILABLE = True
except Exception:
    SLACK_AVAILABLE = False

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


def _validate_env() -> tuple[str, str]:
    bot_token = os.getenv(SLACK_TOKEN_ENV)
    channel = os.getenv(SLACK_CHANNEL_ENV)
    if not bot_token:
        raise EnvironmentError(f"Missing environment variable: {SLACK_TOKEN_ENV}")
    if not channel:
        raise EnvironmentError(f"Missing environment variable: {SLACK_CHANNEL_ENV}")
    return bot_token, channel


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

    time_match = re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", alert_text)
    if time_match:
        ts = time_match.group(0)
    else:
        # fallback: current time in CET/CEST ISO
        ts = datetime.now(CET_ZONE).isoformat()

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
        # Example placeholder: try to fetch VM info or recent metrics if the project_client exposes it.
        # Keep this generic to avoid hard dependency on Azure SDKs at import time.
        if hasattr(project_client, "resources"):
            # pseudo-call; real implementations would vary based on utils/project_client shape
            try:
                context["azure_resources_sample"] = "query-executed"
            except Exception:
                context["azure_resources_sample"] = "query-failed"
    except Exception as e:
        logger.debug("Azure context enrichment failed: %s", e)
    return context


def create_incident_ticket(alert_text: str) -> dict:
    """
    Pure ticket creation from alert text. Performs lightweight triage and returns ticket dict.
    No external network calls are made here.
    """
    parsed = _parse_alert(alert_text)
    incident_id = str(uuid.uuid4())
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
                    {"type": "mrkdwn", "text": f"*Ticket ID:*\n{ticket_id}"},
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


async def raise_incident_in_slack(alert_text: str, severity: str = "Medium", affected_system: str = "") -> dict:
    """
    Create a ticket (triage + enrichment) and post it to Slack. Returns the ticket enriched
    with Slack delivery metadata and any Azure context fetched.
    """
    ticket = create_incident_ticket(alert_text)

    # attempt to enrich via Azure if available
    try:
        azure_ctx = await _gather_azure_context(ticket.get("triage", {}))
        ticket["azure_context"] = azure_ctx
    except Exception as e:
        logger.debug("Azure enrichment skipped/failed: %s", e)
        ticket["azure_context"] = {}

    # Post to slack using helper
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