"""
Monitor Agent - Application Log Monitoring and Anomaly Detection

This agent monitors application logs from Azure Storage for performance anomalies
and returns structured JSON output with detected issues.
"""
import os
import time
import asyncio
import logging
import json
from typing import Tuple, Optional
from datetime import datetime

from azure.ai.agents.models import MessageRole
from azure.storage.blob import BlobServiceClient

from utils import (
    project_client,
    API_DEPLOYMENT_NAME,
    toolset,
    cleanup,
)

logger = logging.getLogger(__name__)


async def get_log_from_azure_storage(
    storage_account_url: str,
    container_name: str,
    blob_name: str,
    sas_token: str
) -> str:
    """
    Retrieve log file from Azure Storage Account.

    Parameters:
    - storage_account_url: URL of the Azure Storage Account (without SAS-token)
    - container_name: name of the container containing the blob
    - blob_name: name of the blob (e.g., 'AvailabilityLogs.log')
    - sas_token: SAS-token for access to the blob (do NOT hardcode secrets in source)

    Returns:
    - Full contents of the log file as a string
    """
    try:
        # Create a client using the SAS token
        blob_service_client = BlobServiceClient(account_url=storage_account_url, credential=sas_token)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

        # Download blob contents
        download_stream = blob_client.download_blob()
        content = download_stream.readall().decode("utf-8")

        logger.info(f"Successfully retrieved log file: {blob_name} from container: {container_name}")
        return content
    except Exception as e:
        logger.error(f"Error retrieving log file from Azure Storage: {e}")
        raise


async def check_for_abnormalities(log_content: str, agent_id: str, thread_id: str) -> dict:
    """
    Use LLM to analyze log content for abnormalities.

    Parameters:
    - log_content: The full log file content
    - agent_id: The monitor agent ID
    - thread_id: The thread ID for the conversation

    Returns:
    - Dictionary with keys:
        - 'abnormalities_found': bool
        - 'title': str (title of the issue)
        - 'description': str (short description)
        - 'detection_time': str (timestamp of detection)
        - 'related_log_lines': list (problematic log lines)
        - 'application_name': str (extracted app name)
    """
    try:
        logger.info("Analyzing log content for abnormalities using LLM...")

        # Create a message with the log content for analysis
        user_message = f"""Please analyze the following log file for abnormalities, specifically looking for increased response times and trends.

Log Content:
---
{log_content}
---

Provide your analysis in the following JSON format ONLY (no markdown, no extra text):
{{
    "abnormalities_found": true or false,
    "title": "Brief title of the issue (e.g., 'Performance Degradation Detected')",
    "short_description": "One sentence summary of what was found",
    "detection_time": "ISO8601 timestamp when the abnormality was detected from logs",
    "application_name": "Name of the application from logs",
    "related_log_lines": ["log line 1", "log line 2", "log line 3"]
}}

Only return valid JSON, nothing else."""

        message = project_client.agents.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message,
        )
        logger.info(f"Message created for analysis: {message.id}")

        # Create run for analysis
        run = project_client.agents.runs.create(
            thread_id=thread_id,
            agent_id=agent_id,
        )
        logger.info(f"Analysis run created: {run.id}")

        # Poll for completion
        max_iterations = 120
        iteration = 0
        while run.status in ("queued", "in_progress", "requires_action") and iteration < max_iterations:
            time.sleep(2)
            iteration += 1
            run = project_client.agents.runs.get(thread_id=thread_id, run_id=run.id)
            logger.debug(f"Run status: {run.status} (iteration {iteration})")

        if run.status == "completed":
            response = project_client.agents.messages.get_last_message_by_role(
                thread_id=thread_id,
                role=MessageRole.AGENT,
            )

            if response:
                analysis_text = "\n".join(t.text.value for t in response.text_messages)
                logger.info(f"LLM analysis completed")

                # Try to parse JSON from response
                try:
                    result = json.loads(analysis_text)
                    return {
                        'abnormalities_found': result.get('abnormalities_found', False),
                        'title': result.get('title', 'Unknown Issue'),
                        'short_description': result.get('short_description', ''),
                        'detection_time': result.get('detection_time', datetime.now().isoformat()),
                        'application_name': result.get('application_name', 'Unknown'),
                        'related_log_lines': result.get('related_log_lines', []),
                    }
                except json.JSONDecodeError:
                    logger.warning("Could not parse JSON from LLM response")
                    return {
                        'abnormalities_found': False,
                        'title': 'Analysis Error',
                        'short_description': 'Could not parse LLM response',
                        'detection_time': datetime.now().isoformat(),
                        'application_name': 'Unknown',
                        'related_log_lines': [],
                    }
            else:
                logger.warning("No response from LLM analysis")
                return {
                    'abnormalities_found': False,
                    'title': 'No Response',
                    'short_description': 'LLM did not return a response',
                    'detection_time': datetime.now().isoformat(),
                    'application_name': 'Unknown',
                    'related_log_lines': [],
                }
        else:
            logger.error(f"Analysis run failed with status: {run.status}")
            return {
                'abnormalities_found': False,
                'title': 'Analysis Failed',
                'short_description': f'LLM analysis failed with status: {run.status}',
                'detection_time': datetime.now().isoformat(),
                'application_name': 'Unknown',
                'related_log_lines': [],
            }
    except Exception as e:
        logger.error(f"Error checking for abnormalities: {e}")
        return {
            'abnormalities_found': False,
            'title': 'Error',
            'short_description': f'Error during analysis: {str(e)}',
            'detection_time': datetime.now().isoformat(),
            'application_name': 'Unknown',
            'related_log_lines': [],
        }


def collect_abnormalities_output(analysis_result: dict) -> dict:
    """
    Format abnormalities output as JSON with required fields.

    Parameters:
    - analysis_result: Dictionary from check_for_abnormalities

    Returns:
    - JSON formatted output with: title, short_description, detection_time, related_log_lines
    """
    if not analysis_result.get('abnormalities_found'):
        return {
            "status": "healthy",
            "message": "No abnormalities detected in logs",
            "title": "System Status: Healthy",
            "short_description": "All response times and metrics are within normal parameters",
            "detection_time": datetime.now().isoformat(),
            "application_name": None,
            "related_log_lines": []
        }

    return {
        "status": "abnormality_detected",
        "title": analysis_result.get('title', 'Abnormality Detected'),
        "short_description": analysis_result.get('short_description', ''),
        "detection_time": analysis_result.get('detection_time', datetime.now().isoformat()),
        "application_name": analysis_result.get('application_name', 'Unknown'),
        "related_log_lines": analysis_result.get('related_log_lines', []),
        "timestamp_detected": datetime.now().isoformat()
    }


async def create_agent_from_prompt(prompt_path: str | None = None) -> Tuple[object, object]:
    """
    Create an Azure AI Agent using monitor agent instructions.

    Args:
        prompt_path: optional path to the prompt file. If omitted, looks for
            instructions/monitor_agent_instructions.txt

    Returns:
        (agent, thread)
    """
    # Default path for monitor agent instructions
    if not prompt_path:
        env = os.getenv("ENVIRONMENT", "local")
        prompt_path = f"{'src/workshop/' if env == 'container' else ''}instructions/monitor_agent_instructions.txt"

    if not os.path.isfile(prompt_path):
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    with open(prompt_path, "r", encoding="utf-8", errors="ignore") as f:
        instructions = f.read()

    logger.info("Creating monitor agent...")
    agent = project_client.agents.create_agent(
        model=API_DEPLOYMENT_NAME,
        name="Monitor Agent",
        instructions=instructions,
        temperature=0.0,
        toolset=toolset,
        headers={"x-ms-enable-preview": "true"},
    )
    logger.info("Created monitor agent: %s", getattr(agent, "id", "<no-id>"))

    logger.info("Creating thread for monitor agent...")
    thread = project_client.agents.threads.create()
    logger.info("Created thread: %s", getattr(thread, "id", "<no-id>"))

    return agent, thread


async def run_monitor_workflow(
    storage_account_url: str,
    container_name: str,
    blob_name: str,
    sas_token: str
) -> dict:
    """
    Execute the complete monitoring workflow:
    1. Get log file from Azure Storage
    2. Check for abnormalities using LLM
    3. Return JSON formatted results

    Parameters:
    - storage_account_url: URL of Azure Storage Account
    - container_name: Name of storage container
    - blob_name: Name of log blob file
    - sas_token: SAS token for storage access

    Returns:
    - Dictionary with JSON formatted monitoring results
    """
    try:
        logger.info("Starting monitor workflow...")

        # Step 1: Get log file from Azure Storage
        logger.info("Step 1: Retrieving log file from Azure Storage...")
        log_content = await get_log_from_azure_storage(
            storage_account_url,
            container_name,
            blob_name,
            sas_token
        )
        logger.info(f"Log file retrieved successfully ({len(log_content)} bytes)")

        # Create agent and thread for analysis
        agent, thread = await create_agent_from_prompt()

        # Step 2: Check for abnormalities
        logger.info("Step 2: Analyzing logs for abnormalities...")
        analysis_result = await check_for_abnormalities(
            log_content,
            agent.id,
            thread.id
        )

        # Step 3: Format output as JSON
        logger.info("Step 3: Formatting output...")
        output = collect_abnormalities_output(analysis_result)

        if output.get('status') == 'abnormality_detected':
            logger.info(f"Monitor workflow completed - abnormalities detected for: {output.get('application_name')}")
        else:
            logger.info("Monitor workflow completed - system is healthy")

        # Cleanup
        await cleanup(agent, thread)

        return output

    except Exception as e:
        logger.error(f"Monitor workflow failed: {e}", exc_info=True)
        # Return error in same JSON format
        return {
            "status": "error",
            "title": "Monitoring Error",
            "short_description": f"An error occurred during monitoring: {str(e)}",
            "detection_time": datetime.now().isoformat(),
            "application_name": None,
            "related_log_lines": [],
            "error_details": str(e)
        }
