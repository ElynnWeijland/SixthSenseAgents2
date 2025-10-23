# Incident Detection Agent

Summary
- Receives monitoring availability alerts, enriches with Azure Monitor metrics, correlates signals, creates a Slack incident, and hands the incident to the Resolution Agent.

End-to-end flow
1. Alert received from Monitoring Agent (availability reduced).
2. Fetch recent metrics from Azure Monitor (CPU, memory, network) — best-effort; Azure SDKs required for full integration.
3. Correlate metrics with the alert (heuristics + placeholder for ML scoring).
4. Create incident in Slack (Block Kit message; fallback to plain text).
5. Send incident details and incident ID to the Resolution Agent for remediation or escalation.

Configuration (preferred: export)
- export SLACK_BOT_TOKEN="xoxb-...your-token..."
- export SLACK_CHANNEL="#incidents"
- To enable Azure enrichment, configure `utils.py` / `project_client` and install Azure Monitor SDKs. The agent will run Slack-only flows without Azure SDKs.

Testing
- Tests mock:
  - Slack posting (async_send_to_slack)
  - Azure metrics fetch (fetch_azure_metrics)
  - Resolution handoff (send_to_resolution_agent)
- Run tests: `pytest -q`

Notes
- The Azure fetch/correlation/resolution handoff are best-effort. Failures are logged and do not prevent Slack ticket creation.
- The agent includes `RAISED_BY = "AIDA - Advanced Incident Detection Agent"` and sets `raised_by` on the ticket and includes that in Slack context.
- Do not commit real tokens.