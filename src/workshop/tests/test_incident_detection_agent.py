import os
import asyncio

from incident_detection_agent import create_incident_ticket, raise_incident_in_slack


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

    # Patch the actual functions in the incident_detection_agent module
    monkeypatch.setattr("incident_detection_agent.async_send_to_slack", _fake_send_to_slack)
    monkeypatch.setattr("incident_detection_agent.fetch_azure_metrics", _fake_fetch_metrics)
    monkeypatch.setattr("incident_detection_agent.send_to_resolution_agent", _fake_send_to_resolution_agent)

    ticket = asyncio.run(raise_incident_in_slack("test alert for unit"))
    assert ticket["status"] == "open"
    assert ticket.get("slack_ts") == "999.888"
    assert ticket.get("slack_channel") == "#incidents-test"
    assert ticket.get("resolution_handoff", {}).get("sent") is True