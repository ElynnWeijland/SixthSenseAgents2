import os
import uuid
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from dotenv import load_dotenv

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
    SLACK_AVAILABLE = True
except Exception:
    SLACK_AVAILABLE = False

# Use project_client as context if available (utils.py loads dotenv already)
try:
    from utils import project_client  # noqa: F401
except Exception:
    project_client = None

load_dotenv()
logger = logging.getLogger(__name__)

SLACK_TOKEN_ENV = "SLACK_BOT_TOKEN"
SLACK_CHANNEL_ENV = "SLACK_CHANNEL"


def _validate_env() -> tuple[str, str]:
    bot_token = os.getenv(SLACK_TOKEN_ENV)
    channel = os.getenv(SLACK_CHANNEL_ENV)
    if not bot_token:
        raise EnvironmentError(f"Missing environment variable: {SLACK_TOKEN_ENV}")
    if not channel:
        raise EnvironmentError(f"Missing environment variable: {SLACK_CHANNEL_ENV}")
    return bot_token, channel


def _format_incident(alert_text: str) -> dict:
    incident_id = str(uuid.uuid4())
    ts = datetime.now(timezone.utc).isoformat()
    title = f"Availability alert detected - {incident_id[:8]}"
    summary = alert_text.strip()
    details = {
        "id": incident_id,
        "title": title,
        "summary": summary,
        "created_at": ts,
        "status": "open",
    }
    return details


async def async_send_to_slack(
    ticket_title: str,
    ticket_id: str,
    incident_details: str,
    severity: str = "Medium",
    affected_system: str = "",
    resolution: str = ""
) -> Dict[str, Any]:
    """Send a formatted ticket to Slack using Block Kit. Returns a dict with delivery metadata."""
    await asyncio.sleep(0.01)  # small yield for async contexts

    slack_token = os.getenv("SLACK_BOT_TOKEN")
    slack_channel = os.getenv("SLACK_CHANNEL", "#incidents")

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
        ]

        if affected_system:
            blocks.append(
                {
                    "type": "section",
                    "fields": [{"type": "mrkdwn", "text": f"*Affected System:*\n{affected_system}"}],
                }
            )

        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*Incident Details:*\n{incident_details}"}})

        if resolution:
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*Resolution:*\n{resolution}"}})

        blocks.append(
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
                ],
            }
        )

        try:
            # Try to send rich Block Kit message first
            response = client.chat_postMessage(channel=slack_channel, blocks=blocks, text=f"New Ticket: {ticket_title}")
        except TypeError as e:
            # Fallback for clients that don't accept blocks (tests use a simple dummy client)
            logger.debug("chat_postMessage does not accept blocks, retrying without blocks: %s", e)
            response = client.chat_postMessage(channel=slack_channel, text=f"New Ticket: {ticket_title}")

        # response may be a dict-like or have .data
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
        logger.error(f"Slack API error: {err}")
    except Exception as e:
        result["delivery_status"] = "failed"
        result["error"] = str(e)
        logger.exception("Error sending to Slack")

    return result


def create_incident_ticket(alert_text: str) -> dict:
    """Create an incident ticket object from a monitoring alert (no external side effects)."""
    return _format_incident(alert_text)


async def raise_incident_in_slack(alert_text: str, severity: str = "Medium", affected_system: str = "") -> dict:
    """
    Create a ticket from the alert and post it to Slack using Block Kit formatting.
    Returns the ticket dict merged with Slack delivery metadata.
    """
    ticket = _format_incident(alert_text)

    # Use Slack helper to post formatted message
    slack_result = await async_send_to_slack(
        ticket_title=ticket["title"],
        ticket_id=ticket["id"],
        incident_details=ticket["summary"],
        severity=severity,
        affected_system=affected_system,
        resolution="",
    )

    # Merge selected fields for backward compatibility
    ticket["slack_delivery_status"] = slack_result.get("delivery_status")
    if slack_result.get("delivery_status") == "success":
        ticket["slack_ts"] = slack_result.get("slack_message_ts")
        ticket["slack_channel"] = slack_result.get("slack_channel_id") or slack_result.get("slack_channel")
        ticket["slack_response"] = slack_result.get("slack_response")
    else:
        ticket["slack_error"] = slack_result.get("error")

    return ticket