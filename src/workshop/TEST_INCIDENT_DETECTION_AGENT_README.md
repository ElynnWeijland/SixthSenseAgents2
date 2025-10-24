# Testing the Incident Detection Agent

Overview
- Unit tests are designed to avoid calling real Slack APIs.
- Tests import through the top-level shim (`incident_detection_agent.py`) and monkeypatch the implementation (`_impl`) functions.

Setup
1. Optional venv:
   - python3 -m venv .venv
   - source .venv/bin/activate

2. Install deps:
   - python -m pip install --upgrade pip
   - python -m pip install -r requirements.txt

3. Export (optional) Slack env vars for manual runs:
   - export SLACK_BOT_TOKEN="xoxb-fake-or-real-token"
   - export SLACK_CHANNEL="#incidents-test"

How tests work
- tests/conftest.py ensures repo root is on sys.path.
- tests/test_incident_detection_agent.py:
  - Verifies create_incident_ticket returns expected fields.
  - Monkeypatches the implementation's async_send_to_slack to return a deterministic result, then calls raise_incident_in_slack via asyncio.run(...) to validate integration.

Run tests
- pytest -q

Integration note
- To run an integration flow that posts to Slack, export real SLACK_BOT_TOKEN and SLACK_CHANNEL and call the main trigger. Be mindful that this will post messages.