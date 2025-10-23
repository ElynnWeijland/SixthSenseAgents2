import asyncio
import os

# Guard import of utils to avoid failing when Azure SDKs aren't installed.
try:
    from utils import project_client
except Exception:
    project_client = None

from incident_detection_agent import raise_incident_in_slack


async def main() -> None:
    """Trigger the incident detection agent with a sample monitoring availability alert.

    Configure SLACK_BOT_TOKEN and SLACK_CHANNEL in your environment (see .env.example).
    """
    alert_text = os.getenv(
        "SAMPLE_ALERT",
        "ALERT: service-x availability dropped below 90% at 2025-10-23T12:00:00Z",
    )

    if project_client:
        with project_client:
            ticket = await raise_incident_in_slack(alert_text)
    else:
        ticket = await raise_incident_in_slack(alert_text)

    print("Incident ticket result:")
    print(ticket)


if __name__ == "__main__":
    print("Starting incident detection trigger...")
    asyncio.run(main())
    print("Finished.")

