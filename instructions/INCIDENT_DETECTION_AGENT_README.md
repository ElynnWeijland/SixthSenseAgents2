# Incident Detection Agent

Summary
- Receives monitoring availability alerts and raises an incident in a Slack channel.
- Implementation: `src/workshop/incident_detection_agent.py`.
- A top-level wrapper (`/workspaces/SixthSenseAgents2/incident_detection_agent.py`) loads the implementation so imports from the repo root work in tests and scripts.

Key functions
- `create_incident_ticket(alert_text: str) -> dict` — pure, returns ticket dict (no external calls).
- `raise_incident_in_slack(alert_text: str) -> dict` — async, posts to Slack and returns ticket with Slack metadata.

Configuration (preferred: export)
- Export environment variables in your shell (recommended for interactive runs):
  - export SLACK_BOT_TOKEN="xoxb-...your-token..."
  - export SLACK_CHANNEL="#incidents"   # or channel ID
- Alternatively, copy `.env.example` to `.env` and edit it, then ensure `python-dotenv` is installed. The agent loads .env if present, but exporting is straightforward and avoids committing files.

Files of interest
- `src/workshop/incident_detection_agent.py` — agent implementation
- `src/workshop/main.py` — trigger script (guards utils import if Azure SDKs are missing)
- `incident_detection_agent.py` — top-level wrapper for easier imports/tests
- `tests/` — unit tests that mock Slack interactions
- `requirements.txt` — runtime/test deps
- `.env.example` — example env variables

Run (dev)
1. Create & activate venv (optional):
   - python3 -m venv .venv
   - source .venv/bin/activate

2. Install deps:
   - python -m pip install --upgrade pip
   - python -m pip install -r requirements.txt

3. Export env vars (example):
   - export SLACK_BOT_TOKEN="xoxb-...your-token..."
   - export SLACK_CHANNEL="#incidents"

4. Trigger the agent:
   - python3 src/workshop/main.py

Notes
- `main.py` guards the import of `utils` so the script can run without Azure SDKs installed.
- For integrations that post to Slack, ensure the bot token has `chat:write` permission and the channel is correct.
- Never commit real tokens. Use export or a local `.env` kept out of git.