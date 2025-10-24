# Incident Detection Agent — Workflow & Configuration

## Summary
The Incident Detection Agent processes monitoring alerts, enriches them with additional context, and creates actionable incidents in Slack. It also hands off the incident details to the Resolution Agent for further analysis and remediation.

## Workflow

1. **Alert Reception**:
   - Receives alerts from the Monitoring Agent (e.g., reduced availability).

2. **Triage and Parsing**:
   - Extracts key fields from the alert:
     - **Service**: Affected service.
     - **Region**: Region where the issue occurred.
     - **Severity**: Severity of the issue.
     - **Timestamp**: Time the alert was generated.

3. **Azure Metrics Fetching**:
   - Queries Azure Monitor for recent metrics (CPU, memory, network traffic).
   - Best-effort; requires Azure SDKs and proper configuration.

4. **Correlation and Analysis**:
   - Correlates the alert with fetched metrics to confirm or refine the alert.
   - Includes a placeholder for machine learning (ML) scoring.

5. **Incident Creation in Slack**:
   - Creates an incident ticket and posts it to a Slack channel.
   - Uses Slack's Block Kit for rich formatting (fallback to plain text).

6. **Handoff to Resolution Agent**:
   - Sends incident details, correlation results, and metrics to the Resolution Agent for further analysis and remediation.

7. **Logging and Error Handling**:
   - Logs all steps for debugging and monitoring.
   - Handles errors gracefully to ensure the workflow continues.

## Configuration

### Environment Variables
- **Slack Configuration**:
  - `SLACK_BOT_TOKEN`: Slack bot token with `chat:write` scope.
  - `SLACK_CHANNEL`: Slack channel name or ID (e.g., `#incidents`).
- **Azure Configuration**:
  - Requires Azure SDKs and proper configuration in `utils.py`.

### Running the Agent
1. Set up a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate