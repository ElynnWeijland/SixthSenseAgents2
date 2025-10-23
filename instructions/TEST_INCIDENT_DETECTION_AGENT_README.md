# Testing the Incident Detection Agent

Overview
- Unit tests run with `pytest` and avoid real Slack network calls by monkeypatching the implementation's Slack client.
- Tests import the top-level wrapper `incident_detection_agent` so they can run from the repo root.
- Async function `raise_incident_in_slack` is invoked synchronously in tests using `asyncio.run(...)` (no pytest-asyncio required).

Setup
1. (Optional) Create & activate venv:
   - python3 -m venv .venv
   - source .venv/bin/activate

2. Install dependencies:
   - python -m pip install --upgrade pip
   - python -m pip install -r requirements.txt

Testing (export approach)
- Set test env vars in the shell (tests use monkeypatch, but exporting is fine for manual runs):
  - export SLACK_BOT_TOKEN="xoxb-fake-or-real-token"
  - export SLACK_CHANNEL="#incidents-test"

Run tests
- From repo root:
  - pytest -q
- To run a single test file:
  - pytest -q tests/test_incident_detection_agent.py

Test specifics
- `tests/conftest.py` ensures repo root is on `sys.path`.
- `tests/test_incident_detection_agent.py`:
  - Verifies `create_incident_ticket` fields.
  - Monkeypatches the implementation module (`ida._impl`) to replace `WebClient` with a dummy client, avoiding network calls.
  - Calls `raise_incident_in_slack` with `asyncio.run(...)` to run the coroutine synchronously.

Integration note
- To run an integration test that posts to Slack, export real `SLACK_BOT_TOKEN` and `SLACK_CHANNEL` (or set them in `.env`), then call `python3 src/workshop/main.py`. Be aware this will post messages to Slack.

Security
- Tests are written to avoid hitting Slack. Never store real tokens in source control.