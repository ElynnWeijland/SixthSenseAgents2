# SixthSense Agents — Overview of Agents

This folder contains multiple cooperating agents designed to detect, triage, resolve, report, and quantify the impact of infrastructure incidents.

Agents
- Monitoring Agent (monitoring availability)
  - Purpose: Continuously ingest monitoring availability alerts (metrics, uptime checks) and forward meaningful alerts to the incident detection pipeline.
  - Input: Monitoring availability alerts (service, region, timestamp, metric values).
  - Output: Normalized alert payloads that downstream agents consume.
  - Location: design / integration points expected in your monitoring pipeline (not fully implemented in this repo).

- Incident Detection Agent (triage on logs & alerts; create Slack incident)
  - Purpose: Receive monitoring availability alerts, triage (extract key fields: service, region, severity, timestamp), and create an incident in a configured Slack channel.
  - Key behavior:
    - Creates a unique ticket (id, title, summary, created_at, status).
    - Posts a rich Slack message (Block Kit) to the configured channel.
    - Returns ticket details merged with Slack delivery metadata.
  - Implementation: `src/workshop/incident_detection_agent.py`
  - Top-level import wrapper: `/workspaces/SixthSenseAgents2/incident_detection_agent.py` (used by tests)
  - Trigger script: `src/workshop/main.py`

- Resolution Agent (search and resolve / escalate)
  - Purpose: Given an incident, search logs, runbooks, KBs, and other sources to propose remediation steps. Optionally apply automated remediation or escalate when manual intervention is required.
  - Typical flow:
    - Query log sources / vector DB / runbooks.
    - Propose a resolution plan (with confidence & steps).
    - Optionally call remediation tools (runbooks, scripts) or update the incident to escalate.
  - Integration: can call `create_and_send_ticket` or use the same Slack helper to communicate resolution attempts.

- Reporting Agent (update ticket with status & resolution)
  - Purpose: Post updates to the incident (status changes, resolution notes, timeline) and keep the ticket in Slack and any ticketing backend in sync.
  - Behavior:
    - Append status updates to the Slack message or post followups.
    - Persist ticket state if connected to a backend (Azure, JIRA, ServiceNow).
  - Integration points: Slack helper (Block Kit updates), Azure Agent threads, project client flows.

- Benefits Agent (calculate benefits of prevented outage)
  - Purpose: After resolution, calculate financial and operational benefits from avoided downtime (estimated lost revenue avoided, SLA credits prevented, productivity preserved).
  - Inputs: incident duration, affected services, estimated cost/rate.
  - Output: A short benefits report suitable for inclusion in the incident summary and reporting dashboards.

Files in this workspace
- src/workshop/incident_detection_agent.py — Incident Detection Agent (ticket creation & Slack poster).
- src/workshop/main.py — Script to trigger the incident detection agent (guards azure imports).
- /workspaces/SixthSenseAgents2/incident_detection_agent.py — top-level wrapper used to import the implementation from repo root.
- src/workshop/utils.py — shared utilities and Azure project client placeholders (may require Azure SDKs).
- tests/ — unit tests for the incident agent (mock Slack calls).
- tests/conftest.py — test sys.path bootstrap.
- tests/test_incident_detection_agent.py — unit tests for ticket creation & Slack posting.
- requirements.txt — runtime and test dependencies.
- .env.example — example environment variables (do NOT commit secrets).

Configuration
- Preferred: use shell export to set Slack credentials before running:
  - export SLACK_BOT_TOKEN="xoxb-...your-bot-token..."
  - export SLACK_CHANNEL="#incidents"   # or channel ID
- Optionally copy `.env.example` → `.env` for development; code uses python-dotenv when present. Do not commit `.env`.

Run (development)
1. Create & activate a venv (optional):
   - python3 -m venv .venv
   - source .venv/bin/activate
2. Install dependencies:
   - python -m pip install --upgrade pip
   - python -m pip install -r requirements.txt
3. Export Slack env vars:
   - export SLACK_BOT_TOKEN="xoxb-..."
   - export SLACK_CHANNEL="#incidents"
4. Trigger the incident detection agent:
   - python3 src/workshop/main.py

Testing
- Unit tests avoid real Slack calls by monkeypatching the implementation's Slack client.
- Run tests:
  - pytest -q
- Test details:
  - `tests/test_incident_detection_agent.py` verifies ticket creation and Slack posting using a dummy client and `asyncio.run(...)` to invoke async functions synchronously.

Azure integration notes
- Advanced flows (Azure AI Agents for automated ticket generation, run orchestration) require Azure SDKs and configuration in `utils.py`.
- `src/workshop/main.py` guards imports from `utils.py` so simple Slack-only runs work without installing Azure packages.
- To enable Azure-driven flows, install required Azure packages and configure environment variables (project endpoint, subscription, resource group) as described in `utils.py`.

Security and best practices
- Never commit real API tokens or `.env` files with secrets.
- Use least privilege for Slack bot tokens (chat:write limited to intended channels).
- For production, store secrets in your secret manager (Azure Key Vault, CI secrets).
- Test via unit tests and mock external calls before running integration flows.

Extending the system
- Monitoring Agent: integrate with your monitoring system (Prometheus, Azure Monitor, Datadog) to forward normalized alerts.
- Resolution Agent: add connectors to runbooks, remediation pipelines, and orchestration tools.
- Reporting & Benefits Agents: add persistence (database or ticketing backend) to store incident timelines and computed benefit reports.

Contact / Next steps
- To wire up full automation:
  - Configure Azure project client in `utils.py` and install Azure SDKs.
  - Provide a Slack bot token with appropriate scopes.
  - Connect monitoring sources to invoke the incident detection flow automatically.


