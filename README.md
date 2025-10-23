# SixthSenseAgents2 — Incident Detection Agent

This repository contains an agent that receives monitoring availability alerts and raises incidents in Slack.

What is included
- `src/workshop/incident_detection_agent.py` — core agent implementation (creates tickets, posts to Slack, optional Azure-agent-driven ticketing flow).
- `src/workshop/main.py` — trigger script that calls the agent (guards `utils` import when Azure SDKs are absent).
- `incident_detection_agent.py` — top-level wrapper to load the implementation for tests and top-level imports.
- `tests/` — unit tests that mock Slack interactions.
- `instructions/` — usage and testing READMEs.
- `requirements.txt` — dependencies.
- `.env.example` — example env variables.

Key functionality
- Local Slack posting: `raise_incident_in_slack(alert_text)` posts a formatted message to Slack and returns ticket metadata.
- Agent-driven ticketing (optional): `create_agent_from_prompt`, `post_message`, `create_and_send_ticket` let you use Azure AI Agents to generate ticket content and call `async_send_to_slack`. These require the Azure project client and related SDKs (see `utils.py`).

Environment variables (preferred: export)
- export SLACK_BOT_TOKEN="xoxb-...your-token..."
- export SLACK_CHANNEL="#incidents"
- Optional: export SAMPLE_ALERT to override the sample alert used by `main.py`.

Quick start (using export)
1. Create & activate a venv (optional):
   - python3 -m venv .venv
   - source .venv/bin/activate

2. Install deps:
   - python -m pip install --upgrade pip
   - python -m pip install -r requirements.txt

3. Export env variables:
   - export SLACK_BOT_TOKEN="xoxb-...your-token..."
   - export SLACK_CHANNEL="#incidents"

4. Run the agent trigger:
   - python3 src/workshop/main.py

5. Run tests:
   - pytest -q

Notes
- `main.py` guards import of `utils` so the script runs without Azure SDKs installed. To use Azure-driven ticketing flows, install Azure SDK packages and configure values in `utils.py` / environment.
- Tests monkeypatch the implementation's Slack client to avoid network calls. Integration runs that actually post to Slack will send messages to the configured channel.
- Never commit real tokens. Use `export` or a local `.env` kept out of version control.