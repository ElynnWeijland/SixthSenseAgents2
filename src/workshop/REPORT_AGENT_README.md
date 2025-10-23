# Report Agent - Slack Ticketing Integration

## Overview

The Report Agent is an AI-powered ticketing system that creates structured IT tickets from incident reports and sends them to Slack. It transforms technical incident information into professional, well-formatted tickets for efficient team communication and tracking.

## Purpose

The Report Agent serves as the notification and documentation layer in the multi-agent system, automatically:

- Creating structured tickets from incident and resolution data
- Formatting tickets with proper severity levels and categorization
- Sending formatted tickets to Slack channels using Slack Block Kit
- Generating unique ticket IDs for tracking
- Including timestamps and all relevant incident details

## Integration with Multi-Agent System

```
Incident Detection → Resolution Agent → Benefits Agent → Report Agent
                          ↓                    ↓              ↓
                    Resolves Issue    Calculates ROI   Creates Ticket
                                                            ↓
                                                        Sends to Slack
```

## Features

### 1. Automated Ticket Creation

- Extracts key incident details (affected systems, severity, technical specifics)
- Generates unique ticket IDs
- Creates clear, actionable ticket titles
- Formats information for easy readability

### 2. Slack Integration

- Uses Slack Block Kit for rich formatting
- Supports custom channels
- Includes severity indicators
- Provides fallback text for notifications
- Returns message timestamps for tracking

### 3. Comprehensive Ticket Information

Each ticket includes:
- **Ticket ID**: Unique identifier
- **Title**: Concise description
- **Severity**: Low, Medium, High, Critical
- **Affected System**: VM/service name
- **Incident Details**: Full description
- **Resolution**: Steps taken or status
- **Timestamp**: Creation time

## Setup Instructions

### Step 1: Install Dependencies

The Slack SDK is required:

```bash
cd /home/dylanmattijssen/SixthSenseAgents2/src/workshop
pip3 install -r requirements.txt
```

### Step 2: Create a Slack App

1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Name your app (e.g., "IT Ticket Bot")
4. Select your workspace

### Step 3: Configure Bot Permissions

In your Slack app settings:

1. Navigate to **OAuth & Permissions**
2. Under **Bot Token Scopes**, add these scopes:
   - `chat:write` - Send messages
   - `chat:write.customize` - Customize message appearance
3. Click **Install to Workspace**
4. Copy the **Bot User OAuth Token** (starts with `xoxb-`)

### Step 4: Configure Environment Variables

Add to your `.env` file:

```env
# Slack Configuration (for Report Agent)
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_CHANNEL=#incidents  # or your preferred channel
```

**Important**: Make sure the bot is invited to the channel:
```
/invite @YourBotName
```

### Step 5: Verify Azure Authentication

Ensure you're logged in with Azure CLI:

```bash
az login
az account show
```

## Usage

### Standalone Testing

Test the report agent independently:

```bash
cd /home/dylanmattijssen/SixthSenseAgents2/src/workshop
python3 test_report_standalone.py
```

### Integration with Other Agents

Use in your multi-agent workflow:

```python
from report_agent import create_and_send_ticket

# After resolution
result = await create_and_send_ticket(
    incident_description="High CPU usage on webshop-prod-01",
    resolution_output="Automated reboot successful",
    severity="High",
    affected_system="webshop-prod-01"
)

if result['success']:
    print("Ticket created and sent to Slack!")
else:
    print(f"Error: {result['error']}")
```

## Slack Message Format

Tickets appear in Slack with this structure:

```
🎫 High CPU Load on webshop-prod-01

Ticket ID: INC-20231115-001
Severity: High

Affected System: webshop-prod-01

Incident Details:
VM experiencing 95% CPU usage for 30 minutes during peak hours.
Customer-facing services impacted.

Resolution:
Automated reboot performed successfully. CPU usage returned to normal.

Created: 2023-11-15 14:30:45
```

## Configuration Options

### Severity Levels

Choose from:
- `Low` - Minor issues, no immediate impact
- `Medium` - Moderate impact, can wait
- `High` - Significant impact, needs attention
- `Critical` - Severe impact, immediate action required

### Custom Channels

Set different channels per environment:

```env
# Development
SLACK_CHANNEL=#dev-incidents

# Production
SLACK_CHANNEL=#prod-alerts
```

## Troubleshooting

### "Slack SDK not installed"

```bash
pip3 install slack-sdk
```

### "SLACK_BOT_TOKEN not configured"

Add the token to your `.env` file:

```env
SLACK_BOT_TOKEN=xoxb-your-token-here
```

### "not_in_channel" Error

Invite the bot to your Slack channel:

```
/invite @YourBotName
```

### "invalid_auth" Error

1. Verify your token starts with `xoxb-`
2. Check the token hasn't expired
3. Reinstall the app to your workspace if needed

### Agent Creation Fails

Ensure:
1. Azure authentication is working (`az account show`)
2. `.env` has all Azure configuration
3. `base_prompt_ticketing_agent.txt` exists in `src/instructions/`

## Testing Without Slack

To test the agent logic without Slack:

1. Comment out or don't set `SLACK_BOT_TOKEN`
2. The agent will still create tickets but report "SLACK_BOT_TOKEN not configured"
3. Useful for testing ticket formatting and agent behavior

## File Structure

```
src/workshop/
├── report_agent.py              # Main report agent implementation
├── test_report_standalone.py    # Standalone test script
└── REPORT_AGENT_README.md       # This file

src/instructions/
└── base_prompt_ticketing_agent.txt  # Agent instructions
```

## Key Functions

### `async_send_to_slack()`

Sends formatted ticket to Slack channel.

**Parameters:**
- `ticket_title` - Title of the ticket
- `ticket_id` - Unique identifier
- `incident_details` - Description
- `severity` - Priority level
- `affected_system` - System name
- `resolution` - Resolution details

**Returns:** JSON with delivery status and Slack message info

### `create_agent_from_prompt()`

Creates the Report Agent instance using Azure AI Agent Service.

**Returns:** Tuple of (agent, thread)

### `create_and_send_ticket()`

Convenience function for end-to-end ticket creation.

**Parameters:**
- `incident_description` - What happened
- `resolution_output` - How it was resolved
- `severity` - Priority level
- `affected_system` - Affected system name

**Returns:** Dictionary with success status and ticket details

## Environment Variables Reference

```env
# Required for Azure AI
AZURE_SUBSCRIPTION_ID=...
AZURE_RESOURCE_GROUP_NAME=...
AZURE_PROJECT_NAME=...
AGENT_MODEL_DEPLOYMENT_NAME=gpt41
PROJECT_ENDPOINT=...

# Required for Slack integration
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL=#incidents
```

## Best Practices

1. **Channel Organization**: Use different channels for different severity levels
2. **Bot Naming**: Use a clear bot name like "IT Ticket Bot" or "Incident Reporter"
3. **Testing**: Always test in a development channel first
4. **Token Security**: Never commit `.env` file to git
5. **Error Handling**: Check `result['success']` before assuming ticket was sent

## Next Steps

- Integrate with the full multi-agent workflow (main.py)
- Set up Slack notifications for ticket updates
- Create custom ticket templates
- Add ticket status tracking
- Implement ticket assignment to team members

## Support

For issues:
1. Check this README
2. Review `src/instructions/base_prompt_ticketing_agent.txt`
3. Examine `src/workshop/report_agent.py`
4. Test with `python3 test_report_standalone.py`

## License

Part of the SixthSenseAgents2 project - see main repository LICENSE file.
