# Incident Detection Agent — Workflow & Configuration

## Summary
The Incident Detection Agent processes monitoring alerts, enriches them with additional context, and creates actionable incidents in Slack. It also hands off the incident details to the Resolution Agent for further analysis and remediation.

## Workflow

1. **Alert Reception**:
   - Receives a JSON payload from the Monitoring Agent. The payload includes:
     - **status**: Status of the alert (e.g., "abnormality_detected").
     - **title**: A short title describing the issue.
     - **short_description**: A brief description of the detected issue.
     - **detection_time**: The time the abnormality was detected.
     - **application_name**: The name of the affected application.
     - **related_log_lines**: Log lines related to the detected issue.
     - **timestamp_detected**: The time the alert was generated.

2. **Triage and Parsing**:
   - Extracts key fields from the JSON payload:
     - **Service**: Derived from `application_name`.
     - **Region**: Defaults to "unknown".
     - **Severity**: Defaults to "Medium".
     - **Timestamp**: Derived from `detection_time`.

3. **Azure Metrics Fetching**:
   - Queries Azure Monitor for recent metrics (e.g., CPU, memory, network traffic).
   - Best-effort; requires Azure SDKs and proper configuration.

4. **Correlation and Analysis**:
   - Correlates the alert with fetched metrics and related log lines to confirm or refine the alert.
   - Includes a placeholder for machine learning (ML) scoring.

5. **Incident Creation in Slack**:
   - Creates an incident ticket and posts it to a Slack channel.
   - Uses Slack's Block Kit for rich formatting (fallback to plain text).

6. **Handoff to Resolution Agent**:
   - Sends incident details, correlation results, and metrics to the Resolution Agent for further analysis and remediation.

7. **Logging and Error Handling**:
   - Logs all steps for debugging and monitoring.
   - Handles errors gracefully to ensure the workflow continues.

## Input Format

The agent expects a JSON payload from the Monitoring Agent with the following structure:

```json
{
  "status": "abnormality_detected",
  "title": "Performance Degradation Detected",
  "short_description": "Gradually increasing response times observed for AppZwaagdijk, indicating a performance degradation trend.",
  "detection_time": "2025-10-21T17:07:00+02:00",
  "application_name": "AppZwaagdijk",
  "related_log_lines": [
    "2025-10-21T17:07:00+02:00 app=AppZwaagdijk method=GET path=/health status=200 response_time_ms=120",
    "2025-10-21T17:26:00+02:00 app=AppZwaagdijk method=GET path=/health status=200 response_time_ms=215",
    "2025-10-21T18:46:00+02:00 app=AppZwaagdijk method=GET path=/health status=200 response_time_ms=615"
  ],
  "timestamp_detected": "2025-10-24T11:59:24.577368"
}
```