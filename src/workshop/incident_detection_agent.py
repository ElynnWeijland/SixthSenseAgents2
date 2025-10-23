import os
import uuid
import time
import asyncio
from datetime import datetime, timezone
from dotenv import load_dotenv

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Use project_client as context if available (utils.py loads dotenv already)
try:
    from utils import project_client  # noqa: F401
except Exception:
    project_client = None


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


def _post_to_slack(client: WebClient, channel: str, message: str) -> dict:
    try:
        resp = client.chat_postMessage(channel=channel, text=message)
        return {"ok": True, "slack_response": resp.data}
    except SlackApiError as exc:
        # Return structured error for caller to handle
        return {"ok": False, "error": str(exc), "response": getattr(exc, "response", None)}


def create_incident_ticket(alert_text: str) -> dict:
    """Create an incident ticket object from a monitoring alert (no external side effects)."""
    return _format_incident(alert_text)


async def raise_incident_in_slack(alert_text: str) -> dict:
    """
    Raise an incident in Slack and return ticket details merged with Slack response.

    This is async-friendly and will run Slack calls in a thread to avoid blocking.
    """
    bot_token, channel = _validate_env()
    ticket = _format_incident(alert_text)

    message = (
        f"*New Incident Created*\n"
        f"ID: {ticket['id']}\n"
        f"Title: {ticket['title']}\n"
        f"Summary: {ticket['summary']}\n"
        f"Created At: {ticket['created_at']}\n"
        f"Status: {ticket['status']}"
    )

    def _sync_post():
        client = WebClient(token=bot_token)
        return _post_to_slack(client, channel, message)

    result = await asyncio.to_thread(_sync_post)

    if result.get("ok"):
        slack_resp = result["slack_response"]
        ticket["slack_ts"] = slack_resp.get("ts")
        ticket["slack_channel"] = slack_resp.get("channel")
        ticket["slack_message"] = slack_resp.get("text", message)
    else:
        ticket["slack_error"] = result.get("error")

    return ticket