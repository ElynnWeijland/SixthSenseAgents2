# Incident Detection Agent

Summary
- Receives monitoring availability alerts and raises an incident in a Slack channel.
- Implementation: `src/workshop/incident_detection_agent.py`.
- A top-level wrapper (`/workspaces/SixthSenseAgents2/incident_detection_agent.py`) loads the implementation so imports from the repo root work in tests and scripts.

Capabilities
- `create_incident_ticket(alert_text: str) -> dict` — pure function that returns a ticket dictionary.
- `raise_incident_in_slack(alert_text: str) -> dict` (async) — posts a formatted message to Slack and returns ticket metadata.
- `async_send_to_slack(...)` -> JSON string (async) — reusable Slack posting helper with Block Kit formatting.
- `create_agent_from_prompt` / `post_message` / `create_and_send_ticket` — optional Azure AI Agents workflow that generates ticket content and invokes the Slack poster. Requires `project_client` and Azure SDKs.

Configuration (preferred: export)
- Export environment variables:
  - `export SLACK_BOT_TOKEN="xoxb-...your-token..."`
  - `export SLACK_CHANNEL="#incidents"`   # or channel ID
- The implementation uses `python-dotenv` if a `.env` file exists, but exporting is recommended for interactive runs and CI.

Run (dev)
1. Setup venv and install deps:
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
   - `python -m pip install --upgrade pip`
   - `python -m pip install -r requirements.txt`

2. Export env vars (example):
   - `export SLACK_BOT_TOKEN="xoxb-...your-token..."`
   - `export SLACK_CHANNEL="#incidents"`

3. Trigger the agent:
   - `python3 src/workshop/main.py`

Azure agent-driven ticketing
- To use the Azure-agent flow (`create_and_send_ticket`), ensure Azure SDKs are installed and `utils.py` is configured (project endpoint, credentials, subscription, etc.). `main.py` guards `utils` import so you can run local Slack-only flows without Azure packages.

Security
- Do not commit real tokens or `.env` containing secrets. Use shell `export` for local runs or secure secret storage in CI.