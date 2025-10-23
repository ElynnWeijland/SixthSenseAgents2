# Testing the Incident Detection Agent

Overview
- Unit tests run with `pytest` and avoid real Slack network calls by monkeypatching the implementation's Slack client.
- Tests import the top-level wrapper `incident_detection_agent` so they can run from the repo root.
- Async functions are executed with `asyncio.run(...)` in tests — no pytest-asyncio plugin required.

Setup
1. (Optional) Create & activate venv:
   - python3 -m venv .venv
   - source .venv/bin/activate

2. Install dependencies:
   - python -m pip install --upgrade pip
   - python -m pip install -r requirements.txt

Testing (export approach)
- Set test env vars in the shell (tests also use monkeypatch):
  - export SLACK_BOT_TOKEN="xoxb-fake-or-real-token"
  - export SLACK_CHANNEL="#incidents-test"

What the tests cover
- `create_incident_ticket` returns expected ticket fields.
- `raise_incident_in_slack` is tested by patching the implementation module's `WebClient` so no network calls occur.
- Tests run the async function synchronously with `asyncio.run(...)`.

Run tests
- From repo root:
  - pytest -q
- To run a single test file:
  - pytest -q tests/test_incident_detection_agent.py

Integration note
- To run integration flows that use Azure AI Agents and/or post to Slack:
  - Install Azure SDK packages and configure `utils.py` (project client, endpoints, credentials).
  - Export real `SLACK_BOT_TOKEN` and `SLACK_CHANNEL` (or use a properly configured `.env`).
  - Running `python3 src/workshop/main.py` may create posts in Slack and/or invoke Azure agent runs.

Security
- Tests avoid hitting Slack. Never store real tokens in source control.