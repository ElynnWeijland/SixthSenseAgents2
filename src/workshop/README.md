# SixthSense Agents — Overview of Agents

This folder contains cooperating agents designed to detect, triage, resolve, report, and quantify the impact of infrastructure incidents.

Agents
- Monitoring Agent (monitoring availability)
  - Purpose: Continuously ingest monitoring availability alerts and forward meaningful alerts to the incident detection pipeline.
  - Input: Monitoring availability alerts (service, region, timestamp, metric values).
  - Output: Normalized alert payloads that downstream agents consume.

- Incident Detection Agent (triage & Slack incident creation)
  - Purpose: Receive availability alerts, triage (service, region, severity, timestamp), optionally enrich using Azure APIs, and create an incident in a configured Slack channel.
  - Behavior:
    - Produces a ticket dict (id, title, summary, created_at, status, triage data).
    - Optionally queries Azure to enrich context (best-effort; does not require Azure SDKs).
    - Posts a Block Kit styled message to Slack (with fallback to plain text for test/dummy clients).
  - Implementation: `src/workshop/incident_detection_agent.py`
  - Trigger script: `src/workshop/main.py`
  - Test shim: `/workspaces/SixthSenseAgents2/incident_detection_agent.py`

- Resolution Agent
  - Purpose: Search logs, runbooks, KBs, and propose remediation steps or escalate.
  - Integration: can call Slack helper or create follow-ups to the ticket.

- Reporting Agent
  - Purpose: Post status updates, timeline, resolution notes to Slack and ticketing backends.

- Benefits Agent
  - Purpose: Calculate estimated benefits from prevented downtime and add to incident reports.

Development notes
- Slack credentials are provided via exported environment variables:
  - export SLACK_BOT_TOKEN="xoxb-..."
  - export SLACK_CHANNEL="#incidents"
- The code uses python-dotenv to load a local .env if present, but exporting is recommended.
- `main.py` guards import of `utils` so Slack-only runs don't require Azure SDKs.


