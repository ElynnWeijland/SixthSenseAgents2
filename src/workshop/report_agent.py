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


async def async_send_to_slack(
    ticket_title: str,
    ticket_id: str,
    incident_details: str,
    severity: str = "Medium",
    affected_system: str = "",
    resolution: str = "",
    thread_ts: str = None,
    reply_broadcast: bool = False
) -> str:
    """Send a formatted ticket to Slack with optional threading support.

    Args:
        ticket_title: Title of the ticket
        ticket_id: Unique ticket identifier
        incident_details: Description of the incident
        severity: Severity level (Low, Medium, High, Critical)
        affected_system: Name of affected system/VM
        resolution: Resolution steps or status
        thread_ts: Thread timestamp to reply to (for threading)
        reply_broadcast: If True, also show reply in main channel

    Returns:
        JSON string with Slack delivery status
    """
    await asyncio.sleep(0.05)  # Simulate async processing

    slack_token = os.getenv("SLACK_BOT_TOKEN")
    slack_channel = os.getenv("SLACK_CHANNEL", "#incidents")

    result = {
        "ticket_id": ticket_id,
        "ticket_title": ticket_title,
        "severity": severity,
        "affected_system": affected_system,
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

        # Format the message using Slack Block Kit for better presentation
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🎫 {ticket_title}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Ticket ID:*\n`{ticket_id}`"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Severity:*\n{severity}"
                    }
                ]
            }
        ]

        if affected_system:
            blocks.append({
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Affected System:*\n{affected_system}"
                    }
                ]
            })

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Incident Details:*\n{incident_details}"
            }
        })

        if resolution:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Resolution:*\n{resolution}"
                }
            })

        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            ]
        })

        # Send message to Slack with threading support
        message_params = {
            "channel": slack_channel,
            "blocks": blocks,
            "text": f"New Ticket: {ticket_title}"  # Fallback text for notifications
        }

        # Add threading parameters if provided
        if thread_ts:
            message_params["thread_ts"] = thread_ts
            logger.info(f"Posting to thread: {thread_ts}")

            # Broadcast to channel if requested (hybrid approach)
            if reply_broadcast:
                message_params["reply_broadcast"] = True
                logger.info("Broadcasting reply to main channel")

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


async def create_agent_from_prompt(prompt_path: Optional[str] = None) -> Tuple[object, object]:
    """Create an Azure AI Report Agent using the ticketing prompt.

    Args:
        prompt_path: optional path to the prompt file. If omitted, looks for
            ../instructions/base_prompt_ticketing_agent.txt relative to this file.

    Returns:
        (agent, thread)
    """
    # Default path for ticketing agent prompt
    if not prompt_path:
        env = os.getenv("ENVIRONMENT", "local")
        base_path = "src/workshop/" if env == "container" else ""
        prompt_path = f"{base_path}../instructions/base_prompt_ticketing_agent.txt"

    if not os.path.isfile(prompt_path):
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    with open(prompt_path, "r", encoding="utf-8", errors="ignore") as f:
        instructions = f.read()

    # Adapt the prompt for Slack instead of Teams
    instructions = instructions.replace("Microsoft Teams", "Slack")
    instructions = instructions.replace("Teams chat", "Slack channel")

    # Add tools configured in utils
    try:
        await add_agent_tools()
    except Exception:
        pass

    # Register the Slack reporting tool
    try:
        slack_tool = AsyncFunctionTool({async_send_to_slack})
        toolset.add(slack_tool)
        print("Registered Slack reporting tool")
    except Exception as e:
        logger.debug(f"Could not add Slack tool: {e}")
        # ignore if already added or unsupported
        pass

    print("Creating report agent...")
    agent = project_client.agents.create_agent(
        model=API_DEPLOYMENT_NAME,
        name="Report Agent",
        instructions=instructions,
        temperature=0.2,
        toolset=toolset,
        headers={"x-ms-enable-preview": "true"},
    )
    print(f"Created report agent: {agent.id}")

    print("Creating thread for report agent...")
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
    """Post a message to the report agent and send ticket to Slack.

    Args:
        thread_id: The thread ID to post to
        content: The message content (should describe the incident)
        agent: The agent object
        thread: The thread object
        timeout_seconds: Max time to wait for response

    Returns:
        The agent's response containing the ticket details
    """
    try:
        print(f"Report Agent - Creating ticket from incident...")

        # Step 1: Receive incident information
        print(f"Step 1: Received incident information: {content[:100]}...")

        # Step 2: Post message to the report agent
        print("Step 2: Posting message to Report Agent for ticket creation...")
        message = project_client.agents.messages.create(
            thread_id=thread_id,
            role="user",
            content=content,
        )
        print(f"Message created: {getattr(message, 'id', '<no-id>')}")

        # Step 3: Create and poll run
        print("Step 3: Creating run for ticket generation...")
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

                        if tool_call.function.name == "async_send_to_slack":
                            args = json.loads(tool_call.function.arguments)
                            result = await async_send_to_slack(**args)
                            tool_outputs.append({
                                "tool_call_id": tool_call.id,
                                "output": result
                            })

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
            return "Ticket creation timed out. Please try again."

        print(f"Step 4: Run completed with status: {run.status}")

        if run.status == "failed":
            print(f"Run failed: {run.last_error}")
            return "Ticket creation failed. Unable to generate ticket."

        # Step 5: Get the agent's response
        if run.status == "completed":
            try:
                response = project_client.agents.messages.get_last_message_by_role(
                    thread_id=thread_id,
                    role=MessageRole.AGENT,
                )
                if response and getattr(response, 'text_messages', None):
                    result = "\n".join(t.text.value for t in response.text_messages)
                    print("Step 5: Ticket creation completed")
                    return result
                else:
                    return "No response from report agent."
            except Exception as e:
                print(f"Error getting response: {e}")
                logger.exception(e)
                return "Error retrieving ticket details."

        return "Unable to complete ticket creation."

    except Exception as e:
        print(f"Error in report agent: {e}")
        logger.exception(e)
        return "An error occurred during ticket creation."


async def create_and_send_ticket(
    incident_description: str,
    resolution_output: str = "",
    severity: str = "Medium",
    affected_system: str = ""
) -> Dict[str, Any]:
    """Convenience function to create a ticket and send to Slack.

    Args:
        incident_description: Description of the incident
        resolution_output: Output from resolution agent (if available)
        severity: Severity level (Low, Medium, High, Critical)
        affected_system: Name of affected system/VM

    Returns:
        Dictionary containing the ticket creation result
    """
    # Create the agent and thread
    agent, thread = await create_agent_from_prompt()

    try:
        # Construct the message for the report agent
        message = f"""
        Create a ticket for the following incident:

        Incident: {incident_description}
        Severity: {severity}
        Affected System: {affected_system}
        """

        if resolution_output:
            message += f"\nResolution: {resolution_output}"

        message += """

        Please:
        1. Generate a unique ticket ID
        2. Create a clear ticket title
        3. Extract and organize all relevant incident details
        4. Format the ticket for Slack delivery
        5. Send the ticket to Slack
        """

        # Get the ticket creation result
        result = await post_message(
            thread_id=thread.id,
            content=message,
            agent=agent,
            thread=thread
        )

        return {
            "success": True,
            "ticket_details": result
        }

    except Exception as e:
        logger.exception(f"Error creating ticket: {e}")
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        # Cleanup
        try:
            project_client.agents.delete_agent(agent.id)
            print(f"Deleted report agent: {agent.id}")
        except Exception as e:
            print(f"Error deleting report agent: {e}")
