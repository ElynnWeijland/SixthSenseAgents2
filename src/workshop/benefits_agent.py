import os
import time
import asyncio
import logging
from typing import Tuple, Dict, Any, Optional
import json
from datetime import datetime

from azure.ai.agents.models import MessageRole

from utils import (
    project_client,
    API_DEPLOYMENT_NAME,
    add_agent_tools,
    toolset,
    AZURE_RESOURCE_GROUP_NAME,
    AZURE_SUBSCRIPTION_ID,
)
from azure.ai.agents.models import AsyncFunctionTool

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
    SLACK_AVAILABLE = True
except ImportError:
    SLACK_AVAILABLE = False
    print("Warning: slack_sdk not installed. Run: pip install slack-sdk")


logger = logging.getLogger(__name__)


def get_revenue_per_hour_by_time(hour: int = 12) -> float:
    """Get revenue per hour based on time of day from business case data.

    Args:
        hour: Hour of day (0-23)

    Returns:
        Revenue per hour in EUR
    """
    if 0 <= hour < 6:
        return CONTEXTUAL_DATA["webshop_revenue_per_hour"]["00:00-06:00"]
    elif 6 <= hour < 9:
        return CONTEXTUAL_DATA["webshop_revenue_per_hour"]["06:00-09:00"]
    elif 9 <= hour < 12:
        return CONTEXTUAL_DATA["webshop_revenue_per_hour"]["09:00-12:00"]
    elif 12 <= hour < 15:
        return CONTEXTUAL_DATA["webshop_revenue_per_hour"]["12:00-15:00"]
    elif 15 <= hour < 18:
        return CONTEXTUAL_DATA["webshop_revenue_per_hour"]["15:00-18:00"]
    elif 18 <= hour < 21:
        return CONTEXTUAL_DATA["webshop_revenue_per_hour"]["18:00-21:00"]
    else:  # 21:00-00:00
        return CONTEXTUAL_DATA["webshop_revenue_per_hour"]["21:00-00:00"]


def get_vm_cost_per_hour(vm_name: str = "") -> float:
    """Get VM cost per hour from Azure cost overview data.

    Args:
        vm_name: Name of the VM (to infer VM type)

    Returns:
        Hourly VM cost in EUR
    """
    # Try to infer VM type from name, default to B4as_v2 for production workloads
    vm_name_lower = vm_name.lower()
    if "prod" in vm_name_lower or "webshop" in vm_name_lower:
        return CONTEXTUAL_DATA["vm_costs"]["B4as_v2"]  # Production workload
    elif "test" in vm_name_lower or "dev" in vm_name_lower:
        return CONTEXTUAL_DATA["vm_costs"]["B2s"]  # Test/dev workload
    else:
        return CONTEXTUAL_DATA["vm_costs"]["D4s_v3"]  # General purpose default


async def async_send_benefits_to_slack(
    incident_description: str = "",
    resolution_method: str = "",
    total_benefit_eur: float = 0.0,
    revenue_preserved_eur: float = 0.0,
    developer_cost_saved_eur: float = 0.0,
    vm_name: str = "",
    downtime_prevented_minutes: int = 30,
    additional_details: str = "",
    ticket_id: str = "",  # Link to the incident ticket
    thread_ts: str = None,  # Thread timestamp for threading
    **kwargs  # Accept additional parameters for flexibility
) -> str:
    """Send benefits analysis to Slack incident channel with optional threading support.

    Args:
        incident_description: Description of the incident that was resolved
        resolution_method: How the incident was resolved
        total_benefit_eur: Total financial benefit calculated
        revenue_preserved_eur: Revenue preserved by preventing downtime
        developer_cost_saved_eur: Developer cost savings
        vm_name: Name of the affected VM
        downtime_prevented_minutes: Minutes of downtime prevented
        additional_details: Additional context or details
        ticket_id: Related incident ticket ID for cross-reference
        thread_ts: Thread timestamp to reply to (for threading)
        **kwargs: Additional parameters (e.g., total_benefit, revenue_preserved, etc.)

    Returns:
        JSON string with Slack delivery status
    """
    await asyncio.sleep(0.05)  # Simulate async processing

    # Handle alternative parameter names that the LLM might use
    # Also handle formatted strings like '€30,085' by cleaning them
    def clean_currency(value) -> float:
        """Convert currency string or number to float."""
        if isinstance(value, (int, float)):
            return float(value)
        # Remove currency symbols, commas, and spaces
        cleaned = str(value).replace('€', '').replace('$', '').replace(',', '').replace(' ', '').strip()
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    if 'total_benefit' in kwargs:
        total_benefit_eur = clean_currency(kwargs['total_benefit'])
    if 'revenue_preserved' in kwargs:
        revenue_preserved_eur = clean_currency(kwargs['revenue_preserved'])
    if 'developer_cost_saved' in kwargs:
        developer_cost_saved_eur = clean_currency(kwargs['developer_cost_saved'])

    # Also clean the main parameters in case they're formatted
    total_benefit_eur = clean_currency(total_benefit_eur)
    revenue_preserved_eur = clean_currency(revenue_preserved_eur)
    developer_cost_saved_eur = clean_currency(developer_cost_saved_eur)

    slack_token = os.getenv("SLACK_BOT_TOKEN")
    slack_channel = os.getenv("SLACK_CHANNEL", "#incidents")

    result = {
        "incident": incident_description[:100],
        "total_benefit_eur": total_benefit_eur,
        "slack_channel": slack_channel,
        "delivery_status": "pending"
    }

    if not SLACK_AVAILABLE:
        result["delivery_status"] = "failed"
        result["error"] = "Slack SDK not installed"
        return json.dumps(result, indent=2)

    if not slack_token:
        result["delivery_status"] = "failed"
        result["error"] = "SLACK_BOT_TOKEN not configured in .env"
        return json.dumps(result, indent=2)

    try:
        client = WebClient(token=slack_token)

        # Format the message using Slack Block Kit
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "💰 Financial Benefits Analysis",
                    "emoji": True
                }
            }
        ]

        # Add ticket ID reference if provided
        if ticket_id:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🎫 *Related Ticket:* `{ticket_id}`"
                }
            })

        blocks.extend([
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Incident Resolved:* {incident_description[:200]}"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Resolution Method:*\n{resolution_method}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Downtime Prevented:*\n{downtime_prevented_minutes} minutes"
                    }
                ]
            }
        ])

        if vm_name:
            blocks.append({
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Affected System:*\n{vm_name}"
                    }
                ]
            })

        # Financial impact section
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*💵 Financial Impact*\n"
                        f"• Revenue Preserved: *€{revenue_preserved_eur:,.2f}*\n"
                        f"• Developer Cost Saved: *€{developer_cost_saved_eur:,.2f}*\n"
                        f"• *Total Benefit: €{total_benefit_eur:,.2f}*"
            }
        })

        if additional_details:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Additional Details:*\n{additional_details}"
                }
            })

        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"📊 Based on Action webshop business case data | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            ]
        })

        # Send message to Slack with threading support
        message_params = {
            "channel": slack_channel,
            "blocks": blocks,
            "text": f"Benefits Analysis: €{total_benefit_eur:,.2f} total benefit"
        }

        # Add threading parameters if provided (benefits should NOT broadcast)
        if thread_ts:
            message_params["thread_ts"] = thread_ts
            logger.info(f"Posting benefits to thread: {thread_ts}")
            # Note: Benefits messages are informational and should stay in thread only
            # Do NOT set reply_broadcast=True here

        response = client.chat_postMessage(**message_params)

        result["delivery_status"] = "success"
        result["slack_message_ts"] = response["ts"]
        result["slack_channel_id"] = response["channel"]

    except SlackApiError as e:
        result["delivery_status"] = "failed"
        result["error"] = f"Slack API error: {e.response['error']}"
        logger.error(f"Slack API error: {e.response}")
    except Exception as e:
        result["delivery_status"] = "failed"
        result["error"] = str(e)
        logger.error(f"Error sending to Slack: {e}")

    return json.dumps(result, indent=2)


# Contextual data from business case documents:
# - Action_Webshopdata_Business_Case.docx: Webshop revenue data
# - VM_Kostenoverzicht_Azure.docx: Azure VM costs
CONTEXTUAL_DATA = {
    "developer_hourly_rate": 75,  # EUR per hour
    "avg_resolution_time_hours": 2,  # Average time to fix issues manually

    # Azure VM costs (from VM_Kostenoverzicht_Azure.docx)
    "vm_costs": {
        "B2s": 0.0832,  # 2 vCPU, 8 GiB - Webserver/microservices
        "B4as_v2": 0.1500,  # 4 vCPU, 16 GiB - Production/API workloads
        "B16s_v2": 0.6660,  # 16 vCPU, 64 GiB - Heavy compute
        "D4s_v3": 0.250,  # 4 vCPU, 16 GiB - General purpose (avg of range)
    },

    # Webshop revenue data per hour (from Action_Webshopdata_Business_Case.docx)
    # Daily revenue: ~€246,000 | Weekly revenue: ~€1.7 million
    "webshop_revenue_per_hour": {
        "00:00-06:00": 16000 / 6,  # €16,000 over 6 hours = €2,667/hour
        "06:00-09:00": 10000 / 3,  # €10,000 over 3 hours = €3,333/hour
        "09:00-12:00": 36000 / 3,  # €36,000 over 3 hours = €12,000/hour
        "12:00-15:00": 56000 / 3,  # €56,000 over 3 hours = €18,667/hour
        "15:00-18:00": 56000 / 3,  # €56,000 over 3 hours = €18,667/hour
        "18:00-21:00": 48000 / 3,  # €48,000 over 3 hours = €16,000/hour
        "21:00-00:00": 24000 / 3,  # €24,000 over 3 hours = €8,000/hour
    },
    "avg_revenue_per_hour": 246000 / 24,  # €10,250/hour average
    "avg_revenue_per_minute": (246000 / 24) / 60,  # ~€170.83/minute

    "customer_impact_cost": 500,  # Cost of customer dissatisfaction per incident
}


async def async_calculate_benefits(
    problem_type: str,
    resolution_method: str,
    vm_name: str = "",
    downtime_prevented_minutes: int = 30,
    incident_hour: int = 12
) -> str:
    """Calculate the financial benefits of a prevented issue.

    Uses real business data from:
    - Action_Webshopdata_Business_Case.docx: Webshop revenue data (€246k daily revenue)
    - VM_Kostenoverzicht_Azure.docx: Azure VM infrastructure costs

    Args:
        problem_type: Type of problem that was prevented (e.g., 'high cpu')
        resolution_method: How it was resolved (e.g., 'reboot', 'escalated')
        vm_name: Name of the VM affected
        downtime_prevented_minutes: Estimated downtime prevented in minutes
        incident_hour: Hour of day when incident occurred (0-23) for accurate revenue calculation

    Returns:
        JSON string with benefit calculation details
    """
    await asyncio.sleep(0.05)  # Simulate async processing

    benefits = {
        "problem_type": problem_type,
        "resolution_method": resolution_method,
        "vm_name": vm_name,
        "data_sources": [
            "Action_Webshopdata_Business_Case.docx",
            "VM_Kostenoverzicht_Azure.docx"
        ],
        "calculations": {}
    }

    # Direct cost savings: developer time
    if resolution_method.lower() == "reboot":
        # Automated resolution saved manual investigation time
        developer_time_saved = CONTEXTUAL_DATA["avg_resolution_time_hours"]
        developer_cost_saved = developer_time_saved * CONTEXTUAL_DATA["developer_hourly_rate"]
        benefits["calculations"]["developer_time_saved_hours"] = developer_time_saved
        benefits["calculations"]["developer_cost_saved_eur"] = developer_cost_saved
    else:
        # Manual escalation still required some developer time
        developer_time_saved = 0.5  # Partial savings from quick detection
        developer_cost_saved = developer_time_saved * CONTEXTUAL_DATA["developer_hourly_rate"]
        benefits["calculations"]["developer_time_saved_hours"] = developer_time_saved
        benefits["calculations"]["developer_cost_saved_eur"] = developer_cost_saved

    # Indirect benefits: preserved revenue
    # Use time-specific revenue data from business case document for more accuracy
    revenue_per_hour_at_incident_time = get_revenue_per_hour_by_time(incident_hour)
    revenue_per_minute = revenue_per_hour_at_incident_time / 60
    revenue_preserved = downtime_prevented_minutes * revenue_per_minute

    benefits["calculations"]["downtime_prevented_minutes"] = downtime_prevented_minutes
    benefits["calculations"]["incident_hour"] = incident_hour
    benefits["calculations"]["revenue_per_hour_at_incident_time_eur"] = round(revenue_per_hour_at_incident_time, 2)
    benefits["calculations"]["revenue_per_minute_eur"] = round(revenue_per_minute, 2)
    benefits["calculations"]["revenue_preserved_eur"] = round(revenue_preserved, 2)

    # Infrastructure cost information (from VM cost overview)
    vm_cost_per_hour = get_vm_cost_per_hour(vm_name)
    vm_cost_for_downtime = (downtime_prevented_minutes / 60) * vm_cost_per_hour
    benefits["calculations"]["vm_hourly_cost_eur"] = round(vm_cost_per_hour, 2)
    benefits["calculations"]["vm_cost_during_potential_downtime_eur"] = round(vm_cost_for_downtime, 2)

    # Customer satisfaction preserved
    if resolution_method.lower() == "reboot":
        # Prevented customer impact entirely
        customer_impact_saved = CONTEXTUAL_DATA["customer_impact_cost"]
    else:
        # Reduced but not eliminated customer impact
        customer_impact_saved = CONTEXTUAL_DATA["customer_impact_cost"] * 0.5

    benefits["calculations"]["customer_satisfaction_value_eur"] = customer_impact_saved

    # Total financial impact
    total_benefit = (
        developer_cost_saved +
        revenue_preserved +
        customer_impact_saved
    )
    benefits["calculations"]["total_benefit_eur"] = round(total_benefit, 2)

    # Add summary context from business case
    benefits["business_context"] = {
        "webshop_daily_revenue_eur": 246000,
        "webshop_weekly_revenue_eur": 1700000,
        "peak_revenue_hours": "12:00-18:00 (€18,667/hour)",
        "vm_type_inferred": "Production workload" if "prod" in vm_name.lower() or "webshop" in vm_name.lower() else "General purpose",
        "data_accuracy": "Based on Action retail webshop business case data"
    }

    return json.dumps(benefits, indent=2)


async def create_agent_from_prompt(prompt_path: Optional[str] = None) -> Tuple[object, object]:
    """Create an Azure AI Benefits Agent using the benefits prompt.

    Args:
        prompt_path: optional path to the prompt file. If omitted, looks for
            ../instructions/base_prompt_benefit_agent.txt relative to this file.

    Returns:
        (agent, thread)
    """
    # Default path for benefits agent prompt
    if not prompt_path:
        env = os.getenv("ENVIRONMENT", "local")
        base_path = "src/workshop/" if env == "container" else ""
        prompt_path = f"{base_path}../instructions/base_prompt_benefit_agent.txt"

    if not os.path.isfile(prompt_path):
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    with open(prompt_path, "r", encoding="utf-8", errors="ignore") as f:
        instructions = f.read()

    # Add tools configured in utils
    try:
        await add_agent_tools()
    except Exception:
        pass

    # Register the benefits calculation tool
    try:
        benefits_tool = AsyncFunctionTool({async_calculate_benefits})
        toolset.add(benefits_tool)
        print("Registered benefits calculation tool")
    except Exception as e:
        logger.debug(f"Could not add benefits tool: {e}")
        # ignore if already added or unsupported
        pass

    # Register the Slack notification tool
    try:
        slack_tool = AsyncFunctionTool({async_send_benefits_to_slack})
        toolset.add(slack_tool)
        print("Registered Slack benefits notification tool")
    except Exception as e:
        logger.debug(f"Could not add Slack tool: {e}")
        # ignore if already added or unsupported
        pass

    print("Creating benefits agent...")
    agent = project_client.agents.create_agent(
        model=API_DEPLOYMENT_NAME,
        name="Benefits Calculator Agent",
        instructions=instructions,
        temperature=0.2,  # Slightly higher for more conversational responses
        toolset=toolset,
        headers={"x-ms-enable-preview": "true"},
    )
    print(f"Created benefits agent: {agent.id}")

    print("Creating thread for benefits agent...")
    thread = project_client.agents.threads.create()
    print(f"Created thread: {thread.id}")

    return agent, thread


async def post_message(
    thread_id: str,
    content: str,
    agent: object,
    thread: object,
    timeout_seconds: int = 120
) -> str:
    """Post a message to the benefits agent and return the financial analysis.

    Args:
        thread_id: The thread ID to post to
        content: The message content (should describe the prevented issue)
        agent: The agent object
        thread: The thread object
        timeout_seconds: Max time to wait for response

    Returns:
        The agent's response containing the benefit analysis
    """
    try:
        print(f"Benefits Agent - Analyzing prevented issue...")

        # Step 1: Receive input about the prevented issue
        print(f"Step 1: Received issue information: {content}")

        # Step 2: Post message to the benefits agent
        print("Step 2: Posting message to Benefits Agent for analysis...")
        message = project_client.agents.messages.create(
            thread_id=thread_id,
            role="user",
            content=content,
        )
        print(f"Message created: {getattr(message, 'id', '<no-id>')}")

        # Step 3: Create and poll run
        print("Step 3: Creating run for benefits calculation...")
        run = project_client.agents.runs.create(
            thread_id=thread.id,
            agent_id=agent.id,
        )
        print(f"Run created: {run.id}")

        # Poll for completion
        waited = 0
        poll_interval = 2
        while run.status in ("queued", "in_progress", "requires_action") and waited < timeout_seconds:
            time.sleep(poll_interval)
            waited += poll_interval

            try:
                run = project_client.agents.runs.get(thread_id=thread.id, run_id=run.id)
                print(f"Run status: {run.status} (waited {waited}s)")
            except Exception as e:
                logger.debug(f"Error polling run: {e}")
                time.sleep(5)
                continue

            # Handle tool calls if required
            if run.status == "requires_action" and run.required_action:
                print("Run requires action - handling tool calls...")
                tool_outputs = []

                try:
                    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                        print(f"Executing function: {tool_call.function.name}")

                        if tool_call.function.name == "async_calculate_benefits":
                            args = json.loads(tool_call.function.arguments)
                            result = await async_calculate_benefits(**args)
                            tool_outputs.append({
                                "tool_call_id": tool_call.id,
                                "output": result
                            })
                        elif tool_call.function.name == "async_send_benefits_to_slack":
                            print(f"Executing async_send_benefits_to_slack tool call...")
                            args = json.loads(tool_call.function.arguments)
                            print(f"Arguments: {args}")
                            result = await async_send_benefits_to_slack(**args)
                            print(f"Result: {result}")
                            tool_outputs.append({
                                "tool_call_id": tool_call.id,
                                "output": result
                            })
                            print("Benefits sent to Slack successfully")

                    if tool_outputs:
                        print("Submitting tool outputs...")
                        run = project_client.agents.runs.submit_tool_outputs(
                            thread_id=thread.id,
                            run_id=run.id,
                            tool_outputs=tool_outputs
                        )
                        print("Tool outputs submitted successfully")
                except Exception as e:
                    print(f"Error handling tool outputs: {e}")
                    logger.exception(e)
                    break

        if waited >= timeout_seconds:
            print("Run timed out")
            return "Benefits calculation timed out. Please try again."

        print(f"Step 4: Run completed with status: {run.status}")

        if run.status == "failed":
            print(f"Run failed: {run.last_error}")
            return "Benefits calculation failed. Unable to analyze financial impact."

        # Step 5: Get the agent's response
        if run.status == "completed":
            try:
                response = project_client.agents.messages.get_last_message_by_role(
                    thread_id=thread_id,
                    role=MessageRole.AGENT,
                )
                if response and getattr(response, 'text_messages', None):
                    result = "\n".join(t.text.value for t in response.text_messages)
                    print("Step 5: Benefits analysis completed")
                    return result
                else:
                    return "No response from benefits agent."
            except Exception as e:
                print(f"Error getting response: {e}")
                logger.exception(e)
                return "Error retrieving benefits analysis."

        return "Unable to complete benefits analysis."

    except Exception as e:
        print(f"Error in benefits agent: {e}")
        logger.exception(e)
        return "An error occurred during benefits calculation."


async def analyze_prevented_issue(
    problem_type: str,
    resolution_method: str,
    vm_name: str = "",
    additional_context: str = ""
) -> Dict[str, Any]:
    """Convenience function to analyze a prevented issue without creating an agent manually.

    Args:
        problem_type: Type of problem prevented (e.g., 'high CPU load')
        resolution_method: How it was resolved (e.g., 'automated reboot', 'escalated')
        vm_name: Name of the affected VM
        additional_context: Any additional context about the issue

    Returns:
        Dictionary containing the benefits analysis
    """
    # Create the agent and thread
    agent, thread = await create_agent_from_prompt()

    try:
        # Construct the message for the benefits agent
        message = f"""
        I need to calculate the financial benefits of a prevented issue:

        Problem Type: {problem_type}
        Resolution Method: {resolution_method}
        VM Name: {vm_name}
        Additional Context: {additional_context}

        Please analyze this prevented issue and provide:
        1. Direct cost savings (developer time, infrastructure resources)
        2. Indirect benefits (preserved revenue, customer satisfaction)
        3. Total financial impact with clear explanation
        """

        # Get the analysis
        result = await post_message(
            thread_id=thread.id,
            content=message,
            agent=agent,
            thread=thread
        )

        return {
            "success": True,
            "analysis": result
        }

    except Exception as e:
        logger.exception(f"Error analyzing prevented issue: {e}")
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        # Cleanup
        try:
            project_client.agents.delete_agent(agent.id)
            print(f"Deleted benefits agent: {agent.id}")
        except Exception as e:
            print(f"Error deleting benefits agent: {e}")
