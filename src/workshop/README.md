# SixthSense Agents — Multi-Agent Incident Management System

This folder contains a coordinated multi-agent system designed to detect, triage, resolve, report, and quantify the impact of infrastructure incidents. The agents work together in a 5-step integrated workflow.

## Integrated Workflow (main.py)

The workflow is orchestrated in a linear pipeline: **Monitoring → Detection → Resolution → Report → Benefits**

### STEP 1: MONITORING AGENT — Analyzing Logs for Abnormalities
- **Purpose**: Analyzes log files from Azure Storage to detect performance anomalies and abnormalities
- **Process**:
  - Retrieves log files from Azure Storage Blob
  - Uses LLM to analyze logs for abnormalities (e.g., elevated response times)
  - Extracts detection timestamp and affected application name
- **Input**: Log file from Azure Storage (e.g., `AvailabilityLogs.log`)
- **Output**:
  - Status: `abnormalities_detected` or `healthy`
  - Detection time (from logs, with timezone support)
  - Application name and abnormal log lines
  - Summary of findings
- **File**: `monitor_agent.py`

### STEP 2: INCIDENT DETECTION AGENT — Processing Abnormalities
- **Purpose**: Converts detected abnormalities into incident tickets and enriches with Azure Monitor metrics
- **Condition**: Only runs if abnormalities are detected in Step 1
- **Process**:
  - Transforms monitoring output to incident detection format
  - Retrieves Azure Monitor metrics for the affected VM (CPU, Memory, Network, Disk)
  - Generates unique ticket ID and severity assessment
  - Sends incident notification to Slack
- **Input**: Abnormality detection from Monitoring Agent
- **Output**:
  - Ticket ID (e.g., `INC1234567`)
  - Incident details (title, severity, application, VM name)
  - Azure Monitor metrics (current system state)
  - Slack message delivery confirmation
- **File**: `incident_detection_agent.py`

### STEP 3: RESOLUTION AGENT — Diagnosing and Resolving Incident
- **Purpose**: Analyzes the incident and determines resolution action or escalation
- **Condition**: Only runs if incident was successfully created in Step 2
- **Process**:
  - Creates a Decision Agent to determine: "solve" vs "escalate"
  - If "solve" (high CPU detected): Attempts VM reboot
  - If "escalate": Forwards to human intervention
- **Input**: Incident ticket with description and metrics from Step 2
- **Output**: Resolution decision and action taken
- **File**: `resolution_agent.py`

### STEP 4: REPORT AGENT — Creating Ticket with Resolution Details
- **Purpose**: Creates a detailed incident report and sends it to Slack
- **Condition**: Only runs if incident was successfully created
- **Process**:
  - Compiles full incident information (detection time, log lines, resolution status)
  - Creates formatted ticket with all contextual information
  - Posts comprehensive incident report to Slack incident channel
- **Input**: Incident data and resolution outcome from Steps 1-3
- **Output**: Formatted ticket posted to Slack with full incident details
- **File**: `report_agent.py`

### STEP 5: BENEFITS AGENT — Calculating Financial Impact
- **Purpose**: Quantifies the business value of proactive incident detection
- **Condition**: Only runs if incident was successfully created
- **Process**:
  - Calculates direct cost savings (developer time saved)
  - Estimates indirect benefits (preserved revenue, customer satisfaction)
  - Computes total financial impact
  - Includes ticket ID in benefits analysis for traceability
- **Input**: Incident details and resolution outcome
- **Output**: Financial benefits analysis posted to Slack
- **File**: `benefits_agent.py`

## Environment Configuration

### Required Environment Variables

The following environment variables are **REQUIRED** to run the integrated workflow. You can set them either:
1. Export them as shell environment variables (`export VAR_NAME=value`)
2. Create a `.env` file in the `src/workshop/` directory (loaded via python-dotenv)

#### Azure AI/Agents Configuration (Required)
These enable the agent framework and LLM integration:

```bash
# Azure subscription ID
AZURE_SUBSCRIPTION_ID=your-subscription-id

# Azure resource group name containing your resources
AZURE_RESOURCE_GROUP_NAME=your-resource-group-name

# Azure AI Project name (the AI Foundry project)
AZURE_PROJECT_NAME=your-ai-project-name

# Azure AI Project endpoint (full URL)
PROJECT_ENDPOINT=https://your-region.api.cognitive.microsoft.com/

# Azure OpenAI deployment name (the model deployment in your subscription)
AGENT_MODEL_DEPLOYMENT_NAME=gpt-4-deployment-name
```

#### Azure Storage Configuration (Required)
Required to retrieve log files for analysis:

```bash
# Azure Storage account name (without .blob.core.windows.net)
STORAGE_ACCOUNT_NAME=yourstorageaccount

# Storage container name where logs are stored (default: "logs")
CONTAINER_NAME=logs

# Log file name to analyze (default: "AvailabilityLogs.log")
BLOB_NAME=AvailabilityLogs.log
```

#### Slack Configuration (Required)
Required to send incident notifications:

```bash
# Slack bot token (starts with xoxb-)
# Create a bot app at: https://api.slack.com/apps
SLACK_BOT_TOKEN=xoxb-your-bot-token-here

# Slack channel for incident notifications (default: "#incidents")
SLACK_CHANNEL=#incidents
```

#### Azure VM Configuration (Optional)
Optional for automatic VM remediation:

```bash
# Azure VM name for automatic reboot (default: "VirtualMachine")
# Used when the Resolution Agent decides to "solve" high CPU incidents
AZURE_VM_NAME=VirtualMachine
```

#### Environment Type (Optional)
Controls path resolution for different deployments:

```bash
# Environment: "local" or "container" (default: "local")
ENVIRONMENT=local
```

### Sample .env File

Create `src/workshop/.env` with all required variables:

```bash
# Azure AI Configuration
AZURE_SUBSCRIPTION_ID=b9b7e9a1-b2d9-46f6-bbd4-d4aa39986192
AZURE_RESOURCE_GROUP_NAME=rg-kotp-team-6
AZURE_PROJECT_NAME=prj-kotpagents-2diq
PROJECT_ENDPOINT=https://aif-kotpagents-2diq.services.ai.azure.com/api/projects/prj-kotpagents-2diq
AGENT_MODEL_DEPLOYMENT_NAME=gpt-4

# Azure Storage
STORAGE_ACCOUNT_NAME=stkotpagents2diq
CONTAINER_NAME=logs
BLOB_NAME=AvailabilityLogs.log

# Slack
SLACK_BOT_TOKEN=xoxb-your-token-here
SLACK_CHANNEL=#incidents

# Optional
AZURE_VM_NAME=VirtualMachine
ENVIRONMENT=local
```

### Authentication Requirements

- **Azure**: Ensure you're authenticated via `az login` or have Azure SDK credentials configured
- **Slack**: Create a bot at https://api.slack.com/apps and grant it permissions to post messages
  - Required scopes: `chat:write`, `channels:read`

## Running the Workflow

### Basic Execution

```bash
cd src/workshop
python3.10 main.py
```

This executes the complete 5-step integrated workflow and outputs results for each stage.

### Testing with Simulated CPU Issue

To test the full incident detection and resolution workflow including VM reboot, you can simulate a high CPU load on the Azure VM:

1. **Connect to the VirtualMachine in Azure** via SSH or RDP

2. **Stress the CPU** (before running main.py):
```bash
stress -c 3
```
This command stresses 3 CPU cores. The stress will run until interrupted.
- On Linux: Press `Ctrl+C` to stop the stress
- Ensure `stress` is installed: `sudo apt-get install stress` (Ubuntu/Debian) or `yum install stress` (RHEL/CentOS)

3. **Keep the stress running** while executing main.py:
```bash
cd src/workshop
python3.10 main.py
```

4. **Expected Behavior**:
   - Step 1 (Monitoring Agent) will detect log abnormalities
   - Step 2 (Incident Detection Agent) will fetch Azure Monitor metrics showing HIGH CPU (>80%)
   - Step 3 (Resolution Agent) will decide to "solve" and **automatically reboot the VM**
   - Steps 4 & 5 will create incident reports and benefits analysis

### Without CPU Stress

If you run main.py without CPU stress, the workflow will proceed through all 5 steps, but the Resolution Agent will likely "escalate" instead of attempting to reboot, as the CPU won't be high enough to warrant automatic remediation.

## Agents

- **Monitoring Agent** (`monitor_agent.py`)
  - Analyzes logs for performance abnormalities
  - Extracts detection timestamps and affected applications

- **Incident Detection Agent** (`incident_detection_agent.py`)
  - Converts abnormalities to incident tickets
  - Retrieves Azure Monitor metrics for system context
  - Integrates with Slack for incident notification

- **Resolution Agent** (`resolution_agent.py`)
  - Makes solve/escalate decisions
  - Can execute remediation actions (e.g., VM reboot)

- **Report Agent** (`report_agent.py`)
  - Compiles and formats incident reports
  - Posts detailed tickets to Slack

- **Benefits Agent** (`benefits_agent.py`)
  - Calculates financial impact of prevention
  - Demonstrates ROI of proactive monitoring

## Key Features

- **Timestamp Handling**: Supports both UTC (Z-suffix) and timezone-aware timestamps (±HH:MM)
- **Azure Integration**:
  - Fetches metrics from Azure Monitor REST API
  - Supports VM reboot for high-CPU incidents
- **Slack Integration**: Posts formatted messages with incident details to configured channel
- **Error Handling**: Graceful degradation with fallbacks and logging
- **Modular Design**: Each agent can be tested independently or run as part of the workflow


