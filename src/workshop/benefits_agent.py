import os
import time
import asyncio
import logging
from typing import Tuple, Dict, Any, Optional
import json

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


logger = logging.getLogger(__name__)


# Sample contextual data for benefit calculations
CONTEXTUAL_DATA = {
    "developer_hourly_rate": 75,  # EUR per hour
    "avg_resolution_time_hours": 2,  # Average time to fix issues manually
    "vm_hourly_cost": 0.50,  # EUR per hour
    "avg_downtime_prevented_minutes": 30,
    "revenue_per_minute": 100,  # EUR per minute for webshop
    "customer_impact_cost": 500,  # Cost of customer dissatisfaction per incident
}


async def async_calculate_benefits(
    problem_type: str,
    resolution_method: str,
    vm_name: str = "",
    downtime_prevented_minutes: int = 30
) -> str:
    """Calculate the financial benefits of a prevented issue.

    Args:
        problem_type: Type of problem that was prevented (e.g., 'high cpu')
        resolution_method: How it was resolved (e.g., 'reboot', 'escalated')
        vm_name: Name of the VM affected
        downtime_prevented_minutes: Estimated downtime prevented in minutes

    Returns:
        JSON string with benefit calculation details
    """
    await asyncio.sleep(0.05)  # Simulate async processing

    benefits = {
        "problem_type": problem_type,
        "resolution_method": resolution_method,
        "vm_name": vm_name,
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
    revenue_preserved = downtime_prevented_minutes * CONTEXTUAL_DATA["revenue_per_minute"]
    benefits["calculations"]["downtime_prevented_minutes"] = downtime_prevented_minutes
    benefits["calculations"]["revenue_preserved_eur"] = revenue_preserved

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
    benefits["calculations"]["total_benefit_eur"] = total_benefit

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
