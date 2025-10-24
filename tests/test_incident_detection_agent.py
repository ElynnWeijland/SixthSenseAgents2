import os
import asyncio

from incident_detection_agent import create_incident_ticket, raise_incident_in_slack
import incident_detection_agent as ida


class DummySlackResult(dict):
    def __init__(self, ts="999.888", channel="#incidents-test"):
        super().__init__(
            ticket_id="dummy",
            ticket_title="dummy",
            severity="Medium",
            affected_system="",
            slack_channel=channel,
            delivery_status="success",
            slack_message_ts=ts,
            slack_channel_id=channel,
        )


def test_create_incident_ticket_basic():
    alert = "service A down in region eu-west-1"
    ticket = create_incident_ticket(alert)
    assert "id" in ticket and ticket["summary"] == alert.strip()
    assert ticket["status"] == "open"
    assert "triage" in ticket


def test_raise_incident_in_slack_monkeypatch(monkeypatch):
    # Ensure env vars for test
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-fake-token")
    monkeypatch.setenv("SLACK_CHANNEL", "#incidents-test")

    async def _fake_send_to_slack(*args, **kwargs):
        return DummySlackResult()

    async def _fake_fetch_metrics(*args, **kwargs):
        return {"cpu_avg": 85, "memory_avg": 40}

    async def _fake_send_to_resolution_agent(ticket, correlation):
        return {"sent": True, "note": "received"}

    # Patch the implementation functions on the loaded impl module
    monkeypatch.setattr(ida._impl, "async_send_to_slack", _fake_send_to_slack, raising=False)
    monkeypatch.setattr(ida._impl, "fetch_azure_metrics", _fake_fetch_metrics, raising=False)
    monkeypatch.setattr(ida._impl, "send_to_resolution_agent", _fake_send_to_resolution_agent, raising=False)

    ticket = asyncio.run(raise_incident_in_slack("test alert for unit"))
    assert ticket["status"] == "open"
    assert ticket.get("slack_ts") == "999.888"
    assert ticket.get("slack_channel") == "#incidents-test"
    assert ticket.get("resolution_handoff", {}).get("sent") is True


# Incident Detection Agent — Flow & Configuration

# Summary
# - Receives monitoring availability alerts, enriches with Azure Monitor metrics, correlates signals, creates a Slack incident, and hands the incident to the Resolution Agent.

# End-to-end flow
# 1. Alert received from Monitoring Agent (availability reduced).
# 2. Fetch recent metrics from Azure Monitor (CPU, memory, network) — best-effort; Azure SDKs required for full integration.
# 3. Correlate metrics with the alert (heuristics + placeholder for ML scoring).
# 4. Create incident in Slack (Block Kit message; fallback to plain text).
# 5. Send incident details and incident ID to the Resolution Agent for remediation or escalation.

# ## Testing the Incident Detection Agent

# ### Test Location
# The tests for the Incident Detection Agent are located in the `src/workshop/tests` folder.

# ### Running Tests
# 1. Ensure you have a Python virtual environment set up and activated:
#    ```bash
#    python3 -m venv .venv
#    source .venv/bin/activate
#    ```