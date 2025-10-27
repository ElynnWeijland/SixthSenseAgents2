# SixthSenseAgents2 — Incident Detection Agent

This repository contains a set of cooperating agents to detect, triage, resolve, report, and quantify the impact of infrastructure incidents.

High level agents
- Monitoring Agent
  - Ingests monitoring availability alerts and forwards structured alerts to downstream agents.
  - Input: availability alerts (service, region, timestamp, metric values).
  - Not fully implemented in this repo — integration points expected in your monitoring pipeline.

- Incident Detection Agent
  - Receives availability alerts, triages (extracts service, region, severity, timestamp), optionally enriches via Azure, and creates an incident in Slack.
  - Posts a rich Block Kit message to the configured Slack channel and returns ticket metadata.
  - Implementation: `src/workshop/incident_detection_agent.py` (pure triage + optional Azure enrichment + Slack poster).
  - Top-level import shim for tests: `/workspaces/SixthSenseAgents2/incident_detection_agent.py`
  - Trigger script: `src/workshop/main.py`

- Resolution Agent
  - Searches logs, runbooks, KBs, and proposes remediation steps. It can attempt automated remediation or escalate when needed.
  - Integrates with the incident ticketing flow and Slack helpers.

- Reporting Agent
  - Posts updates to the ticket (status, timeline, resolution) and synchronizes with a backend ticketing system if configured.

- Benefits Agent
  - Calculates financial and operational benefits of prevented outages (estimated revenue preserved, SLA credits avoided, productivity impact).
  - Produces a concise benefits report to attach to incident summaries.

Running locally
1. Optional: create a venv and activate it:
   - python3 -m venv .venv
   - source .venv/bin/activate

2. Install dependencies:
   - python -m pip install --upgrade pip
   - python -m pip install -r requirements.txt

3. Export required Slack env vars:
   - export SLACK_BOT_TOKEN="<your-slack-bot-token>"
   - export SLACK_CHANNEL="<your-slack-channel>"

4. Trigger the incident detection agent:
   - python3 src/workshop/main.py

Testing
- Tests mock Slack interactions and run synchronously via `asyncio.run(...)`.
- Run:
  - pytest -q

Notes
- `src/workshop/main.py` contains a guarded import of `utils` so core Slack-only flows run without Azure SDKs installed.
- Azure-driven workflows require Azure SDK installation and `utils.py` configuration (project endpoint, credentials).
- Do not commit real tokens. Use shell export or secure secret management.