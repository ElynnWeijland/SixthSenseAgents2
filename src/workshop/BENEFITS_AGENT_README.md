# Benefits Agent - Financial Impact Calculator

## Overview

The Benefits Agent is an AI-powered financial analysis agent that calculates and quantifies the business value of automated incident resolution. It works in conjunction with other agents in the multi-agent system to provide tangible ROI insights for proactive technical interventions.

## Purpose

According to the base prompt (`src/instructions/base_prompt_benefit_agent.txt`), the Benefits Agent serves as Action's dedicated financial analysis assistant for their webshop environment. It translates technical preventions into business value by analyzing:

- **Direct cost savings**: Developer time, infrastructure resources
- **Indirect benefits**: Preserved revenue, customer satisfaction
- **Total financial impact**: Comprehensive ROI analysis with clear methodology

## Integration with Multi-Agent System

The Benefits Agent works as part of a coordinated workflow:

```
Incident Detection → Resolution Agent → Benefits Agent
                          ↓                    ↓
                    Resolves Issue    Calculates ROI
```

### Workflow

1. **Incident Detection**: An issue is identified (e.g., high CPU usage on a VM)
2. **Resolution Agent**: Diagnoses and resolves the incident (e.g., automated VM reboot)
3. **Benefits Agent**: Analyzes the financial impact of the prevention/resolution

## Key Features

### 1. Contextual Financial Analysis

The agent incorporates real-world business metrics:
- Developer hourly rates (€75/hour)
- Average manual resolution time (2 hours)
- VM operational costs (€0.50/hour)
- Revenue impact (€100/minute for webshop)
- Customer satisfaction costs (€500/incident)

### 2. Comprehensive Benefit Calculation

For each prevented issue, the agent calculates:

**Direct Cost Savings:**
- Developer time saved by automated resolution
- Infrastructure resource costs avoided

**Indirect Benefits:**
- Revenue preservation from prevented downtime
- Customer satisfaction value maintained

**Total Financial Impact:**
- Sum of all savings and benefits
- Clear explanation of calculation methodology

### 3. Conversational Business Communication

The agent presents findings in business-friendly terms that help teams understand:
- Not just *how much* value was preserved
- But also *why* preventive measures matter to business outcomes

## Technical Implementation

### File Structure

```
src/workshop/
├── benefits_agent.py          # Main benefits agent implementation
├── resolution_agent.py         # Resolution agent (works before benefits agent)
├── main.py                     # Multi-agent orchestration
└── utils.py                    # Shared utilities

src/instructions/
└── base_prompt_benefit_agent.txt  # Agent instructions and personality
```

### Key Functions

#### `async_calculate_benefits()`

Performs financial calculations based on:
- Problem type
- Resolution method (automated vs. escalated)
- VM information
- Downtime prevented

Returns detailed JSON with:
- Direct savings breakdown
- Indirect benefits calculation
- Total financial impact

#### `create_agent_from_prompt()`

Creates the Benefits Agent instance using:
- Azure AI Agent Service
- Base prompt from instruction file
- Configured calculation tools
- Project client credentials

#### `post_message()`

Handles communication with the agent:
- Posts benefit analysis requests
- Manages tool calls and polling
- Returns formatted financial analysis

#### `analyze_prevented_issue()`

Convenience function for standalone analysis:
- Creates temporary agent instance
- Performs complete benefit calculation
- Cleans up resources automatically

## Usage Example

### Running the Multi-Agent System

```bash
cd src/workshop
python main.py
```

This executes a complete workflow:

1. Simulates an incident (high CPU on VM)
2. Resolution Agent resolves it (automated reboot)
3. Benefits Agent calculates financial impact

### Output Example

```
STEP 2: BENEFITS AGENT - Calculating Financial Impact
================================================================================

Benefits Agent Analysis:
Based on the prevented issue analysis, here's the financial impact:

Direct Cost Savings:
- Developer time saved: 2 hours @ €75/hour = €150
- No manual investigation or escalation required

Indirect Benefits:
- Revenue preserved: 30 minutes downtime prevented @ €100/min = €3,000
- Customer satisfaction maintained: €500

Total Financial Impact: €3,650

This automated resolution demonstrates significant value by preventing customer-facing
downtime and eliminating the need for manual intervention. The proactive approach
preserved both revenue and customer experience while optimizing developer productivity.
```

## Configuration

### Contextual Data (in `benefits_agent.py`)

Adjust these values based on your organization's metrics:

```python
CONTEXTUAL_DATA = {
    "developer_hourly_rate": 75,              # EUR per hour
    "avg_resolution_time_hours": 2,           # Average manual fix time
    "vm_hourly_cost": 0.50,                   # EUR per hour
    "avg_downtime_prevented_minutes": 30,     # Typical downtime
    "revenue_per_minute": 100,                # EUR per minute (webshop)
    "customer_impact_cost": 500,              # Per incident dissatisfaction cost
}
```

### Environment Variables

Ensure these are set in your `.env` file:

```env
PROJECT_ENDPOINT=<your-azure-ai-project-endpoint>
AGENT_MODEL_DEPLOYMENT_NAME=<your-model-deployment>
AZURE_SUBSCRIPTION_ID=<subscription-id>
AZURE_RESOURCE_GROUP_NAME=<resource-group>
AZURE_PROJECT_NAME=<project-name>
```

## Integration Points

### Working with Resolution Agent

The Benefits Agent receives output from the Resolution Agent:

```python
# Resolution Agent output
resolution_result = "The problem is solved, your virtual machine is rebooted."

# Benefits Agent input
benefits_query = f"""
Calculate financial benefits for:
- Original Problem: {incident_description}
- Resolution: {resolution_result}
- Context: VM name, downtime prevented, issue type
"""
```

### Standalone Usage

You can also use the Benefits Agent independently:

```python
from benefits_agent import analyze_prevented_issue

result = await analyze_prevented_issue(
    problem_type="High CPU load",
    resolution_method="automated reboot",
    vm_name="webshop-prod-01",
    additional_context="30 minutes of potential downtime prevented"
)

print(result["analysis"])
```

## Business Value

The Benefits Agent helps stakeholders understand:

1. **ROI of Automation**: Quantify the value of automated incident resolution
2. **Resource Optimization**: Show cost savings from reduced manual intervention
3. **Revenue Protection**: Demonstrate preserved revenue from prevented downtime
4. **Customer Experience**: Highlight the value of proactive issue prevention
5. **Decision Support**: Provide data-driven insights for infrastructure investments

## Future Enhancements

Potential improvements:

- **Historical Tracking**: Store and analyze benefit calculations over time
- **Trend Analysis**: Identify patterns in cost savings
- **Custom Metrics**: Allow organization-specific financial parameters
- **Reporting**: Generate weekly/monthly ROI reports
- **Budget Planning**: Use historical data to justify infrastructure spending

## Dependencies

Required packages (from `requirements.txt`):
- `azure-ai-projects`
- `azure-ai-agents`
- `azure-identity`
- `python-dotenv`

## Support

For issues or questions about the Benefits Agent:

1. Check the base prompt: `src/instructions/base_prompt_benefit_agent.txt`
2. Review the implementation: `src/workshop/benefits_agent.py`
3. Examine the multi-agent workflow: `src/workshop/main.py`

## License

Part of the SixthSenseAgents2 project - see main repository LICENSE file.
