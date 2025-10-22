"""
Standalone test script for the Benefits Agent.
This tests the benefits agent independently without requiring the resolution agent.
"""

import asyncio
from benefits_agent import analyze_prevented_issue


async def main():
    print("\n" + "="*80)
    print("BENEFITS AGENT STANDALONE TEST")
    print("="*80 + "\n")

    # Test scenario
    print("Testing scenario: High CPU issue resolved by automated reboot\n")

    result = await analyze_prevented_issue(
        problem_type="High CPU load on webshop VM",
        resolution_method="automated reboot",
        vm_name="webshop-prod-01",
        additional_context="VM was experiencing 95% CPU usage for 30 minutes during peak hours. Automated reboot prevented customer-facing downtime and resolved the issue immediately."
    )

    print("\n" + "-"*80)
    print("TEST RESULT")
    print("-"*80)
    print(f"Success: {result['success']}\n")

    if result['success']:
        print("Financial Analysis:")
        print(result['analysis'])
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")

    print("\n" + "="*80)
    print("TEST COMPLETED")
    print("="*80 + "\n")


if __name__ == "__main__":
    print("Starting Benefits Agent standalone test...")
    asyncio.run(main())
    print("Test finished.")
