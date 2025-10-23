import os
import asyncio
import pytest

from incident_detection_agent import create_incident_ticket, raise_incident_in_slack
import incident_detection_agent as ida


class DummySlackResp:
    def __init__(self, ts="12345.6789", channel="C12345", text="ok"):
        self.data = {"ts": ts, "channel": channel, "text": text}


def test_create_incident_ticket_basic():
    alert = "service A down in region eu-west-1"
    ticket = create_incident_ticket(alert)
    assert "id" in ticket and ticket["summary"] == alert.strip()
    assert ticket["status"] == "open"


def test_raise_incident_in_slack_monkeypatch(monkeypatch):
    # Ensure env vars for test
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-fake-token")
    monkeypatch.setenv("SLACK_CHANNEL", "#incidents-test")

    # Patch the implementation module's WebClient so Slack calls don't go out
    class DummyClient:
        def __init__(self, token=None):
            self.token = token

        def chat_postMessage(self, channel, text):
            return DummySlackResp(ts="999.888", channel=channel, text=text)

    # The top-level incident_detection_agent wrapper loads the real module into _impl
    # Patch WebClient on that implementation module
    monkeypatch.setattr(ida._impl, "WebClient", DummyClient, raising=False)

    # Call the async function synchronously for pytest without asyncio plugin
    ticket = asyncio.run(raise_incident_in_slack("test alert for unit"))
    assert ticket["status"] == "open"
    assert ticket.get("slack_ts") == "999.888"
    assert ticket.get("slack_channel") == "#incidents-test"