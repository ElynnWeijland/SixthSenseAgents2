"""
Standalone test script for the Report Agent.
This tests the report agent independently and sends tickets to Slack.
"""

import asyncio
from report_agent import create_and_send_ticket


async def main():
    print("\n" + "="*80)
    print("REPORT AGENT STANDALONE TEST")
    print("="*80 + "\n")

    # Test scenario
    print("Testing scenario: Creating and sending ticket for high CPU incident\n")

    result = await create_and_send_ticket(
        incident_description="VM 'webshop-prod-01' experiencing 95% CPU usage for 30 minutes during peak hours. Customer-facing services impacted.",
        resolution_output="Automated reboot performed successfully. CPU usage returned to normal levels (25%). All services restored.",
        severity="High",
        affected_system="webshop-prod-01"
    )

    print("\n" + "-"*80)
    print("TEST RESULT")
    print("-"*80)
    print(f"Success: {result['success']}\n")

    if result['success']:
        print("Ticket Details:")
        print(result['ticket_details'])
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")

    print("\n" + "="*80)
    print("TEST COMPLETED")
    print("="*80 + "\n")


if __name__ == "__main__":
    print("Starting Report Agent standalone test...")
    asyncio.run(main())
    print("Test finished.")
