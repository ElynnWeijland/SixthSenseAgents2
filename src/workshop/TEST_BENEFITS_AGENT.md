# How to Test-Run the Benefits Agent

## Prerequisites

Before running the Benefits Agent, ensure you have:

1. **Azure AI Foundry Project** set up
2. **Python 3.10+** installed
3. **Azure credentials** configured

## Step-by-Step Test Instructions

### Step 1: Install Dependencies

Navigate to the workshop directory and install required packages:

```bash
cd /home/dylanmattijssen/SixthSenseAgents2/src/workshop
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

Create a `.env` file in the workshop directory:

```bash
cp .env.sample .env
```

Then edit the `.env` file with your Azure credentials:

```bash
nano .env  # or use your preferred editor
```

Required variables:
```env
AZURE_SUBSCRIPTION_ID=<your-subscription-id>
AZURE_RESOURCE_GROUP_NAME=<your-resource-group>
AZURE_PROJECT_NAME=<your-ai-foundry-project-name>
AGENT_MODEL_DEPLOYMENT_NAME=gpt41  # or your model deployment name
PROJECT_ENDPOINT=https://<your-resource>.services.ai.azure.com/api/projects/<project-name>
```

### Step 3: Authenticate with Azure

Make sure you're logged into Azure CLI:

```bash
az login
```

Or set up your Azure credentials using one of these methods:
- Azure CLI authentication (recommended)
- Environment variables
- Managed Identity (if running in Azure)

### Step 4: Run the Multi-Agent System

Run the main script to test the complete workflow (Resolution Agent → Benefits Agent):

```bash
cd /home/dylanmattijssen/SixthSenseAgents2/src/workshop
python main.py
```

**Expected Output:**
```
Starting multi-agent system...

================================================================================
MULTI-AGENT WORKFLOW: Resolution + Benefits Analysis
================================================================================

Simulating an incident scenario...

Incident Report:
  VM 'webshop-prod-01' is experiencing high CPU usage at 95% for the past 30 minutes

================================================================================
STEP 1: RESOLUTION AGENT - Diagnosing and Resolving Issue
================================================================================

Creating resolution agent...
[... resolution process ...]

Resolution Agent Output:
  The problem is solved, your virtual machine is rebooted.

================================================================================
STEP 2: BENEFITS AGENT - Calculating Financial Impact
================================================================================

Creating benefits agent...
[... benefits calculation ...]

Benefits Agent Analysis:
[Financial analysis showing cost savings, revenue preserved, and total impact]

================================================================================
MULTI-AGENT WORKFLOW COMPLETED
================================================================================

Program finished.
```

## Alternative Testing Methods

### Method 1: Test Benefits Agent Standalone

Create a test script to run only the Benefits Agent:

```python
# test_benefits_only.py
import asyncio
from benefits_agent import analyze_prevented_issue

async def test():
    result = await analyze_prevented_issue(
        problem_type="High CPU load on webshop VM",
        resolution_method="automated reboot",
        vm_name="webshop-prod-01",
        additional_context="30 minutes of potential downtime prevented during peak hours"
    )

    print("Success:", result["success"])
    print("\nAnalysis:\n", result["analysis"])

if __name__ == "__main__":
    asyncio.run(test())
```

Run it:
```bash
python test_benefits_only.py
```

### Method 2: Test with Custom Scenario

Modify `main.py` to test different scenarios:

```python
# Change the incident description in main.py:
incident_description = "Database server experiencing connection timeout issues"
# or
incident_description = "Memory leak detected in application server"
```

### Method 3: Interactive Testing

Create an interactive test script:

```python
# interactive_test.py
import asyncio
from benefits_agent import create_agent_from_prompt, post_message
from utils import project_client

async def interactive_test():
    with project_client:
        agent, thread = await create_agent_from_prompt()

        try:
            print("Benefits Agent Interactive Test")
            print("="*50)

            while True:
                print("\nDescribe the prevented issue (or 'exit' to quit):")
                user_input = input("> ")

                if user_input.lower() == 'exit':
                    break

                result = await post_message(
                    thread_id=thread.id,
                    content=user_input,
                    agent=agent,
                    thread=thread
                )

                print("\nBenefits Analysis:")
                print("-" * 50)
                print(result)

        finally:
            project_client.agents.delete_agent(agent.id)
            print("\nAgent cleaned up.")

if __name__ == "__main__":
    asyncio.run(interactive_test())
```

## Troubleshooting

### Issue: "resolution_agent not found"

The main.py will gracefully skip the resolution agent if it's not available. To ensure it works:

```bash
# Check if resolution_agent.py exists
ls -la /home/dylanmattijssen/SixthSenseAgents2/src/workshop/resolution_agent.py
```

If missing, you can still test benefits agent standalone using Method 1 above.

### Issue: Authentication Errors

```bash
# Re-authenticate with Azure
az login
az account set --subscription <your-subscription-id>
```

### Issue: Missing Environment Variables

```bash
# Check your .env file
cat /home/dylanmattijssen/SixthSenseAgents2/src/workshop/.env

# Verify it contains all required variables
```

### Issue: Module Import Errors

```bash
# Reinstall dependencies
pip install -r requirements.txt --upgrade

# Or install specific packages
pip install azure-ai-projects azure-ai-agents azure-identity python-dotenv
```

### Issue: Agent Creation Fails

Check that:
1. Your Azure AI Foundry project is running
2. The model deployment name is correct
3. You have proper permissions on the Azure resources
4. The PROJECT_ENDPOINT is correct

## Debugging Tips

### Enable Detailed Logging

Add this to the top of your test script:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Agent Status

```python
# In your test script, print agent details
print(f"Agent ID: {agent.id}")
print(f"Agent Name: {agent.name}")
print(f"Thread ID: {thread.id}")
```

### Verify Tool Registration

The benefits agent registers a calculation tool. Verify it's loaded:

```python
print(f"Toolset: {toolset}")
```

## Expected Test Results

A successful test run should show:

✅ Agent created successfully
✅ Thread created successfully
✅ Tool registration completed
✅ Message posted to agent
✅ Run completed with status: completed
✅ Financial analysis returned
✅ Agent cleaned up

## Next Steps After Testing

1. **Customize Financial Metrics**: Edit `CONTEXTUAL_DATA` in `benefits_agent.py` to match your organization
2. **Integrate with Other Agents**: Connect with monitoring or ticketing agents
3. **Add Historical Tracking**: Store benefit calculations in a database
4. **Create Reports**: Generate weekly/monthly ROI summaries

## Quick Test Command

For a quick test without modifying files:

```bash
cd /home/dylanmattijssen/SixthSenseAgents2/src/workshop && python main.py
```

This will run the complete multi-agent workflow with a simulated incident scenario.
